"""CLI command handlers for Cheri tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..client import CheriClient
from ..sessions import JsonCredentialStore
from ..services import TaskService, WatchService
from ..task.discovery import TaskTargetCandidate, describe_search_locations, search_task_targets
from ..task.runtime import display_path_label


def _render_tasks(console: Console, tasks) -> None:
    task_service = TaskService()
    table = Table(box=box.ROUNDED, border_style="cyan", title="Cheri Tasks")
    table.add_column("Task Id", style="cyan", width=18)
    table.add_column("Target", style="white", width=34)
    table.add_column("Workspace", width=18)
    table.add_column("Mode", width=24)
    table.add_column("Status", width=12)
    table.add_column("Last Run", style="dim", width=20)
    if not tasks:
        table.add_row("-", "-", "-", "-", "-", "-")
    else:
        for task in tasks:
            table.add_row(
                task.id,
                display_path_label(Path(task.target_path)),
                task.workspace_name,
                task.mode_label,
                task_service.effective_status(task),
                task.last_run_at[:19] if task.last_run_at else "-",
            )
    console.print(table)


def _resolve_target(task_file: Optional[str], task_directory: Optional[str]) -> tuple[str, str]:
    if bool(task_file) == bool(task_directory):
        raise click.ClickException("Specify exactly one of --file or --directory.")
    if task_file:
        return "file", task_file
    return "directory", task_directory or ""


def _resolve_mode(mode: Optional[str], on_change: bool, instant: bool) -> Optional[str]:
    selected = [item for item in [mode, "on-change" if on_change else None, "instant" if instant else None] if item]
    if len(selected) > 1:
        raise click.ClickException("Choose either --mode, --on-change, or --instant.")
    return selected[0] if selected else None


def _render_target_candidates(console: Console, title: str, candidates: Sequence[TaskTargetCandidate]) -> None:
    table = Table(box=box.ROUNDED, border_style="blue", title=title)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Location", style="white", width=18)
    table.add_column("Path", style="dim")
    for index, candidate in enumerate(candidates, start=1):
        table.add_row(str(index), candidate.source_label, str(candidate.path))
    console.print(table)


def _resolve_target_candidate(
    console: Console,
    raw_target: str,
    target_type: str,
    *,
    pick: bool,
) -> TaskTargetCandidate:
    search_result = search_task_targets(raw_target, target_type)
    if not search_result.candidates:
        searched = describe_search_locations(search_result.searched_locations)
        raise click.ClickException(
            f"Could not find the {target_type} target `{raw_target}`.\n\n"
            f"Searched:\n{searched}\n\n"
            "Try `cheri task find <name>` or pass a quoted full path."
        )

    if len(search_result.candidates) == 1 and not pick:
        return search_result.candidates[0]

    _render_target_candidates(console, "Task Target Matches", search_result.candidates)
    selected_index = click.prompt(
        "Select the task target",
        type=click.IntRange(1, len(search_result.candidates)),
        default=1,
    )
    return search_result.candidates[selected_index - 1]


def create_task(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    *,
    task_file: Optional[str],
    task_directory: Optional[str],
    workspace: Optional[str],
    mode: Optional[str],
    on_change: bool,
    instant: bool,
    every: str,
    debounce_seconds: int,
    recursive: bool,
    include_patterns: Sequence[str],
    exclude_patterns: Sequence[str],
    direction: str,
    conflict_strategy: str,
    watch_poll_seconds: float,
    no_start: bool,
    pick: bool,
) -> None:
    target_type, raw_target = _resolve_target(task_file, task_directory)
    requested_mode = _resolve_mode(mode, on_change, instant)
    resolved_target = _resolve_target_candidate(console, raw_target, target_type, pick=pick)
    task_service = TaskService()
    task = task_service.create_task(
        client,
        store,
        target_type=target_type,
        target_path=str(resolved_target.path),
        workspace=workspace,
        mode=requested_mode,
        every=every,
        debounce_seconds=debounce_seconds,
        recursive=recursive,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        direction=direction,
        conflict_strategy=conflict_strategy,
        watch_poll_seconds=watch_poll_seconds,
        enabled=not no_start,
    )
    if no_start:
        task.status = "stopped"
    else:
        task = WatchService(task_service=task_service).start_task(client, store, task.id)
    console.print(
        Panel.fit(
            f"Task id       : {task.id}\n"
            f"Workspace     : {task.workspace_name}\n"
            f"Target        : {display_path_label(Path(task.target_path))}\n"
            f"Resolved from : {resolved_target.source_label}\n"
            f"Mode          : {task.mode_label}\n"
            f"Direction     : {task.direction}\n"
            f"Recursive     : {'yes' if task.recursive else 'no'}\n"
            f"Status        : {task.status}\n"
            f"Watcher       : {'started automatically' if not no_start else 'not started'}",
            title="Task Created",
            border_style="green" if not no_start else "yellow",
        )
    )
    if not no_start:
        console.print(f"[green]Watching[/] {display_path_label(Path(task.target_path))} in the background.")
        console.print(f"Use [white]cheri task stop {task.id}[/] to stop it.")


def create_task_interactive(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
) -> None:
    """Interactive task creation with guided prompts."""
    console.print(Panel.fit(
        "[bold cyan]Create a Watch Task[/]\n\n"
        "Answer a few questions to set up automatic file syncing.",
        border_style="cyan",
    ))
    console.print()

    # Step 1: Choose file or directory
    console.print("[bold]Step 1: Choose what to watch[/]")
    target_type_choice = click.prompt(
        "Watch a file or directory?",
        type=click.Choice(["1", "2"], case_sensitive=False),
        default="2",
        show_choices=False,
    )
    target_type = "directory" if target_type_choice == "2" else "file"
    console.print()

    # Step 2: Choose target path
    console.print("[bold]Step 2: Choose target[/]")
    search_query = click.prompt(
        f"Enter {target_type} name or path",
        default=".",
    ).strip()
    console.print()

    # Resolve target
    console.print("[bold]Resolving target...[/]")
    resolved_target = _resolve_target_candidate(console, search_query, target_type, pick=True)
    console.print(f"[green]✓[/] Selected: {resolved_target.path} ({resolved_target.source_label})")
    console.print()

    # Step 3: Choose workspace
    console.print("[bold]Step 3: Choose workspace[/]")
    from ..sessions import load_authenticated_state
    state = load_authenticated_state(client, store)
    if not state.active_workspace:
        raise click.ClickException("No active workspace. Use 'cheri workspace create' or 'cheri workspace join' first.")

    workspace_choice = click.prompt(
        f"Workspace [{state.active_workspace.name}]",
        default="1",
    ).strip()

    selected_workspace = None
    if workspace_choice != "1" and workspace_choice:
        # User selected a different workspace
        for i, ws in enumerate(state.workspaces, start=2):
            if str(i) == workspace_choice:
                selected_workspace = ws.id
                break
    else:
        selected_workspace = state.active_workspace.id

    console.print(f"[green]✓[/] Workspace: {selected_workspace or state.active_workspace.name}")
    console.print()

    # Step 4: Choose mode
    console.print("[bold]Step 4: Choose sync mode[/]")
    console.print("  [1] on-change  - Upload when files are modified (recommended for directories)")
    console.print("  [2] interval   - Upload on a schedule (e.g., every 10 minutes)")
    console.print("  [3] instant    - Upload immediately when files change")
    console.print("  [4] hybrid     - Combination of interval and on-change")

    mode_choice = click.prompt(
        "Sync mode",
        type=click.Choice(["1", "2", "3", "4"], case_sensitive=False),
        default="1",
        show_choices=False,
    )
    mode_map = {"1": "on-change", "2": "interval", "3": "instant", "4": "hybrid"}
    selected_mode = mode_map.get(mode_choice, "on-change")
    console.print(f"[green]✓[/] Mode: {selected_mode}")
    console.print()

    # Step 5: Choose interval (if interval or hybrid)
    every = ""
    if selected_mode in ("interval", "hybrid"):
        every = click.prompt(
            "Upload interval (e.g., 10m, 30s, 1h)",
            default="10m",
        ).strip()
        console.print(f"[green]✓[/] Interval: {every}")
        console.print()

    # Step 6: Recursive option
    recursive = True
    if target_type == "directory":
        recursive = click.confirm(
            "Watch subdirectories recursively?",
            default=True,
        )
        console.print(f"[green]✓[/] Recursive: {'yes' if recursive else 'no'}")
        console.print()

    # Step 7: Include/exclude patterns
    console.print("[bold]Step 5: Include/exclude patterns[/]")
    console.print("[dim]Press Enter to skip any pattern[/]")

    include_patterns = []
    exclude_patterns = []

    include_input = click.prompt(
        "Include patterns (e.g., *.py, src/*)",
        default="",
    ).strip()
    if include_input:
        include_patterns = [p.strip() for p in include_input.split(",") if p.strip()]

    exclude_input = click.prompt(
        "Exclude patterns (e.g., *.log, .git/*)",
        default="",
    ).strip()
    if exclude_input:
        exclude_patterns = [p.strip() for p in exclude_input.split(",") if p.strip()]

    console.print(f"[green]✓[/] Include: {include_patterns or 'none'}")
    console.print(f"[green]✓[/] Exclude: {exclude_patterns or 'none'}")
    console.print()

    # Step 6: Secret-safe warning
    console.print(Panel.fit(
        "[yellow]Secret-Safe Exclusions[/]\n\n"
        "The following patterns are always excluded and will NOT be uploaded:\n"
        ".env, .env.*, *.env, credentials.json, *.key, *.pem, id_rsa, id_ed25519,\n"
        ".npmrc, .pypirc, .netrc, secrets.json, secret.json, and more.\n\n"
        "These files are never uploaded to protect sensitive data.",
        border_style="yellow",
    ))
    console.print()

    # Step 7: Preview
    console.print("[bold]Task Preview[/]")
    preview_table = Table(box=None, border_style=None, show_header=False)
    preview_table.add_column("Field", width=20, style="dim")
    preview_table.add_column("Value", width=50)
    preview_table.add_row("Target", str(resolved_target.path))
    preview_table.add_row("Type", target_type)
    preview_table.add_row("Workspace", selected_workspace or state.active_workspace.name)
    preview_table.add_row("Mode", selected_mode)
    if every:
        preview_table.add_row("Interval", every)
    preview_table.add_row("Recursive", "yes" if recursive else "no")
    if include_patterns:
        preview_table.add_row("Include", ", ".join(include_patterns))
    if exclude_patterns:
        preview_table.add_row("Exclude", ", ".join(exclude_patterns))
    console.print(preview_table)
    console.print()

    # Step 8: Confirm and create
    confirm = click.confirm("Create this task?", default=True)
    if not confirm:
        console.print("[yellow]Task creation cancelled.[/]")
        return

    # Create the task
    task_service = TaskService()
    task = task_service.create_task(
        client,
        store,
        target_type=target_type,
        target_path=str(resolved_target.path),
        workspace=selected_workspace,
        mode=selected_mode,
        every=every,
        debounce_seconds=3,
        recursive=recursive,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        direction="upload-only",
        conflict_strategy="manual-placeholder",
        watch_poll_seconds=2.0,
        enabled=False,  # Don't start automatically in interactive mode
    )

    console.print()
    console.print(
        Panel.fit(
            f"Task id       : {task.id}\n"
            f"Workspace     : {task.workspace_name}\n"
            f"Target        : {display_path_label(Path(task.target_path))}\n"
            f"Mode          : {task.mode_label}\n"
            f"Direction     : {task.direction}\n"
            f"Recursive     : {'yes' if task.recursive else 'no'}",
            title="Task Created",
            border_style="green",
        )
    )
    console.print()

    # Ask to start watcher
    start_watcher = click.confirm("Start the watcher now?", default=True)
    if start_watcher:
        task = WatchService(task_service=task_service).start_task(client, store, task.id)
        console.print(f"[green]✓[/] Watching {display_path_label(Path(task.target_path))} in the background.")
        console.print(f"Use [white]cheri task stop {task.id}[/] to stop it.")
    else:
        console.print("Use [white]cheri task start {task.id}[/] to start the watcher later.")


def list_tasks(console: Console) -> None:
    _render_tasks(console, TaskService().list_tasks())


def start_task(console: Console, client: CheriClient, store: JsonCredentialStore, task_id: str) -> None:
    task = WatchService().start_task(client, store, task_id)
    console.print(f"[green]Started[/] [white]{task.id}[/] and resumed background watching.")


def stop_task(console: Console, client: CheriClient, store: JsonCredentialStore, task_id: str) -> None:
    task = WatchService().stop_task(client, store, task_id)
    console.print(f"[yellow]Stopped[/] [white]{task.id}[/]. The task definition is kept locally.")


def pause_task(console: Console, task_id: str) -> None:
    stop_task(console, CheriClient(), JsonCredentialStore(), task_id)


def resume_task(console: Console, task_id: str) -> None:
    start_task(console, CheriClient(), JsonCredentialStore(), task_id)


def remove_task(console: Console, task_id: str) -> None:
    task_service = TaskService()
    task = task_service.get_task(task_id)
    if not click.confirm(f"Remove task {task.id} for {display_path_label(Path(task.target_path))}?", default=False):
        return
    WatchService(task_service=task_service).stop_task(CheriClient(), JsonCredentialStore(), task.id)
    task_service.remove_task(task_id, client=CheriClient(), store=JsonCredentialStore())
    console.print(f"[green]Removed[/] [white]{task.id}[/].")


def run_task(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    task_id: str,
    *,
    dry_run: bool,
) -> None:
    result = TaskService().execute_task(task_id, client, store, dry_run=dry_run)
    console.print(
        Panel.fit(
            f"Task id    : {result.task.id}\n"
            f"Workspace  : {result.task.workspace_name}\n"
            f"Target     : {display_path_label(Path(result.task.target_path))}\n"
            f"Summary    : {result.log_entry.summary}\n"
            f"Changed    : {len(result.changed_paths)}\n"
            f"Deleted    : {len(result.deleted_paths)}\n"
            f"Uploaded   : {result.uploaded_count}\n"
            f"Dry run    : {'yes' if dry_run else 'no'}",
            title="Task Run",
            border_style="green" if result.log_entry.status != "noop" else "yellow",
        )
    )
    if result.log_entry.status == "noop" and result.skipped_sensitive:
        console.print(
            f"[yellow]Note:[/] {len(result.skipped_sensitive)} file(s) skipped due to "
            "potentially sensitive names (e.g. .env, credentials.json).",
        )


def show_task_logs(console: Console, task_id: str) -> None:
    task_service = TaskService()
    task = task_service.get_task(task_id)
    logs = task_service.list_logs(task_id)
    table = Table(box=box.ROUNDED, border_style="magenta", title=f"Task Logs: {task.id}")
    table.add_column("Started", style="dim", width=20)
    table.add_column("Status", width=12)
    table.add_column("Summary", style="white")
    if not logs:
        table.add_row("-", "-", "No task runs recorded.")
    else:
        for entry in logs[:20]:
            summary = entry.summary if not entry.error else f"{entry.summary} ({entry.error})"
            table.add_row(entry.started_at[:19], entry.status, summary)
    console.print(table)


def find_task_targets(console: Console, query: str, *, target_type: str = "directory") -> None:
    search_result = search_task_targets(query, target_type)
    if not search_result.candidates:
        searched = describe_search_locations(search_result.searched_locations)
        raise click.ClickException(f"No matching {target_type} found for `{query}`.\n\nSearched:\n{searched}")
    _render_target_candidates(console, "Task Target Matches", search_result.candidates)


def watch_tasks(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    *,
    task_id: Optional[str],
    watch_all: bool,
    dry_run: bool,
    poll_seconds: Optional[float],
    background: bool = False,
) -> None:
    WatchService().watch(
        console,
        client,
        store,
        task_id=task_id,
        watch_all=watch_all,
        dry_run=dry_run,
        poll_seconds=poll_seconds,
        background=background,
    )


def dry_run_task(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    task_id: str,
) -> None:
    """Show files that would be uploaded without actually uploading."""
    result = TaskService().execute_task(task_id, client, store, dry_run=True)

    table = Table(box=box.ROUNDED, border_style="cyan", title="Dry Run Results")
    table.add_column("Action", width=16)
    table.add_column("Path", style="white")

    if result.skipped_sensitive:
        table.add_row("[yellow]SKIPPED (secret-safe)[/]", f"{len(result.skipped_sensitive)} file(s)")
        for path in result.skipped_sensitive[:10]:
            table.add_row("", f"  [dim]{path}[/]")
        if len(result.skipped_sensitive) > 10:
            table.add_row("", f"  [dim]... and {len(result.skipped_sensitive) - 10} more[/]")

    if result.deleted_paths:
        table.add_row("[dim]IGNORED (upload-only)[/]", f"{len(result.deleted_paths)} deleted path(s)")
        for path in result.deleted_paths[:5]:
            table.add_row("", f"  [dim]{path}[/]")
        if len(result.deleted_paths) > 5:
            table.add_row("", f"  [dim]... and {len(result.deleted_paths) - 5} more[/]")

    if result.changed_paths:
        table.add_row("[green]WOULD UPLOAD[/]", f"{len(result.changed_paths)} file(s)")
        for path in result.changed_paths[:20]:
            table.add_row("", f"  {path}")
        if len(result.changed_paths) > 20:
            table.add_row("", f"  [dim]... and {len(result.changed_paths) - 20} more[/]")
    else:
        table.add_row("[dim]NO CHANGES[/]", "No files to upload")

    console.print(table)
    console.print()
    console.print(f"[cyan]Task:[/] {result.task.id} | [cyan]Workspace:[/] {result.task.workspace_name}")
    console.print("[cyan]Note:[/] This was a dry run. No files were uploaded.")


def scan_task(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    task_id: str,
) -> None:
    """Show current snapshot/diff state without uploading."""
    from ..services import TaskService as TSS
    from ..task.runtime import scan_task as do_scan, display_path_label

    task_service = TSS()
    task = task_service.get_task(task_id)
    runtime = task_service.registry.get_runtime(task.id)

    scan = do_scan(task, runtime, force=False)

    table = Table(box=box.ROUNDED, border_style="cyan", title=f"Scan: {task.id}")
    table.add_column("Status", width=16)
    table.add_column("Path", style="white")

    if scan.skipped_sensitive:
        table.add_row("[yellow]SECRET-SAFE[/]", f"{len(scan.skipped_sensitive)} file(s) excluded")
        for path in scan.skipped_sensitive[:5]:
            table.add_row("", f"  [dim]{path}[/]")
        if len(scan.skipped_sensitive) > 5:
            table.add_row("", f"  [dim]... and {len(scan.skipped_sensitive) - 5} more[/]")

    if scan.deleted_paths:
        table.add_row("[dim]DELETED (local)[/]", f"{len(scan.deleted_paths)} path(s)")
        for path in scan.deleted_paths[:5]:
            table.add_row("", f"  [dim]{path}[/]")
        if len(scan.deleted_paths) > 5:
            table.add_row("", f"  [dim]... and {len(scan.deleted_paths) - 5} more[/]")

    if scan.changed_paths:
        table.add_row("[green]CHANGED[/]", f"{len(scan.changed_paths)} file(s)")
        for path in scan.changed_paths[:20]:
            table.add_row("", f"  {path}")
        if len(scan.changed_paths) > 20:
            table.add_row("", f"  [dim]... and {len(scan.changed_paths) - 20} more[/]")
    else:
        table.add_row("[dim]NO CHANGES[/]", "Files are in sync with last snapshot")

    console.print(table)
    console.print()
    console.print(f"[cyan]Task:[/] {task.id}")
    console.print(f"[cyan]Target:[/] {display_path_label(Path(task.target_path))}")
    console.print(f"[cyan]Workspace:[/] {task.workspace_name}")
    console.print(f"[cyan]Mode:[/] {task.mode_label}")
    console.print()
    console.print("[dim]Note: This scan does not upload files. Use 'cheri task run' to sync.[/]")
