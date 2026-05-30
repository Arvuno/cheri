"""Cheri init - new user onboarding flow."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .client import CheriClient, CheriClientError
from .config import get_base_url, load_cli_settings, set_saved_api_url
from .providers import prompt_for_provider
from .sessions import JsonCredentialStore, load_authenticated_state


console = Console()


def _check_backend_api(client: CheriClient) -> bool:
    """Check if the backend API is reachable."""
    try:
        client.healthcheck()
        return True
    except CheriClientError:
        return False


def _check_auth_state(store: JsonCredentialStore) -> tuple[bool, Optional[str]]:
    """Check if the user is logged in. Returns (is_logged_in, username)."""
    try:
        state = store.load()
        if state and state.session_token:
            return True, state.user.username if state.user else None
    except Exception:
        pass
    return False, None


def _get_default_api_url() -> str:
    """Get the default API URL."""
    return get_base_url()


def _welcome_panel() -> None:
    """Display the welcome panel."""
    console.print(
        Panel.fit(
            "[bold cyan]Cheri[/] — CLI-first workspace sync for developer teams\n\n"
            "Sync files and automate uploads across your team. "
            "All uploads are encrypted and stored securely.",
            title="Welcome to Cheri",
            border_style="cyan",
        )
    )


def _show_api_check(api_url: str, is_reachable: bool) -> None:
    """Show the API URL check result."""
    if is_reachable:
        console.print(f"[green]✓[/] Backend API: [white]{api_url}[/]")
    else:
        console.print(
            f"[yellow]![/] Backend API: [white]{api_url}[/] [dim](not reachable)[/]\n"
            "  This may affect some features. Run [white]cheri doctor[/] to diagnose."
        )


def _ask_api_url(non_interactive: bool, default_url: str) -> Optional[str]:
    """Ask for API URL if non-interactive mode allows it."""
    if non_interactive:
        return default_url

    use_default = click.confirm(
        f"Use [white]{default_url}[/] as the backend API?",
        default=True,
    )
    if use_default:
        return default_url

    custom_url = click.prompt(
        "Enter the backend API URL",
        default="https://cheri.parapanteri.com",
    ).strip()
    return custom_url if custom_url else default_url


def _show_auth_state(is_logged_in: bool, username: Optional[str]) -> None:
    """Show authentication state."""
    if is_logged_in and username:
        console.print(f"[green]✓[/] Logged in as: [white]{username}[/]")
    else:
        console.print("[yellow]![/] Not logged in")


def _handle_auth(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    non_interactive: bool,
    force_register: bool = False,
) -> tuple[bool, Optional[str]]:
    """Handle authentication flow. Returns (should_continue, username)."""
    is_logged_in, username = _check_auth_state(store)

    if is_logged_in:
        console.print(f"[green]✓[/] Already logged in as [white]{username}[/]")
        if not non_interactive:
            if click.confirm("Continue with this account?", default=True):
                return True, username
        return True, username

    if non_interactive and not force_register:
        console.print("[yellow]![/] Not logged in. Use --register or --login to authenticate.")
        return False, None

    console.print()
    auth_choice = click.prompt(
        "Choose an action",
        type=click.Choice(["1", "2", "3"], case_sensitive=False),
        default="1",
        show_choices=False,
    )

    if auth_choice == "1":
        _do_register(console, client, store)
        state = store.load()
        return True, state.user.username if state and state.user else None
    elif auth_choice == "2":
        _do_login(console, client, store)
        state = store.load()
        return True, state.user.username if state and state.user else None
    else:
        console.print("[yellow]Skipping authentication.[/] Some features will be unavailable.")
        return False, None


def _do_register(console: Console, client: CheriClient, store: JsonCredentialStore) -> None:
    """Perform registration."""
    username = click.prompt("Username").strip()
    workspace_name = click.prompt("Initial workspace name", default=f"{username} workspace").strip()
    provider = prompt_for_provider(console, client)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task_description}"),
        console=console,
    ) as progress:
        progress.add_task("Creating account...", total=None)
        try:
            state = client.register(username=username, workspace_name=workspace_name, provider=provider)
        except CheriClientError as e:
            console.print(f"[red]Registration failed:[/] {e}")
            raise click.Abort()

    console.print(
        Panel.fit(
            f"Your bootstrap secret:\n\n[yellow]{state.bootstrap_secret}[/]\n\n"
            "Save this securely. You will need it to log in on other devices.",
            title="Bootstrap Secret",
            border_style="yellow",
        )
    )

    save = click.confirm("Save credentials locally?", default=True)
    if save:
        persist_bootstrap = click.confirm(
            "Also save bootstrap secret for future logins?",
            default=False,
        )
        store.save(state, persist_bootstrap_secret=persist_bootstrap)
    else:
        console.print("[yellow]Note:[/] You will need your bootstrap secret to log in again.")


def _do_login(console: Console, client: CheriClient, store: JsonCredentialStore) -> None:
    """Perform login."""
    username = click.prompt("Username").strip()
    has_secret = click.confirm("Do you have a bootstrap secret?", default=True)

    if has_secret:
        bootstrap_secret = click.prompt("Bootstrap secret", hide_input=True).strip()
    else:
        console.print("[yellow]No bootstrap secret?[/] Run [white]cheri register[/] to create an account.")
        raise click.Abort()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task_description}"),
        console=console,
    ) as progress:
        progress.add_task("Logging in...", total=None)
        try:
            state = client.login(username=username, bootstrap_secret=bootstrap_secret)
        except CheriClientError as e:
            console.print(f"[red]Login failed:[/] {e}")
            raise click.Abort()

    save = click.confirm("Save credentials locally?", default=True)
    if save:
        persist_bootstrap = click.confirm(
            "Also save bootstrap secret for future logins?",
            default=False,
        )
        store.save(state, persist_bootstrap_secret=persist_bootstrap)


def _handle_workspace(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    non_interactive: bool,
    workspace_name: Optional[str],
) -> tuple[bool, Optional[str]]:
    """Handle workspace creation/join. Returns (has_workspace, workspace_name)."""
    if non_interactive and workspace_name:
        _create_workspace(console, client, store, workspace_name)
        return True, workspace_name

    if non_interactive:
        console.print("[yellow]Skipping workspace creation.[/] Use --workspace to specify.")
        return False, None

    state = store.load()
    if state and state.active_workspace:
        console.print(
            f"[green]✓[/] Active workspace: [white]{state.active_workspace.name}[/]"
        )
        if click.confirm("Create or join another workspace?", default=False):
            pass
        else:
            return True, state.active_workspace.name

    console.print()
    choice = click.prompt(
        "Workspace action",
        type=click.Choice(["1", "2", "3"], case_sensitive=False),
        default="1",
        show_choices=False,
    )

    if choice == "1":
        name = click.prompt("Workspace name").strip()
        _create_workspace(console, client, store, name)
        return True, name
    elif choice == "2":
        invite_code = click.prompt("Invite code (e.g. CHR-TEAM-8X2K91QZ)").strip()
        _join_workspace(console, client, store, invite_code)
        return True, None
    else:
        console.print("[yellow]Skipping workspace selection.[/]")
        return False, None


def _create_workspace(console: Console, client: CheriClient, store: JsonCredentialStore, name: str) -> None:
    """Create a new workspace."""
    state = load_authenticated_state(client, store)
    provider = prompt_for_provider(console, client)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task_description}"),
        console=console,
    ) as progress:
        progress.add_task("Creating workspace...", total=None)
        try:
            updated = client.select_workspace(
                state,
                identifier=name,
                create_if_missing=True,
                provider=provider,
            )
            store.save(updated)
        except CheriClientError as e:
            console.print(f"[red]Workspace creation failed:[/] {e}")
            raise click.Abort()

    console.print(f"[green]✓[/] Created workspace: [white]{name}[/]")


def _join_workspace(console: Console, client: CheriClient, store: JsonCredentialStore, invite_code: str) -> None:
    """Join a workspace via invite code."""
    state = load_authenticated_state(client, store)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task_description}"),
        console=console,
    ) as progress:
        progress.add_task("Joining workspace...", total=None)
        try:
            updated = client.accept_team_invite(state, invite_code)
            store.save(updated)
        except CheriClientError as e:
            console.print(f"[red]Failed to join workspace:[/] {e}")
            raise click.Abort()

    console.print("[green]✓[/] Joined workspace via invite code")


def _show_storage_provider(console: Console, client: CheriClient, store: JsonCredentialStore) -> None:
    """Show the current storage provider."""
    try:
        state = store.load()
        if not state or not state.active_workspace_id:
            console.print("[dim]No active workspace.[/]")
            return

        auth_state = load_authenticated_state(client, store)
        config = client.get_storage_config(auth_state, state.active_workspace_id)
        provider_label = config.get("provider_label", config.get("kind", "unknown"))
        validation_state = config.get("validation", {}).get("state", "unknown")

        state_label = {
            "ready": "[green]✓[/]",
            "not_ready": "[yellow]![/]",
            "error": "[red]✗[/]",
        }.get(validation_state, "[dim]?[/]")

        console.print(f"{state_label} Storage provider: [white]{provider_label}[/]")

        if validation_state != "ready":
            console.print("  [dim]Run [white]cheri doctor[/] for details[/]")
    except CheriClientError:
        console.print("[dim]Could not fetch storage provider info[/]")


def _offer_upload(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    non_interactive: bool,
    skip_upload: bool,
) -> None:
    """Offer to upload a file."""
    if skip_upload:
        return

    if non_interactive:
        console.print("[dim]Skipping upload offer (non-interactive).[/]")
        return

    state = store.load()
    if not state or not state.active_workspace:
        console.print("[dim]No active workspace - skipping upload offer.[/]")
        return

    console.print()
    if click.confirm("Upload a file now?", default=False):
        path_str = click.prompt(
            "File path to upload",
            default=".",
        ).strip()

        if not path_str or path_str == ".":
            console.print("[yellow]No file specified.[/] Use [white]cheri file upload <path>[/] later.")
            return

        path = Path(path_str)
        if not path.exists():
            console.print(f"[red]File not found:[/] {path}")
            console.print("Use [white]cheri file upload <path>[/] to upload a file later.")
            return

        from .files import upload_file
        try:
            upload_file(console, client, store, path)
            console.print("[green]✓[/] File uploaded successfully.")
        except CheriClientError as e:
            console.print(f"[yellow]Upload failed:[/] {e}")
            console.print("Use [white]cheri file upload <path>[/] to try again.")


def _offer_task_creation(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    non_interactive: bool,
    skip_task: bool,
) -> None:
    """Offer to create a watch task."""
    if skip_task:
        return

    if non_interactive:
        console.print("[dim]Skipping task creation offer (non-interactive).[/]")
        return

    state = store.load()
    if not state or not state.active_workspace:
        console.print("[dim]No active workspace - skipping task creation offer.[/]")
        return

    console.print()
    if click.confirm("Create a watch task for automatic uploads?", default=False):
        console.print("\nRun [white]cheri task create --interactive[/] to create a task.\n")


def _success_screen(console: Console, username: Optional[str], workspace_name: Optional[str]) -> None:
    """Show the final success screen."""
    items = []
    if username:
        items.append(f"Logged in as    : [white]{username}[/]")
    if workspace_name:
        items.append(f"Active workspace: [white]{workspace_name}[/]")

    items.extend([
        "",
        "[bold]Next steps:[/]",
        "",
        "  [white]cheri workspace status[/]    View workspace information",
        "  [white]cheri file upload <path>[/]   Upload a file",
        "  [white]cheri task create --interactive[/]  Create a watch task",
        "  [white]cheri activity[/]           View recent activity",
        "  [white]cheri doctor[/]             Diagnose configuration",
        "",
    ])

    panel_content = "\n".join(items) if items else "\n[bold]Next steps:[/]\n\n  [white]cheri doctor[/]  Diagnose configuration\n"
    console.print(
        Panel.fit(
            panel_content,
            title="Cheri Initialized",
            border_style="green",
        )
    )


def run_init(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    *,
    non_interactive: bool = False,
    skip_upload: bool = False,
    skip_task: bool = False,
    workspace: Optional[str] = None,
    api_url: Optional[str] = None,
    register: bool = False,
) -> None:
    """
    Run the Cheri initialization flow.

    Args:
        non_interactive: Run without interactive prompts
        skip_upload: Skip the upload offer
        skip_task: Skip the task creation offer
        workspace: Workspace name to create or use
        api_url: API URL to use
        register: Force registration
    """
    _welcome_panel()
    console.print()

    # Step 1: API URL check
    default_url = _get_default_api_url()
    current_settings = load_cli_settings()
    effective_url = api_url or current_settings.api_url or default_url

    api_reachable = _check_backend_api(client)
    _show_api_check(effective_url, api_reachable)

    if api_url and api_url != current_settings.api_url:
        try:
            saved_url = set_saved_api_url(api_url)
            console.print(f"[green]✓[/] API URL saved: [white]{saved_url}[/]")
        except Exception as e:
            console.print(f"[yellow]![/] Could not save API URL: {e}")

    console.print()

    # Step 2: Auth check
    is_logged_in, username = _check_auth_state(store)
    _show_auth_state(is_logged_in, username)

    if not is_logged_in:
        should_continue, username = _handle_auth(
            console, client, store, non_interactive, force_register=register
        )
        if not should_continue:
            _success_screen(console, None, None)
            return

    console.print()

    # Step 3: Workspace selection
    has_workspace, ws_name = _handle_workspace(
        console, client, store, non_interactive, workspace
    )

    if not has_workspace:
        _success_screen(console, username, None)
        return

    console.print()

    # Step 4: Storage provider info
    _show_storage_provider(console, client, store)
    console.print()

    # Step 5: Upload offer
    _offer_upload(console, client, store, non_interactive, skip_upload)
    console.print()

    # Step 6: Task creation offer
    _offer_task_creation(console, client, store, non_interactive, skip_task)

    # Final success screen
    _success_screen(console, username, ws_name or (store.load().active_workspace.name if store.load() else None))


def init(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    *,
    non_interactive: bool = False,
    skip_upload: bool = False,
    skip_task: bool = False,
    workspace: Optional[str] = None,
    api_url: Optional[str] = None,
    register: bool = False,
) -> None:
    """CLI entry point for cheri init."""
    try:
        run_init(
            console,
            client,
            store,
            non_interactive=non_interactive,
            skip_upload=skip_upload,
            skip_task=skip_task,
            workspace=workspace,
            api_url=api_url,
            register=register,
        )
    except click.Abort:
        console.print("\n[yellow]Init cancelled.[/]")
        console.print("Run [white]cheri doctor[/] to check your configuration.")
        sys.exit(1)
    except CheriClientError as e:
        console.print(f"\n[red]Error:[/] {e}")
        console.print("\nRecovery: Run [white]cheri doctor[/] to diagnose the issue.")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/] {e}")
        console.print("\nRecovery: Run [white]cheri doctor[/] to diagnose the issue.")
        sys.exit(1)
