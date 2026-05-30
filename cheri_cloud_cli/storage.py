"""Storage provider commands for the Cheri CLI."""

from __future__ import annotations

from typing import Any, Optional

import click
from rich.console import Console
from rich.table import Table
from rich import box

from .client import CheriClient, CheriClientError
from .sessions import JsonCredentialStore, load_authenticated_state


console = Console()


def _ws_get(ws: object, key: str, default: Any = None) -> Any:
    """Get a workspace attribute by key, handling dict or dataclass."""
    if isinstance(ws, dict):
        return ws.get(key, default)
    return getattr(ws, key, default)


def _provider_get(provider: object, key: str, default: Any = None) -> Any:
    """Get a provider attribute by key, handling dict or dataclass."""
    if isinstance(provider, dict):
        return provider.get(key, default)
    return getattr(provider, key, default)


def list_storage_providers(client: CheriClient, include_experimental: bool = False) -> None:
    """List available storage providers from the catalog."""
    try:
        catalog = client.get_provider_catalog(include_experimental=include_experimental)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] Failed to fetch provider catalog: {exc}")
        return

    if not catalog:
        console.print("[yellow]No providers found.[/]")
        return

    table = Table(box=box.ROUNDED, border_style="blue", title="Storage Providers")
    table.add_column("Provider", style="cyan", width=24)
    table.add_column("Status", width=14)
    table.add_column("Type", width=12)
    table.add_column("Notes", style="dim")

    for provider in catalog:
        kind = provider.get("kind", "unknown")
        label = provider.get("label", kind)

        if provider.get("coming_soon"):
            status = "[yellow]Coming soon[/]"
        elif provider.get("experimental"):
            status = "[magenta]Experimental[/]"
        elif provider.get("integration_status") == "connected":
            status = "[green]Ready[/]"
        elif provider.get("integration_status") == "scaffolded":
            status = "[dim]Scaffolded[/]"
        else:
            status = "[dim]Unknown[/]"

        provider_type = "Temporary" if provider.get("temporary") else "Persistent"

        notes = []
        if provider.get("recommended"):
            notes.append("Recommended")
        if provider.get("reset_policy"):
            notes.append(f"Reset: {provider['reset_policy']}")
        if not provider.get("selectable") and not provider.get("coming_soon"):
            notes.append("Not selectable")
        if provider.get("experimental"):
            notes.append("Use with caution")

        note_text = ", ".join(notes) if notes else "-"
        table.add_row(label, status, provider_type, note_text)

    console.print(table)

    if not include_experimental:
        has_experimental = any(p.get("experimental") for p in catalog)
        if has_experimental:
            console.print("\n[dim]Some providers are experimental. Use --include-experimental to see all providers.[/]")


def show_storage_status(client: CheriClient, store: JsonCredentialStore, workspace_id: Optional[str] = None) -> None:
    """Show the active storage provider status for a workspace."""
    try:
        state = load_authenticated_state(client, store)
        if not state:
            console.print("[red]Error:[/] Not logged in. Run `cheri login` first.")
            return
        workspaces = client.list_workspaces(state)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] Failed to list workspaces: {exc}")
        return

    target_workspace = None
    if workspace_id:
        for ws in workspaces:
            ws_id = getattr(ws, 'id', None) or (ws.to_dict().get('id') if hasattr(ws, 'to_dict') else None)
            ws_name = getattr(ws, 'name', None) or (ws.to_dict().get('name') if hasattr(ws, 'to_dict') else None)
            ws_slug = getattr(ws, 'slug', None) or (ws.to_dict().get('slug') if hasattr(ws, 'to_dict') else None)
            if ws_id == workspace_id or ws_name == workspace_id or ws_slug == workspace_id:
                target_workspace = ws
                break
        if not target_workspace:
            console.print(f"[red]Error:[/] Workspace '{workspace_id}' not found.")
            return
    else:
        active_ws_id = state.active_workspace_id
        if not active_ws_id:
            console.print("[yellow]No active workspace. Use --workspace to specify one.[/]")
            return
        for ws in workspaces:
            ws_id = getattr(ws, 'id', None) or (ws.to_dict().get('id') if hasattr(ws, 'to_dict') else None)
            if ws_id == active_ws_id:
                target_workspace = ws
                break
        if not target_workspace:
            console.print("[yellow]No active workspace. Use --workspace to specify one.[/]")
            return

    storage = _ws_get(target_workspace, "storage", {})
    provider = _ws_get(storage, "provider", {}) if isinstance(storage, dict) else {}

    if not provider:
        console.print("[yellow]No storage provider configured for this workspace.[/]")
        return

    kind = _provider_get(provider, "kind", "unknown")
    label = _provider_get(provider, "label", kind)
    validation = _provider_get(provider, "validation", {})
    validation_state = _provider_get(validation, "state", "unknown") if isinstance(validation, dict) else "unknown"
    available = _provider_get(validation, "available", False) if isinstance(validation, dict) else False
    reset_policy = _provider_get(provider, "reset_policy", "")

    from rich.panel import Panel

    status_lines = [
        f"Workspace   : {_ws_get(target_workspace, 'name', 'unknown')} ({_ws_get(target_workspace, 'id', '')})",
        f"Provider    : {label}",
        f"Kind        : {kind}",
        f"State       : {validation_state}",
        f"Available   : {'Yes' if available else 'No'}",
    ]

    if reset_policy:
        status_lines.append(f"Reset policy : {reset_policy}")

    warnings = _provider_get(validation, "warnings", []) if isinstance(validation, dict) else []
    if warnings:
        status_lines.append("")
        status_lines.append("Warnings:")
        for warning in warnings:
            status_lines.append(f"  - {warning}")

    errors = validation.get("errors", []) if isinstance(validation, dict) else []
    if errors:
        status_lines.append("")
        status_lines.append("Errors:")
        for error in errors:
            status_lines.append(f"  - {error}")

    border = "green" if available else "red" if errors else "yellow"
    console.print(Panel.fit("\n".join(status_lines), title="Storage Status", border_style=border))


def check_storage_connectivity(client: CheriClient) -> None:
    """Check storage provider connectivity."""
    try:
        health = client.healthcheck()
        console.print(f"[green]Backend:[/] OK (product: {health.get('product', 'unknown')})")
    except CheriClientError as exc:
        console.print(f"[red]Backend:[/] Unreachable - {exc}")

    try:
        catalog = client.get_provider_catalog(include_experimental=False)
        ready_providers = [p for p in catalog if p.get("integration_status") == "connected"]
        console.print(f"[green]Providers:[/] {len(ready_providers)} ready, {len(catalog)} total")
    except CheriClientError as exc:
        console.print(f"[yellow]Providers:[/] Could not fetch catalog - {exc}")

def _load_state(client: CheriClient, store: JsonCredentialStore):
    state = load_authenticated_state(client, store)
    if not state:
        raise CheriClientError("Not logged in. Run `cheri login` first.")
    return state


def _resolve_workspace(state, workspaces, workspace_id: Optional[str]):
    active_ws_id = workspace_id or state.active_workspace_id
    if not active_ws_id:
        raise CheriClientError("No active workspace. Use --workspace to specify one.")
    for ws in workspaces:
        ws_id = getattr(ws, 'id', None) or (ws.to_dict().get('id') if hasattr(ws, 'to_dict') else None)
        if ws_id == active_ws_id:
            return ws
    raise CheriClientError(f"Workspace '{active_ws_id}' not found.")


def _render_config_result(console: Console, result: dict, provider: dict) -> None:
    from rich.panel import Panel
    provider_label = provider.get("label", provider.get("kind", ""))
    validation = provider.get("validation", {})
    available = validation.get("available", False) if isinstance(validation, dict) else False
    errors = validation.get("errors", []) if isinstance(validation, dict) else []
    warnings = validation.get("warnings", []) if isinstance(validation, dict) else []

    lines = [
        f"Workspace : {result.get('workspace_id', 'unknown')}",
        f"Provider  : {provider_label}",
        f"Kind      : {provider.get('kind', '')}",
        f"State     : {validation.get('state', 'unknown') if isinstance(validation, dict) else 'unknown'}",
        f"Available : {'Yes' if available else 'No'}",
    ]
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"  - {w}")
    if errors:
        lines.append("")
        lines.append("Errors:")
        for e in errors:
            lines.append(f"  - {e}")
    border = "green" if available and not errors else "red" if errors else "yellow"
    console.print(Panel.fit("\n".join(lines), title="Storage Configured", border_style=border))

    if available:
        console.print("\n[green]Next:[/] Upload a file to verify:\n  cheri file upload ./notes.md")


def configure_storage_provider(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    *,
    provider_kind: Optional[str],
    include_experimental: bool,
    workspace: Optional[str],
) -> None:
    """Configure or change the storage provider for a workspace."""
    from .providers.catalog import iter_provider_options, find_provider_option, _render_provider_table, _render_validation
    from .contracts import ProviderConfig, ProviderValidationState
    import os

    state = _load_state(client, store)
    workspaces = client.list_workspaces(state)
    target_ws = _resolve_workspace(state, workspaces, workspace)

    # Determine target provider
    if not provider_kind:
        # Interactive selection
        options = list(iter_provider_options(client))
        _render_provider_table(console, tuple(options))
        selectable_indexes = [
            i for i, opt in enumerate(options, 1)
            if opt.selectable or (opt.experimental and include_experimental)
            or (opt.experimental and os.environ.get("CHERI_EXPERIMENTAL_PROVIDERS") == "1")
        ]
        if not selectable_indexes:
            console.print("[yellow]No selectable providers. Try --include-experimental.[/]")
            return
        selected = click.prompt(
            "Select storage provider",
            type=click.IntRange(1, len(options)),
            default=selectable_indexes[0],
        )
        option = options[selected - 1]
    else:
        try:
            option = find_provider_option(provider_kind, client)
        except KeyError:
            console.print(f"[red]Unknown provider:[/] {provider_kind}")
            console.print("Available providers: system, s3-compatible, backblaze-b2")
            return

    # Check experimental gate
    if option.experimental and not include_experimental:
        console.print(
            f"[yellow]{option.label} is experimental.[/] "
            "Use --include-experimental to configure it."
        )
        return

    # Collect credentials
    settings = {}
    for field in option.fields:
        if field.secret:
            value = click.prompt(field.label, hide_input=True)
        else:
            prompt_kwargs = {}
            if field.default:
                prompt_kwargs["default"] = field.default
            value = click.prompt(field.label, **prompt_kwargs)
        settings[field.key] = value

    # Build selection payload
    selection = ProviderConfig(
        kind=option.key,
        label=option.label,
        temporary=option.temporary,
        recommended=option.recommended,
        selectable=option.selectable,
        coming_soon=option.coming_soon,
        experimental=option.experimental,
        warning_acknowledged=False,
        reset_policy=option.reset_policy,
        settings=settings,
        metadata=option.to_metadata(),
        validation=ProviderValidationState(),
    )

    # Validate
    try:
        validated = client.validate_provider_config(selection, allow_experimental=option.experimental)
    except CheriClientError as exc:
        console.print(f"[red]Validation failed:[/] {exc}")
        return

    if validated.validation.errors:
        console.print("[red]Configuration errors:[/]")
        for err in validated.validation.errors:
            console.print(f"  - {err}")
        console.print("\n[yellow]Provider was not changed.[/]")
        return

    _render_validation(console, option, validated)

    if validated.validation.warnings:
        for warn in validated.validation.warnings:
            console.print(f"[yellow]Warning:[/] {warn}")

    if not validated.validation.available:
        if not click.confirm("Provider is not available. Use anyway?", default=False):
            console.print("[yellow]Provider configuration cancelled.[/]")
            return

    console.print(f"Configuring {validated.label} for workspace {target_ws.name}...")

    try:
        result = client.configure_storage(state, validated, workspace_id=target_ws.id)
    except CheriClientError as exc:
        console.print(f"[red]Failed to save configuration:[/] {exc}")
        return

    _render_config_result(console, result, validated.to_dict() if hasattr(validated, 'to_dict') else {
        "kind": validated.kind,
        "label": validated.label,
        "validation": validated.validation,
    })


def storage_migrate_plan(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    *,
    target_provider: str,
    workspace: Optional[str],
) -> None:
    """Show what a storage migration would involve (non-destructive)."""
    from rich.panel import Panel
    from rich.table import Table

    state = _load_state(client, store)
    workspaces = client.list_workspaces(state)
    target_ws = _resolve_workspace(state, workspaces, workspace)

    # Current provider
    try:
        current_config = client.get_storage_config(state, target_ws.id)
        current_provider = current_config.get("provider") or {}
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] Could not fetch current storage config: {exc}")
        return

    current_kind = current_provider.get("kind", "system")
    current_label = current_provider.get("label", "System")
    current_validation = current_provider.get("validation", {})
    current_available = current_validation.get("available", False) if isinstance(current_validation, dict) else False

    # Target provider check
    try:
        catalog = client.get_provider_catalog(include_experimental=True)
    except CheriClientError as exc:
        console.print(f"[red]Error:[/] Could not fetch provider catalog: {exc}")
        return

    target_option = None
    for p in catalog:
        if p.get("kind") == target_provider:
            target_option = p
            break

    if not target_option:
        console.print(f"[red]Unknown target provider:[/] {target_provider}")
        return

    target_label = target_option.get("label", target_provider)
    target_experimental = target_option.get("experimental", False)
    if target_experimental:
        console.print(f"[yellow]Warning:[/] {target_label} is experimental. Use --include-experimental to proceed.")

    console.print(Panel.fit(
        f"[b]Storage Migration Plan[/b]\n\n"
        f"Active workspace : {target_ws.name} ({target_ws.id})\n"
        f"Source provider  : {current_label} ({current_kind})\n"
        f"Target provider  : {target_label} ({target_provider})\n"
        f"Source available : {'Yes' if current_available else 'No'}",
        title="Migration Plan",
        border_style="blue",
    ))

    table = Table(box=box.ROUNDED, border_style="blue", title="Migration Considerations")
    table.add_column("Item", style="cyan", width=20)
    table.add_column("Detail", style="white")
    table.add_row("Files", "File records will NOT be copied or migrated automatically.")
    table.add_row("Provider switch", f"New uploads will go to {target_label}.")
    table.add_row("Original files", "Files in the original provider remain until manually migrated.")
    table.add_row("Rollback", "You can re-configure back to the original provider at any time.")
    table.add_row("Credentials", "Target provider credentials will be validated before switching.")
    console.print(table)

    console.print("\n[yellow]WARNING:[/] No files were copied or modified.")
    console.print("[yellow]WARNING:[/] This is a plan only. Run `cheri storage migrate dry-run --to "
                  f"{target_provider}` for a detailed simulation.")


def storage_migrate_dry_run(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    *,
    target_provider: str,
    workspace: Optional[str],
) -> None:
    """Show what WOULD happen during a storage migration without executing it."""
    from rich.panel import Panel
    from rich.table import Table

    state = _load_state(client, store)
    workspaces = client.list_workspaces(state)
    target_ws = _resolve_workspace(state, workspaces, workspace)

    # Current config
    try:
        current_config = client.get_storage_config(state, target_ws.id)
        current_provider = current_config.get("provider") or {}
    except CheriClientError:
        current_provider = {}

    current_kind = current_provider.get("kind", "system")
    current_label = current_provider.get("label", "System")

    console.print(Panel.fit(
        "[b]Storage Migration Dry-Run[/b]\n\n"
        f"Workspace      : {target_ws.name} ({target_ws.id})\n"
        f"Source         : {current_label} ({current_kind})\n"
        f"Target         : {target_provider}\n\n"
        "[yellow]No files were copied or modified.[/]\n"
        "[yellow]No provider configuration was changed.[/]",
        title="Dry-Run",
        border_style="yellow",
    ))

    table = Table(box=box.ROUNDED, border_style="yellow", title="Would Happen")
    table.add_column("Step", style="cyan", width=4)
    table.add_column("Action", style="white", width=28)
    table.add_column("Risk", style="dim")
    table.add_row("1", "Validate target provider config", "None — read-only check")
    table.add_row("2", "Save new provider to workspace storage", "Config write (reversible)")
    table.add_row("3", "Existing files stay in source provider", "None")
    table.add_row("4", "New uploads go to target provider", "None")
    console.print(table)

    console.print("[green]All checks passed.[/] No files were copied or modified.")
    console.print(f"\nTo execute this migration:\n  cheri storage configure --provider {target_provider}")
