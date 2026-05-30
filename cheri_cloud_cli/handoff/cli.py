"""Handoff CLI command handlers."""

from __future__ import annotations

import hashlib
import json
import requests
import tarfile
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table
from rich.tree import Tree

from ..client import CheriClient, CheriClientError
from ..sessions import JsonCredentialStore, load_authenticated_state
from ..retry import with_retry, DEFAULT_MAX_RETRIES, DEFAULT_INITIAL_DELAY
from .service import (
    create_manifest,
    write_manifest,
    list_handoffs as list_handoffs_service,
    get_handoff as get_handoff_service,
    get_latest_handoff as get_latest_handoff_service,
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


def _on_retry_log(exc: Exception, attempt: int) -> None:
    """Log retry attempts."""
    console.print(f"[yellow]Retry {attempt} after error:[/] {exc}")


# =============================================================================
# INSPECT
# =============================================================================

def inspect_handoff(console: Console, path: str) -> None:
    """Dry-run scan showing included/skipped files."""
    p = _resolve_path(path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Scanning files..."),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("", total=None)
        manifest = create_manifest(
            source_path=str(p),
            name="inspect",
            description="",
            include_sensitive=False,
        )

    table = Table(box=None, border_style="cyan", title="Inspect Results")
    table.add_column("Status", width=20)
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


# =============================================================================
# CREATE
# =============================================================================

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

    if not include_sensitive:
        console.print(
            "[yellow]Warning:[/] Secret-safe scanning is enabled by default. "
            "Sensitive files (.env, credentials, keys, etc.) will be skipped.\n"
            "Use --include-sensitive to include them (requires explicit confirmation).\n"
        )
        confirmed = console.input("Continue? [Y/n] ")
        if confirmed.lower() in ("n", "no"):
            console.print("[yellow]Cancelled.[/]")
            return

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Scanning and creating manifest..."),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("", total=None)
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


# =============================================================================
# PUSH (with retry, progress, partial failure policy)
# =============================================================================

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
    allow_partial: bool = False,
) -> int:
    """
    Create manifest and upload safe files to workspace.

    Returns exit code: 0 for success, 1 for failure/partial failure.
    """
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
            return 0

    console.print(f"[cyan]Creating handoff for[/] {p}...")

    # Scan directory with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Scanning files..."),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("", total=None)
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

    from .service import upload_handoff_file

    files_to_upload = manifest.get("files", [])
    uploaded_files = []
    failed_files = []
    total_uploaded_size = 0

    if not files_to_upload:
        console.print("[yellow]No files to upload.[/]")
        return 0

    # Upload with progress bar
    console.print(f"[cyan]Uploading {len(files_to_upload)} file(s)...[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Uploading file {task.description}..."),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[dim]{task.completed}/{task.total}[/]"),
        console=console,
    ) as progress:
        upload_task = progress.add_task(
            "upload",
            total=len(files_to_upload),
        )

        for i, file_entry in enumerate(files_to_upload):
            rel_path = file_entry["relative_path"]
            progress.update(upload_task, description=rel_path[:30])

            # For small files, just upload directly
            file_path = p / rel_path if p.is_dir() else Path(file_entry.get("source_path", p / rel_path))

            try:
                # Retry upload with exponential backoff
                result = with_retry(
                    upload_handoff_file,
                    client=client,
                    state=state,
                    source_path=file_path,
                    handoff_id=manifest["handoff_id"],
                    relative_path=rel_path,
                    workspace_id=ws.id,
                    max_retries=DEFAULT_MAX_RETRIES,
                    initial_delay=DEFAULT_INITIAL_DELAY,
                    on_retry=_on_retry_log,
                )
                # Update manifest file entry with upload metadata
                file_entry["file_id"] = result["file_id"]
                file_entry["storage_key"] = result["storage_key"]
                file_entry["provider_id"] = result["provider_id"]
                file_entry["uploaded_at"] = result["uploaded_at"]
                file_entry["upload_status"] = result["upload_status"]
                uploaded_files.append(result)
                total_uploaded_size += file_entry["size"]
                progress.update(upload_task, completed=i + 1)
                console.print(f"  [green]+[/] {rel_path}")
            except Exception as exc:
                file_entry["upload_status"] = "failed"
                failed_files.append({"path": rel_path, "error": str(exc)})
                progress.update(upload_task, completed=i + 1)
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

    # Upload manifest as a handoff file
    manifest_file_id = None
    try:
        manifest_rel_path = "cheri-handoff.json"
        manifest_result = with_retry(
            upload_handoff_file,
            client=client,
            state=state,
            source_path=manifest_path,
            handoff_id=manifest["handoff_id"],
            relative_path=manifest_rel_path,
            workspace_id=ws.id,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            on_retry=_on_retry_log,
        )
        manifest_file_id = manifest_result["file_id"]
        console.print(f"  [green]+[/] {manifest_rel_path} (manifest)")
    except Exception as exc:
        console.print(f"[yellow]Warning:[/] Manifest upload failed: {exc}")

    # Compute manifest checksum
    with open(manifest_path, "rb") as f:
        manifest_checksum = hashlib.sha256(f.read()).hexdigest()

    # Create/update backend metadata with retry
    console.print("[cyan]Updating handoff metadata...[/]")
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
        result = with_retry(
            client.update_handoff,
            state,
            manifest["handoff_id"],
            backend_updates,
            max_retries=DEFAULT_MAX_RETRIES,
            initial_delay=DEFAULT_INITIAL_DELAY,
            on_retry=_on_retry_log,
        )
        console.print(f"[green]Handoff metadata updated:[/] status={handoff_status}")
    except Exception as exc:
        console.print(f"[yellow]Warning:[/] Could not update backend metadata: {exc}")
        console.print("[dim]Local manifest was created successfully.[/]")

    # Summary
    border_style = "green" if not failed_files else "yellow"
    if failed_files and not allow_partial:
        border_style = "red"

    console.print(Panel.fit(
        f"Name          : {manifest['name']}\n"
        f"Handoff ID    : {manifest['handoff_id']}\n"
        f"Files         : {len(uploaded_files)}/{len(files_to_upload)} uploaded\n"
        f"Total size    : {manifest['_total_size']:,} bytes\n"
        f"Manifest      : {manifest_path}\n"
        f"Status        : {handoff_status}\n"
        f"Skipped       : {len(manifest['skipped_sensitive'])} secret-safe file(s)"
        + (f"\nFailed        : {len(failed_files)} file(s)" if failed_files else ""),
        title="Handoff Complete",
        border_style=border_style,
    ))

    # Return exit code
    if failed_files and not allow_partial:
        return 1
    return 0


# =============================================================================
# LIST (with filters)
# =============================================================================

def list_handoffs(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    workspace: Optional[str],
    agent: Optional[str] = None,
    tag: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> None:
    """List recent handoffs in a workspace with optional filters."""
    try:
        ws = _resolve_workspace(client, store, workspace)
        load_authenticated_state(client, store)

        # Build query params for backend filtering
        params = {}
        if agent:
            params["agent"] = agent
        if tag:
            params["tag"] = tag
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if status_filter:
            params["status"] = status_filter

        handoffs = list_handoffs_service(client, store, workspace_id=ws.id, params=params)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    if not handoffs:
        console.print("[yellow]No handoffs found in this workspace.[/]")
        return

    # Build filter description
    filter_parts = []
    if agent:
        filter_parts.append(f"agent={agent}")
    if tag:
        filter_parts.append(f"tag={tag}")
    if since:
        filter_parts.append(f"since={since}")
    if until:
        filter_parts.append(f"until={until}")
    if status_filter:
        filter_parts.append(f"status={status_filter}")

    filter_desc = f" [dim](filtered: {', '.join(filter_parts)})[/]" if filter_parts else ""

    table = Table(box=None, border_style="cyan", title=f"Handoffs: {ws.name}{filter_desc}")
    table.add_column("ID", style="cyan", width=16)
    table.add_column("Name", style="white", width=24)
    table.add_column("Status", style="white", width=14)
    table.add_column("Files", justify="right", width=5)
    table.add_column("Size", justify="right", width=10)
    table.add_column("Agent", style="dim", width=14)
    table.add_column("Tags", style="dim", width=16)
    table.add_column("Created", style="dim", width=20)

    for h in handoffs:
        h_status = h.get("status", "unknown")
        status_color = {
            "ready": "green",
            "partial_failed": "yellow",
            "uploading": "cyan",
            "created": "dim",
            "archived": "dim",
        }.get(h_status, "white")
        table.add_row(
            h.get("id", "")[:16],
            h.get("name", "")[:24],
            f"[{status_color}]{h_status}[/{status_color}]",
            str(h.get("file_count", 0)),
            _format_size(h.get("total_uploaded_size", h.get("total_size", 0))),
            h.get("agent_name", "-") or "-",
            ",".join(h.get("tags", []) or [])[:16] or "-",
            h.get("created_at", "")[:19] if h.get("created_at") else "-",
        )
    console.print(table)


# =============================================================================
# SHOW
# =============================================================================

def show_handoff(console: Console, client: CheriClient, store: JsonCredentialStore, handoff_id: str) -> None:
    """Show metadata and file list for a handoff."""
    try:
        h = get_handoff_service(client, store, handoff_id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    status = h.get("status", "unknown")
    status_color = {
        "ready": "green",
        "partial_failed": "yellow",
        "uploading": "cyan",
        "created": "dim",
        "archived": "dim",
    }.get(status, "white")

    lines = [
        f"ID              : {h.get('id', 'unknown')}",
        f"Name            : {h.get('name', '')}",
        f"Description     : {h.get('description', '')}",
        f"Workspace       : {h.get('workspace_id', '')}",
        f"Status          : [{status_color}]{status}[/{status_color}]",
        f"Provider        : {h.get('provider_id', '-') or '-'}",
        f"Files (uploaded): {h.get('file_count', 0)}",
        f"Total size      : {_format_size(h.get('total_uploaded_size', h.get('total_size', 0)))}",
        f"Manifest        : {'yes' if h.get('manifest_file_id') else 'no'} (file_id: {h.get('manifest_file_id', 'N/A')[:16] if h.get('manifest_file_id') else 'N/A'})",
        f"Agent           : {h.get('agent_name', '-') or '-'}",
        f"Tool            : {h.get('tool_name', '-') or '-'}",
        f"Version         : {h.get('version_label', '-') or '-'}",
        f"Tags            : {', '.join(h.get('tags', []) or ['-'])}",
        f"Created         : {h.get('created_at', 'unknown')}",
        f"Source path     : {h.get('source_path', '-')}",
    ]

    if h.get("git_branch"):
        lines.append(f"Git branch      : {h.get('git_branch')}")
        lines.append(f"Git commit      : {h.get('git_commit', '')[:12]}")

    if h.get("failed_files"):
        lines.append(f"Failed files    : {len(h['failed_files'])}")
        for fp in h["failed_files"][:5]:
            lines.append(f"  - {fp}")
        if len(h["failed_files"]) > 5:
            lines.append(f"  ... and {len(h['failed_files']) - 5} more")

    console.print(Panel.fit("\n".join(lines), title=f"Handoff: {handoff_id[:16]}", border_style="green"))

    # Show files if available in manifest
    manifest = h.get("manifest", {})
    files = manifest.get("files", []) if manifest else []
    if files:
        console.print()
        table = Table(box=None, border_style="dim", title="Files (with upload status)")
        table.add_column("Path", style="white")
        table.add_column("Size", justify="right", width=10)
        table.add_column("Status", width=12)
        table.add_column("File ID", style="dim", width=18)
        table.add_column("Checksum", style="dim", width=16)
        for f in files[:50]:
            upload_status = f.get("upload_status", "unknown")
            status_style = {
                "uploaded": "green",
                "failed": "red",
                "pending": "yellow",
            }.get(upload_status, "dim")
            table.add_row(
                f.get("relative_path", ""),
                _format_size(f.get("size", 0)),
                f"[{status_style}]{upload_status}[/{status_style}]",
                f.get("file_id", "-")[:18] if f.get("file_id") else "-",
                f.get("checksum", "")[:12],
            )
        console.print(table)
        if len(files) > 50:
            console.print(f"[dim]... and {len(files) - 50} more files[/]")


# =============================================================================
# PULL (with progress, partial failure policy, checksum verification)
# =============================================================================

def pull_handoff(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    handoff_id: str,
    dest: Optional[str],
    allow_partial: bool = False,
) -> int:
    """
    Download handoff files to a local folder.

    Returns exit code: 0 for success, 1 for failure/partial failure.
    """
    state = load_authenticated_state(client, store)

    try:
        h = get_handoff_service(client, store, handoff_id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return 1

    output_dir = Path(dest or f"./handoff-{handoff_id[:8]}").resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        if not console.input(f"[yellow]Directory {output_dir} exists and is not empty. Continue?[/]", default="n"):
            console.print("[yellow]Cancelled.[/]")
            return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[cyan]Pulling handoff to[/] {output_dir}...")

    # Get manifest from backend with retry
    manifest_data = h.get("manifest", {})
    manifest_file_id = h.get("manifest_file_id")

    if manifest_file_id:
        try:
            def _download_manifest():
                client.get_file(state, manifest_file_id, workspace_id=h.get("workspace_id"))
                grant = client.request_download_grant(state, manifest_file_id, workspace_id=h.get("workspace_id"))
                resp = requests.get(grant.download_url, timeout=60)
                resp.raise_for_status()
                return resp.json()

            manifest_data = with_retry(
                _download_manifest,
                max_retries=DEFAULT_MAX_RETRIES,
                initial_delay=DEFAULT_INITIAL_DELAY,
                on_retry=_on_retry_log,
            )
            console.print("[green]Downloaded manifest from storage[/]")
        except Exception as exc:
            console.print(f"[yellow]Warning:[/] Could not download manifest file, using backend metadata: {exc}")
            if not manifest_data:
                console.print("[red]Error:[/] No manifest available. Run 'cheri handoff show' to check status.")
                return 1
    elif not manifest_data:
        console.print("[red]Error:[/] No manifest available. Handoff may not have been pushed successfully.")
        return 1

    # Write manifest to destination
    manifest_path = output_dir / "cheri-handoff.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # Download files with progress
    files = manifest_data.get("files", [])
    workspace_id = h.get("workspace_id")

    downloaded = []
    failed = []
    checksum_mismatches = []
    skipped = []

    if not files:
        console.print("[yellow]No files to download.[/]")
        return 0

    console.print(f"[cyan]Downloading {len(files)} file(s)...[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Downloading file {task.description}..."),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[dim]{task.completed}/{task.total}[/]"),
        console=console,
    ) as progress:
        download_task = progress.add_task(
            "download",
            total=len(files),
        )

        for i, file_entry in enumerate(files):
            rel_path = file_entry.get("relative_path", "")
            progress.update(download_task, description=rel_path[:30])

            file_id = file_entry.get("file_id")
            expected_checksum = file_entry.get("checksum", "")

            # Skip files without file_id (not uploaded)
            if not file_id:
                skipped.append(rel_path)
                progress.update(download_task, completed=i + 1)
                console.print(f"  [dim]-[dim] {rel_path} (no file_id - not uploaded)")
                continue

            try:
                def _download_file():
                    grant = client.request_download_grant(state, file_id, workspace_id=workspace_id)
                    resp = requests.get(grant.download_url, timeout=300)
                    resp.raise_for_status()
                    return resp.content

                content = with_retry(
                    _download_file,
                    max_retries=DEFAULT_MAX_RETRIES,
                    initial_delay=DEFAULT_INITIAL_DELAY,
                    on_retry=_on_retry_log,
                )

                # Verify checksum if available
                if expected_checksum:
                    actual_checksum = hashlib.sha256(content).hexdigest()
                    if actual_checksum != expected_checksum:
                        checksum_mismatches.append({
                            "path": rel_path,
                            "expected": expected_checksum,
                            "actual": actual_checksum,
                        })
                        progress.update(download_task, completed=i + 1)
                        console.print(f"  [red]![/] {rel_path}: checksum mismatch!")
                        failed.append(rel_path)
                        continue

                # Write to destination
                dest_path = output_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(content)
                downloaded.append(rel_path)
                progress.update(download_task, completed=i + 1)
                console.print(f"  [green]+[/] {rel_path}")
            except Exception as exc:
                failed.append(rel_path)
                progress.update(download_task, completed=i + 1)
                console.print(f"  [red]![/] {rel_path}: {exc}")

    # Summary
    has_failures = failed or checksum_mismatches
    border_style = "green" if not has_failures else "yellow"
    if has_failures and not allow_partial:
        border_style = "red"

    console.print(Panel.fit(
        f"Handoff ID   : {handoff_id}\n"
        f"Downloaded   : {len(downloaded)} file(s)\n"
        f"Failed       : {len(failed)} file(s)\n"
        f"Checksum mismatches: {len(checksum_mismatches)}\n"
        f"Skipped (no file_id): {len(skipped)}\n"
        f"Destination  : {output_dir}",
        title="Pull Complete",
        border_style=border_style,
    ))

    if checksum_mismatches:
        console.print("\n[red]Checksum mismatches:[/]")
        for cm in checksum_mismatches:
            console.print(f"  {cm['path']}: expected {cm['expected'][:12]}..., got {cm['actual'][:12]}...")

    if failed:
        console.print("\n[red]Failed files:[/]")
        for path in failed:
            console.print(f"  {path}")

    # Return exit code
    if has_failures and not allow_partial:
        return 1
    return 0


# =============================================================================
# LATEST
# =============================================================================

def latest_handoff(console: Console, client: CheriClient, store: JsonCredentialStore, workspace: Optional[str]) -> None:
    """Show the most recent handoff for a workspace."""
    try:
        ws = _resolve_workspace(client, store, workspace)
        h = get_latest_handoff_service(client, store, workspace_id=ws.id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    show_handoff(console, client, store, h.get("id", ""))


# =============================================================================
# ARCHIVE
# =============================================================================

def archive_handoff(console: Console, client: CheriClient, store: JsonCredentialStore, handoff_id: str) -> None:
    """Archive a handoff (non-destructive)."""
    state = load_authenticated_state(client, store)

    try:
        h = get_handoff_service(client, store, handoff_id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    current_status = h.get("status", "unknown")
    if current_status == "archived":
        console.print(f"[yellow]Handoff {handoff_id[:16]} is already archived.[/]")
        return

    confirmed = console.input(
        f"[yellow]Archive handoff '{h.get('name', handoff_id[:16])}'?[/]\n"
        "This is a non-destructive operation. The handoff will be marked as archived.\n"
        "Continue?",
        default="n",
    )
    if confirmed.lower() not in ("y", "yes"):
        console.print("[yellow]Cancelled.[/]")
        return

    try:
        client.update_handoff(state, handoff_id, {"status": "archived"})
        console.print(f"[green]Handoff {handoff_id[:16]} archived successfully.[/]")
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] Could not archive handoff: {exc}")


# =============================================================================
# DELETE
# =============================================================================

def delete_handoff(console: Console, client: CheriClient, store: JsonCredentialStore, handoff_id: str) -> None:
    """Delete a handoff permanently (requires confirmation)."""
    state = load_authenticated_state(client, store)

    try:
        h = get_handoff_service(client, store, handoff_id)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    console.print(Panel.fit(
        f"Name     : {h.get('name', 'unknown')}\n"
        f"Status   : {h.get('status', 'unknown')}\n"
        f"Files    : {h.get('file_count', 0)}\n"
        f"Created  : {h.get('created_at', 'unknown')}",
        title=f"Delete Handoff: {handoff_id[:16]}",
        border_style="red",
    ))

    confirmed = console.input(
        f"[red]This will PERMANENTLY delete handoff '{h.get('name', handoff_id[:16])}'.[/]\n"
        "This operation cannot be undone. All associated file content will be removed.\n"
        "Type 'yes' to confirm: ",
        default="no",
    )
    if confirmed.lower() != "yes":
        console.print("[yellow]Cancelled.[/]")
        return

    try:
        # Try DELETE endpoint first, fall back to status update
        try:
            # Attempt to call delete endpoint
            client._request("delete", f"/v1/handoffs/{handoff_id}", state=state)
            console.print(f"[green]Handoff {handoff_id[:16]} deleted successfully.[/]")
        except Exception:
            # Fall back to marking as deleted via update
            client.update_handoff(state, handoff_id, {"status": "deleted"})
            console.print(f"[green]Handoff {handoff_id[:16]} marked as deleted.[/]")
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] Could not delete handoff: {exc}")


# =============================================================================
# DIFF
# =============================================================================

def diff_handoffs(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    handoff_id_1: str,
    handoff_id_2: str,
) -> None:
    """Compare two handoffs and show differences."""
    try:
        h1 = get_handoff_service(client, store, handoff_id_1)
        h2 = get_handoff_service(client, store, handoff_id_2)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return

    manifest1 = h1.get("manifest", {})
    manifest2 = h2.get("manifest", {})

    files1 = {f["relative_path"]: f for f in manifest1.get("files", [])}
    files2 = {f["relative_path"]: f for f in manifest2.get("files", [])}

    paths1 = set(files1.keys())
    paths2 = set(files2.keys())

    added = paths2 - paths1  # In h2 but not in h1
    removed = paths1 - paths2  # In h1 but not in h2
    common = paths1 & paths2

    modified = []
    for path in common:
        f1, f2 = files1[path], files2[path]
        if f1.get("checksum") != f2.get("checksum"):
            modified.append({
                "path": path,
                "old_size": f1.get("size", 0),
                "new_size": f2.get("size", 0),
                "old_checksum": f1.get("checksum", ""),
                "new_checksum": f2.get("checksum", ""),
            })

    # Calculate sizes
    total_size1 = sum(f.get("size", 0) for f in manifest1.get("files", []))
    total_size2 = sum(f.get("size", 0) for f in manifest2.get("files", []))
    size_delta = total_size2 - total_size1

    console.print(Panel.fit(
        f"Handoff 1  : {handoff_id_1[:16]} - {h1.get('name', 'unknown')}\n"
        f"Handoff 2  : {handoff_id_2[:16]} - {h2.get('name', 'unknown')}\n"
        f"Status     : {h1.get('status', 'unknown')} vs {h2.get('status', 'unknown')}",
        title="Handoff Comparison",
        border_style="cyan",
    ))

    console.print()
    table = Table(box=None, border_style="cyan", title="Summary")
    table.add_column("Metric", style="white", width=20)
    table.add_column("Handoff 1", justify="right", width=12)
    table.add_column("Handoff 2", justify="right", width=12)
    table.add_column("Delta", justify="right", width=12)
    table.add_row("Files", str(len(files1)), str(len(files2)), str(len(files2) - len(files1)))
    table.add_row("Total Size", _format_size(total_size1), _format_size(total_size2), _format_size(size_delta) if size_delta >= 0 else f"-{_format_size(abs(size_delta))}")
    table.add_row("Added", "-", str(len(added)), str(len(added)))
    table.add_row("Removed", str(len(removed)), "-", str(-len(removed)))
    table.add_row("Modified", "-", "-", str(len(modified)))
    console.print(table)

    if added:
        console.print()
        tree = Tree("[green]Added files (in handoff 2 but not in handoff 1)[/]")
        for path in sorted(added)[:20]:
            tree.add(f"[green]+[/] {path}")
        if len(added) > 20:
            tree.add(f"[dim]... and {len(added) - 20} more[/]")
        console.print(tree)

    if removed:
        console.print()
        tree = Tree("[red]Removed files (in handoff 1 but not in handoff 2)[/]")
        for path in sorted(removed)[:20]:
            tree.add(f"[red]-[/] {path}")
        if len(removed) > 20:
            tree.add(f"[dim]... and {len(removed) - 20} more[/]")
        console.print(tree)

    if modified:
        console.print()
        table = Table(box=None, border_style="yellow", title="Modified files")
        table.add_column("Path", style="white")
        table.add_column("Old Size", justify="right", width=10)
        table.add_column("New Size", justify="right", width=10)
        table.add_column("Size Delta", justify="right", width=10)
        for m in sorted(modified, key=lambda x: x["path"])[:20]:
            delta = m["new_size"] - m["old_size"]
            delta_str = f"+{_format_size(delta)}" if delta >= 0 else f"-{_format_size(abs(delta))}"
            table.add_row(m["path"], _format_size(m["old_size"]), _format_size(m["new_size"]), delta_str)
        if len(modified) > 20:
            console.print(f"[dim]... and {len(modified) - 20} more modified files[/]")
        console.print(table)


# =============================================================================
# BUNDLE
# =============================================================================

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

    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Creating bundle..."),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("", total=None)
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


# =============================================================================
# LOGS
# =============================================================================

def show_logs(
    console: Console,
    client: Optional[CheriClient],
    store: Optional[JsonCredentialStore],
    handoff_id: Optional[str] = None,
    json_output: bool = False,
) -> None:
    """Show local operation logs for handoffs."""
    from ..config import get_paths

    paths = get_paths()
    log_file = paths.config_dir / "handoff.log"

    if not log_file.exists():
        if json_output:
            console.print("[]")
        else:
            console.print("[yellow]No handoff logs found.[/]")
        return

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
    except Exception as exc:
        console.print(f"[red]Error reading logs:[/] {exc}")
        return

    # Filter by handoff_id if specified
    if handoff_id:
        lines = [line for line in lines if handoff_id in line]

    if json_output:
        import json
        logs = []
        for line in lines[-100:]:  # Last 100 entries
            try:
                # Try to parse as JSON
                logs.append(json.loads(line.strip()))
            except Exception:
                # Plain text line
                logs.append({"message": line.strip(), "raw": True})
        console.print(json.dumps(logs, indent=2))
    else:
        if not lines:
            console.print("[yellow]No logs found.[/]")
            return

        for line in lines[-50:]:  # Last 50 entries
            line = line.strip()
            if not line:
                continue
            # Simple color coding based on log level
            if "ERROR" in line or "FAILED" in line:
                console.print(f"[red]{line}[/]")
            elif "WARNING" in line or "partial_failed" in line:
                console.print(f"[yellow]{line}[/]")
            elif "SUCCESS" in line or "completed" in line:
                console.print(f"[green]{line}[/]")
            else:
                console.print(f"[dim]{line}[/]")


# =============================================================================
# UTILITIES
# =============================================================================

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