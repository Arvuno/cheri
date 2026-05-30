"""Workspace selection and creation flows."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..client import CheriClient, CheriClientError
from ..contracts import AuthState, WorkspaceSummary
from ..providers import describe_provider, prompt_for_provider
from ..sessions import JsonCredentialStore, load_authenticated_state


def _render_workspaces(console: Console, workspaces, active_workspace_id: str) -> None:
    table = Table(box=box.ROUNDED, border_style="cyan", title="Accessible Workspaces")
    table.add_column("Active", width=8)
    table.add_column("Name", style="white", width=26)
    table.add_column("Id", style="dim", width=18)
    table.add_column("Role", width=10)
    table.add_column("Provider", width=28)
    table.add_column("Joined", style="dim", width=20)
    for workspace in workspaces:
        table.add_row(
            "*" if workspace.id == active_workspace_id else "",
            workspace.name,
            workspace.id,
            workspace.role,
            describe_provider(workspace.provider),
            workspace.joined_at[:19],
        )
    console.print(table)


def resolve_workspace_reference(state: AuthState, identifier: Optional[str]) -> Optional[WorkspaceSummary]:
    if not identifier:
        return state.active_workspace
    normalized = str(identifier).strip()
    if not normalized:
        return state.active_workspace
    return next((workspace for workspace in state.workspaces if workspace.matches(normalized)), None)


def resolve_workspace_id(state: AuthState, identifier: Optional[str]) -> Optional[str]:
    workspace = resolve_workspace_reference(state, identifier)
    if identifier and not workspace:
        raise click.ClickException(f"Workspace not found: {identifier}")
    return workspace.id if workspace else None


def describe_workspace_target(state: AuthState, identifier: Optional[str]) -> str:
    workspace = resolve_workspace_reference(state, identifier)
    if workspace:
        return workspace.name
    return "active workspace"


def list_workspaces(console: Console, client: CheriClient, store: JsonCredentialStore) -> None:
    state = load_authenticated_state(client, store)
    _render_workspaces(console, state.workspaces, state.active_workspace_id)


def use_workspace(console: Console, client: CheriClient, store: JsonCredentialStore, *, identifier: str) -> None:
    state = load_authenticated_state(client, store)
    target = resolve_workspace_reference(state, identifier)
    if not target:
        raise click.ClickException(f"Workspace not found: {identifier}")
    updated = client.select_workspace(state, identifier=target.id)
    store.save(updated)
    console.print(f"[green]Active workspace:[/] [white]{target.name}[/] ({target.id})")
    _render_workspaces(console, updated.workspaces, updated.active_workspace_id)


def create_workspace(console: Console, client: CheriClient, store: JsonCredentialStore, *, name: str) -> None:
    state = load_authenticated_state(client, store)
    existing = resolve_workspace_reference(state, name)
    if existing:
        updated = client.select_workspace(state, identifier=existing.id)
        store.save(updated)
        console.print(f"[green]Workspace already exists.[/] Using [white]{existing.name}[/] ({existing.id}).")
        _render_workspaces(console, updated.workspaces, updated.active_workspace_id)
        return

    provider = prompt_for_provider(console, client)
    updated = client.select_workspace(
        state,
        identifier=name,
        create_if_missing=True,
        provider=provider,
    )
    store.save(updated)
    created = resolve_workspace_reference(updated, name)
    created_label = created.name if created else name
    console.print(f"[green]Created and selected[/] [white]{created_label}[/].")
    _render_workspaces(console, updated.workspaces, updated.active_workspace_id)


def manage_workspace(console: Console, client: CheriClient, store: JsonCredentialStore, *, name: Optional[str]) -> None:
    if not name:
        state = load_authenticated_state(client, store)
        _render_workspaces(console, state.workspaces, state.active_workspace_id)
        return
    create_workspace(console, client, store, name=name)


def join_workspace(console: Console, client: CheriClient, store: JsonCredentialStore, *, invite_code: str) -> None:
    state = load_authenticated_state(client, store)
    updated = client.accept_team_invite(state, invite_code)
    store.save(updated)
    workspace = updated.active_workspace
    console.print(
        Panel.fit(
            f"Joined workspace : {(workspace.name if workspace else '-')}\n"
            f"Active workspace : {updated.active_workspace_id}\n"
            f"Accessible total : {len(updated.workspaces)}",
            title="Workspace Joined",
            border_style="green",
        )
    )
    _render_workspaces(console, updated.workspaces, updated.active_workspace_id)


def _get_storage_info(client: CheriClient, store: JsonCredentialStore, workspace_id: str) -> Dict[str, Any]:
    """Get storage information for a workspace."""
    try:
        auth_state = load_authenticated_state(client, store)
        config = client.get_storage_config(auth_state, workspace_id)
        return config
    except CheriClientError:
        return {}


def _get_member_count(client: CheriClient, store: JsonCredentialStore, workspace_id: str) -> Optional[int]:
    """Get member count for a workspace."""
    try:
        auth_state = load_authenticated_state(client, store)
        team = client.list_team(auth_state, workspace_id)
        return len(team.members) if hasattr(team, 'members') else None
    except CheriClientError:
        return None


def _get_file_count(client: CheriClient, store: JsonCredentialStore, workspace_id: str) -> Optional[int]:
    """Get file count for a workspace."""
    try:
        auth_state = load_authenticated_state(client, store)
        files = client.list_files(auth_state, workspace_id)
        return len(files) if files else None
    except CheriClientError:
        return None


def _get_active_tasks(workspace_id: str) -> List[Dict[str, Any]]:
    """Get active tasks for a workspace."""
    try:
        from ..task.registry import TaskRegistry
        registry = TaskRegistry()
        tasks = registry.list_tasks()
        workspace_tasks = [t for t in tasks if t.get("workspace_id") == workspace_id]
        running = [t for t in workspace_tasks if t.get("status") == "running"]
        return running
    except Exception:
        return []


def workspace_status(console: Console, client: CheriClient, store: JsonCredentialStore, *, json_output: bool = False) -> None:
    """Show detailed status for the active workspace."""
    state = store.load()

    if not state:
        if json_output:
            console.print(json.dumps({"error": "Not logged in"}, indent=2))
        else:
            console.print("[yellow]Not logged in.[/] Run [white]cheri login[/] first.")
        return

    if not state.active_workspace:
        if json_output:
            console.print(json.dumps({
                "logged_in": True,
                "active_workspace": None,
                "message": "No active workspace. Use 'cheri workspace create' or 'cheri workspace join'.",
            }, indent=2))
        else:
            console.print("[yellow]No active workspace.[/]")
            console.print("Use [white]cheri workspace create[/] or [white]cheri workspace join[/] to set one up.")
        return

    workspace = state.active_workspace
    auth_state = load_authenticated_state(client, store)

    # Gather workspace info
    storage_info = _get_storage_info(client, store, workspace.id)
    member_count = _get_member_count(client, store, workspace.id)
    file_count = _get_file_count(client, store, workspace.id)
    active_tasks = _get_active_tasks(workspace.id)

    # Gather recent activity
    recent_items = []
    try:
        activity = client.list_activity(auth_state, workspace.id)
        if activity and hasattr(activity, 'items'):
            recent_items = activity.items[:5] if activity.items else []
    except CheriClientError:
        pass

    if json_output:
        output = {
            "logged_in": True,
            "username": state.user.username if state.user else None,
            "active_workspace": {
                "id": workspace.id,
                "name": workspace.name,
                "role": workspace.role,
                "provider": storage_info.get("kind", workspace.provider.kind if hasattr(workspace, 'provider') else None),
                "provider_label": storage_info.get("provider_label", describe_provider(workspace.provider) if hasattr(workspace, 'provider') else None),
                "validation_state": storage_info.get("validation", {}).get("state", "unknown") if storage_info else "unknown",
                "member_count": member_count,
                "file_count": file_count,
            },
            "active_tasks": [
                {"id": t.get("id"), "target": t.get("target_path"), "mode": t.get("mode")}
                for t in active_tasks
            ],
            "recent_activity_count": len(recent_items),
            "warnings": [
                {"code": "upload-only", "message": "Cheri is upload-only; bidirectional sync is not implemented."},
                {"code": "system-reset", "message": "System provider data resets daily."} if storage_info.get("kind") == "system" else None,
            ],
        }
        output["warnings"] = [w for w in output["warnings"] if w is not None]
        console.print(json.dumps(output, indent=2))
        return

    # Human-readable output
    console.print(Panel.fit(
        f"[bold cyan]{workspace.name}[/] [dim]({workspace.id})[/]",
        title="Active Workspace",
        border_style="cyan",
    ))
    console.print()

    # Basic info table
    info_table = Table(box=None, border_style=None, show_header=False)
    info_table.add_column("Label", width=20, style="dim")
    info_table.add_column("Value", width=50)

    info_table.add_row("Current user", state.user.username if state.user else "-")
    info_table.add_row("Role", workspace.role or "-")
    info_table.add_row("Workspace ID", workspace.id)

    if member_count is not None:
        info_table.add_row("Members", str(member_count))
    if file_count is not None:
        info_table.add_row("Files", str(file_count))

    console.print(info_table)
    console.print()

    # Storage info
    if storage_info:
        provider_kind = storage_info.get("kind", "unknown")
        provider_label = storage_info.get("provider_label", provider_kind)
        validation = storage_info.get("validation", {})
        validation_state = validation.get("state", "unknown")

        status_icon = {
            "ready": "[green]✓[/]",
            "not_ready": "[yellow]![/]",
            "error": "[red]✗[/]",
        }.get(validation_state, "[dim]?[/]")

        console.print(f"Storage Provider: {status_icon} {provider_label} [dim]({validation_state})[/]")
        console.print()
    else:
        console.print("[dim]Storage provider: unknown[/]")
        console.print()

    # Active tasks
    if active_tasks:
        task_table = Table(box=box.ROUNDED, border_style="cyan", title="Active Tasks")
        task_table.add_column("Task Id", style="cyan", width=16)
        task_table.add_column("Target", style="white", width=40)
        task_table.add_column("Mode", width=16)
        for task in active_tasks:
            task_table.add_row(
                task.get("id", "-"),
                task.get("target_path", "-"),
                task.get("mode", "-"),
            )
        console.print(task_table)
    else:
        console.print("[dim]No active tasks[/]")
    console.print()

    # Recent activity
    if recent_items:
        console.print("[bold]Recent Activity:[/]")
        for item in recent_items:
            action = getattr(item, 'action', 'unknown')
            path = getattr(item, 'path', '-')
            time = getattr(item, 'created_at', '')[:19]
            console.print(f"  [dim]{time}[/] {action}: {path}")
    console.print()

    # Warnings
    warnings = []
    warnings.append("[yellow]Upload-only sync:[/] Cheri is upload-only; bidirectional sync is not implemented.")
    if storage_info.get("kind") == "system":
        warnings.append("[yellow]System provider:[/] Data managed by System provider resets daily.")

    if warnings:
        console.print(Panel.fit(
            "\n".join(f"  {w}" for w in warnings),
            title="Warnings",
            border_style="yellow",
        ))

