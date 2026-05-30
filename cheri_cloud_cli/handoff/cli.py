"""Handoff CLI command handlers."""

from __future__ import annotations

import json
import os
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..client import CheriClient, CheriClientError
from ..sessions import JsonCredentialStore, load_authenticated_state
from .service import (
    create_manifest,
    write_manifest,
    list_handoffs as list_handoffs_service,
    get_handoff as get_handoff_service,
    get_latest_handoff as get_latest_handoff_service,
    create_handoff_metadata,
    _get_git_context,
)


console = Console()


def _resolve_workspace(client, store, workspace_id: Optional[str]):
    """Resolve workspace from id or name."""
    state = load_authenticated_state(client, store)
    if not state.active_workspace:
        raise CheriClientError("No active workspace. Run 'cheri workspace use' or provide --workspace.")
    workspaces = client.list_workspaces(state)
    if workspace_id:
        for ws in workspaces:
            ws_id = getattr(ws, 'id', None) or (ws.to_dict().get('id') if hasattr(ws, 'to_dict') else None)
            ws_name = getattr(ws, 'name', None) or (ws.to_dict().get('name') if hasattr(ws, 'to_dict') else None)
            if ws_id == workspace_id or ws_name == workspace_id:
                return ws
        raise CheriClientError(f"Workspace '{workspace_id}' not found.")
    return state.active_workspace


def _resolve_path(path: str) -> Path:
    """Resolve path from string."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise click.ClickException(f"Path not found: {path}")
    return p


def inspect_handoff(console: Console, path: str) -> None:
    """Dry-run scan showing included/skipped files."""
    p = _resolve_path(path)
    manifest = create_manifest(
        source_path=str(p),
        name="inspect",
        description="",
        include_sensitive=False,
    )

    table = Table(box=None, border_style="cyan", title="Inspect Results")
    table.add_column("Status", width=16)
    table.add_column("Count", justify="right", width=8)
    table.add_row("[green]INCLUDED[/]", str(manifest["_file_count"]))
    table.add_row("[yellow]SKIPPED (secret-safe)[/]", str(len(manifest["skipped_sensitive"])))
    console.print(table)

    if manifest["skipped_sensitive"]:
        console.print()
        console.print("[yellow]Skipped files (names only):[/]")
        for name in sorted(manifest["skipped_sensitive"])[:20]:
            console.print(f"  [dim]{name}[/]")
        if len(manifest["skipped_sensitive"]) > 20:
            console.print(f"  [dim]... and {len(manifest['skipped_sensitive']) - 20} more[/]")

    if manifest.get("git_context"):
        git = manifest["git_context"]
        console.print()
        console.print(Panel.fit(
            f"Branch   : {git['branch']}\n"
            f"Commit   : {git['commit_hash']}\n"
            f"Dirty    : {'yes' if git['dirty'] else 'no'}",
            title="Git Context",
            border_style="blue",
        ))


def create_handoff(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    path: str,
    name: str,
    description: str,
    tags: tuple[str, ...],
    agent_name: Optional[str],
    tool_name: Optional[str],
    version_label: Optional[str],
    include_sensitive: bool,
) -> None:
    """Create a local handoff manifest (no upload)."""
    p = _resolve_path(path)

    if not include_sensitive and not console.input(
        "[yellow]Warning:[/] Secret-safe scanning is enabled by default. "
        "Sensitive files (.env, credentials, keys, etc.) will be skipped.\n"
        "Use --include-sensitive to include them (requires explicit confirmation).\n\n"
        "Continue?",
        default="y",
    ):
        console.print("[yellow]Cancelled.[/]")
        return

    manifest = create_manifest(
        source_path=str(p),
        name=name,
        description=description,
        tags=list(tags),
        agent_name=agent_name,
        tool_name=tool_name,
        version_label=version_label,
        include_sensitive=include_sensitive,
    )

    output_dir = p if p.is_dir() else p.parent
    manifest_path = write_manifest(manifest, str(output_dir))

    console.print(Panel.fit(
        f"Name          : {manifest['name']}\n"
        f"Handoff ID    : {manifest['handoff_id']}\n"
        f"Files         : {manifest['_file_count']}\n"
        f"Total size    : {manifest['_total_size']:,} bytes\n"
        f"Manifest      : {manifest_path}\n"
        f"Skipped       : {len(manifest['skipped_sensitive'])} secret-safe file(s)",
        title="Handoff Created",
        border_style="green",
    ))

    if manifest.get("git_context"):
        git = manifest["git_context"]
        console.print(f"\n[dim]Git: {git['branch']} @ {git['commit_hash']}{' (dirty)' if git['dirty'] else ''}[/]")


def push_handoff(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    path: str,
    name: str,
    workspace: Optional[str],
    description: str,
    tags: tuple[str, ...],
    agent_name: Optional[str],
    tool_name: Optional[str],
    version_label: Optional[str],
    include_sensitive: bool,
) -> None:
    """Create manifest and upload safe files to workspace."""
    p = _resolve_path(path)

    if not include_sensitive:
        confirmed = console.input(
            "[yellow]Warning:[/] Secret-safe scanning is enabled. "
            "Sensitive files will be skipped.\n"
            "Use --include-sensitive to include them.\n\n"
            "Continue with handoff?",
            default="y",
        )
        if confirmed.lower() not in ("y", "yes"):
            console.print("[yellow]Cancelled.[/]")
            return

    console.print(f"[cyan]Creating handoff for[/] {p}...")

    manifest = create_manifest(
        source_path=str(p),
        name=name,
        description=description,
        tags=list(tags),
        agent_name=agent_name,
        tool_name=tool_name,
        version_label=version_label,
        include_sensitive=include_sensitive,
    )

    # Resolve workspace
    ws = _resolve_workspace(client, store, workspace)
    state = load_authenticated_state(client, store)

    # Upload files
    from .service import upload_handoff_file
    from datetime import datetime, timezone

    files_to_upload = manifest.get("files", [])
    uploaded_files = []
    failed_files = []
    total_uploaded_size = 0

    console.print(f"[cyan]Uploading {len(files_to_upload)} file(s)...[/]")

    for i, file_entry in enumerate(files_to_upload):
        rel_path = file_entry["relative_path"]
        file_path = p / rel_path if p.is_dir() else Path(file_entry.get("source_path", p / rel_path))

        try:
            result = upload_handoff_file(
                client=client,
                state=state,
                source_path=file_path,
                handoff_id=manifest["handoff_id"],
                relative_path=rel_path,
                workspace_id=ws.id,
            )
            # Update manifest file entry with upload metadata
            file_entry["file_id"] = result["file_id"]
            file_entry["storage_key"] = result["storage_key"]
            file_entry["provider_id"] = result["provider_id"]
            file_entry["uploaded_at"] = result["uploaded_at"]
            file_entry["upload_status"] = result["upload_status"]
            uploaded_files.append(result)
            total_uploaded_size += file_entry["size"]
            console.print(f"  [green]+[/] {rel_path}")
        except Exception as exc:
            file_entry["upload_status"] = "failed"
            failed_files.append({"path": rel_path, "error": str(exc)})
            console.print(f"  [red]![/] {rel_path}: {exc}")

    # Determine overall status
    if failed_files:
        handoff_status = "partial_failed"
        console.print(f"\n[yellow]Warning:[/] {len(failed_files)} file(s) failed to upload")
    else:
        handoff_status = "ready"

    # Write manifest locally (with upload metadata)
    output_dir = p if p.is_dir() else p.parent
    manifest_path = write_manifest(manifest, str(output_dir))
    console.print(f"[green]Manifest written:[/] {manifest_path}")

    # Upload manifest as a handoff file (store its file_id as manifest_file_id)
    manifest_file_id = None
    try:
        manifest_rel_path = "cheri-handoff.json"
        manifest_result = upload_handoff_file(
            client=client,
            state=state,
            source_path=manifest_path,
            handoff_id=manifest["handoff_id"],
            relative_path=manifest_rel_path,
            workspace_id=ws.id,
        )
        manifest_file_id = manifest_result["file_id"]
        console.print(f"  [green]+[/] {manifest_rel_path} (manifest)")
    except Exception as exc:
        console.print(f"[yellow]Warning:[/] Manifest upload failed: {exc}")

    # Compute manifest checksum
    import hashlib
    with open(manifest_path, "rb") as f:
        manifest_checksum = hashlib.sha256(f.read()).hexdigest()

    # Create/update backend metadata
    console.print(f"[cyan]Updating handoff metadata...[/]")
    try:
        backend_updates = {
            "status": handoff_status,
            "file_count": len(uploaded_files),
            "total_uploaded_size": total_uploaded_size,
            "uploaded_file_ids": [f["file_id"] for f in uploaded_files],
            "manifest_file_id": manifest_file_id,
            "manifest_checksum": manifest_checksum,
            "failed_files": [f["path"] for f in failed_files],
            "provider_id": uploaded_files[0]["provider_id"] if uploaded_files else "system",
        }
        result = client.update_handoff(state, manifest["handoff_id"], backend_updates)
        console.print(f"[green]Handoff metadata updated:[/] status={handoff_status}")
    except CheriClientError as exc:
        console.print(f"[yellow]Warning:[/] Could not update backend metadata: {exc}")
        console.print("[dim]Local manifest was created successfully.[/]")

    # Summary
    console.print(Panel.fit(
        f"Name          : {manifest['name']}\n"
        f"Handoff ID    : {manifest['handoff_id']}\n"
        f"Files         : {len(uploaded_files)}/{len(files_to_upload)} uploaded\n"
        f"Total size    : {manifest['_total_size']:,} bytes\n"
        f"Manifest      : {manifest_path}\n"
        f"Status        : {handoff_status}\n"
        f"Skipped       : {len(manifest['skipped_sensitive'])} secret-safe file(s)",
        title="Handoff Complete",
        border_style="green" if not failed_files else "yellow",
    ))


def list_handoffs(console: Console, client: CheriClient, store: JsonCredentialStore, workspace: Optional[str]) -> None:
    """List recent handoffs in a workspace."""
    try:
        ws = _resolve_workspace(client, store, workspace)
        handoffs = list_handoffs_service(client, store, workspace_id=ws.id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    if not handoffs:
        console.print("[yellow]No handoffs found in this workspace.[/]")
        return

    table = Table(box=None, border_style="cyan", title=f"Handoffs: {ws.name}")
    table.add_column("ID", style="cyan", width=16)
    table.add_column("Name", style="white", width=32)
    table.add_column("Files", justify="right", width=6)
    table.add_column("Size", justify="right", width=12)
    table.add_column("Agent", style="dim", width=16)
    table.add_column("Created", style="dim", width=20)

    for h in handoffs:
        table.add_row(
            h.get("id", "")[:16],
            h.get("name", ""),
            str(h.get("file_count", 0)),
            _format_size(h.get("total_size", 0)),
            h.get("agent_name", "-") or "-",
            h.get("created_at", "")[:19] if h.get("created_at") else "-",
        )
    console.print(table)


def show_handoff(console: Console, client: CheriClient, store: JsonCredentialStore, handoff_id: str) -> None:
    """Show metadata and file list for a handoff."""
    try:
        h = get_handoff_service(client, store, handoff_id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    lines = [
        f"ID          : {h.get('id', 'unknown')}",
        f"Name        : {h.get('name', '')}",
        f"Description : {h.get('description', '')}",
        f"Workspace   : {h.get('workspace_id', '')}",
        f"Files       : {h.get('file_count', 0)}",
        f"Total size  : {_format_size(h.get('total_size', 0))}",
        f"Agent       : {h.get('agent_name', '-') or '-'}",
        f"Tool        : {h.get('tool_name', '-') or '-'}",
        f"Version     : {h.get('version_label', '-') or '-'}",
        f"Tags        : {', '.join(h.get('tags', []) or ['-'])}",
        f"Created     : {h.get('created_at', 'unknown')}",
        f"Source path : {h.get('source_path', '-')}",
    ]

    if h.get("git_branch"):
        lines.append(f"Git branch  : {h.get('git_branch')}")
        lines.append(f"Git commit  : {h.get('git_commit', '')[:12]}")

    console.print(Panel.fit("\n".join(lines), title=f"Handoff: {handoff_id[:16]}", border_style="green"))

    # Show files if available
    files = h.get("files", [])
    if files:
        console.print()
        table = Table(box=None, border_style="dim", title="Files")
        table.add_column("Path", style="white")
        table.add_column("Size", justify="right", width=12)
        table.add_column("Checksum", style="dim", width=16)
        for f in files[:50]:
            table.add_row(f.get("relative_path", ""), _format_size(f.get("size", 0)), f.get("checksum", "")[:12])
        console.print(table)
        if len(files) > 50:
            console.print(f"[dim]... and {len(files) - 50} more files[/]")


def pull_handoff(console: Console, client: CheriClient, store: JsonCredentialStore, handoff_id: str, dest: Optional[str]) -> None:
    """Download handoff files to a local folder."""
    try:
        h = get_handoff_service(client, store, handoff_id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    output_dir = Path(dest or f"./handoff-{handoff_id[:8]}").resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        if not console.input(f"[yellow]Directory {output_dir} exists and is not empty. Continue?[/]", default="n"):
            console.print("[yellow]Cancelled.[/]")
            return

    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[cyan]Pulling handoff to[/] {output_dir}...")

    # Write manifest
    manifest_data = h.get("manifest", {})
    manifest_path = output_dir / "cheri-handoff.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    console.print(f"[green]Downloaded handoff manifest[/]")
    console.print(f"[dim]Note:[/] File content download requires storage provider integration.")


def latest_handoff(console: Console, client: CheriClient, store: JsonCredentialStore, workspace: Optional[str]) -> None:
    """Show the most recent handoff for a workspace."""
    try:
        ws = _resolve_workspace(client, store, workspace)
        h = get_latest_handoff_service(client, store, workspace_id=ws.id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    show_handoff(console, client, store, h.get("id", ""))


def bundle_handoff(console: Console, path: str, name: str, include_sensitive: bool) -> None:
    """Create a bundle archive of a path."""
    p = _resolve_path(path)

    if not include_sensitive:
        confirmed = console.input(
            "[yellow]Warning:[/] Secret-safe scanning is enabled. Continue?",
            default="y",
        )
        if confirmed.lower() not in ("y", "yes"):
            console.print("[yellow]Cancelled.[/]")
            return

    manifest = create_manifest(
        source_path=str(p),
        name=name,
        include_sensitive=include_sensitive,
    )

    bundle_name = f"{name.replace(' ', '-')}-{manifest['handoff_id'][:8]}.tar.gz"
    output_path = Path(bundle_name).resolve()

    console.print(f"[cyan]Creating bundle:[/] {output_path}")

    with tarfile.open(output_path, "w:gz") as tar:
        # Add manifest
        manifest_json = json.dumps(manifest, indent=2)
        import io
        manifest_bytes = manifest_json.encode("utf-8")
        tarinfo = tarfile.TarInfo(name="cheri-handoff.json")
        tarinfo.size = len(manifest_bytes)
        tar.addfile(tarinfo, io.BytesIO(manifest_bytes))

        # Add files
        for f in manifest["files"]:
            file_path = p / f["relative_path"] if p.is_dir() else Path(f["relative_path"])
            if file_path.exists():
                tar.add(file_path, arcname=f["relative_path"])

    console.print(f"[green]Bundle created:[/] {output_path}")
    console.print(f"[dim]Size: {_format_size(output_path.stat().st_size)}[/]")


def _format_size(size: int) -> str:
    """Format byte size as human-readable string."""
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f}GB"