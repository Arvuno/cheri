"""Standardized CLI error messages for Cheri."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.panel import Panel


@dataclass(frozen=True)
class CheriError:
    """Standardized error with recovery suggestions."""

    what_failed: str
    likely_cause: str
    suggested_fix: str
    recovery_command: Optional[str] = None


BACKEND_UNREACHABLE = CheriError(
    what_failed="Backend API is not reachable",
    likely_cause=(
        "The Cheri backend server is down, your internet connection is broken, "
        "or the API URL is misconfigured."
    ),
    suggested_fix="Check your internet connection and verify the API URL.",
    recovery_command="cheri config check",
)


NOT_LOGGED_IN = CheriError(
    what_failed="Not logged in",
    likely_cause=(
        "No valid session found. You may have never registered or logged in, "
        "or your local credentials have expired."
    ),
    suggested_fix="Register a new account or log in with your bootstrap secret.",
    recovery_command="cheri register",
)


NO_ACTIVE_WORKSPACE = CheriError(
    what_failed="No active workspace",
    likely_cause=(
        "You are logged in but have not created or joined a workspace yet. "
        "A workspace is required for most Cheri operations."
    ),
    suggested_fix="Create a new workspace or join an existing one.",
    recovery_command="cheri workspace create --name myworkspace",
)


PROVIDER_INVALID = CheriError(
    what_failed="Storage provider configuration is invalid",
    likely_cause=(
        "The storage provider credentials are missing, malformed, or lack required permissions. "
        "This can happen after a provider configuration change."
    ),
    suggested_fix="Reconfigure your storage provider with valid credentials.",
    recovery_command="cheri storage configure --provider system",
)


UPLOAD_GRANT_FAILURE = CheriError(
    what_failed="Could not obtain upload authorization",
    likely_cause=(
        "The backend could not generate an upload grant. This may be due to "
        "workspace storage limits, permission issues, or backend problems."
    ),
    suggested_fix="Check your workspace storage status and try again.",
    recovery_command="cheri storage status",
)


DOWNLOAD_GRANT_FAILURE = CheriError(
    what_failed="Could not obtain download authorization",
    likely_cause=(
        "The backend could not generate a download grant. The file may not exist, "
        "be inaccessible, or storage may be misconfigured."
    ),
    suggested_fix="Verify the file exists and you have access to it.",
    recovery_command="cheri file list",
)


TASK_TARGET_MISSING = CheriError(
    what_failed="Task target file or directory not found",
    likely_cause=(
        "The file or directory specified for the task no longer exists or was moved. "
        "Tasks require an existing target to watch."
    ),
    suggested_fix="Update the task to point to an existing file or directory.",
    recovery_command="cheri task list",
)


KEYRING_UNAVAILABLE = CheriError(
    what_failed="Secure keyring storage is unavailable",
    likely_cause=(
        "The OS keychain is not accessible (headless environment, permissions issue, "
        "or keyring package not installed). Cheri will use encrypted file storage instead."
    ),
    suggested_fix="For better security, install a keyring backend for your OS.",
    recovery_command="pip install keyring[crypto]",
)


AUTH_SESSION_EXPIRED = CheriError(
    what_failed="Session has expired",
    likely_cause=(
        "Your login session has expired. This happens after a period of inactivity "
        "or if the backend has invalidated the session."
    ),
    suggested_fix="Log in again to refresh your session.",
    recovery_command="cheri login",
)


WORKSPACE_NOT_FOUND = CheriError(
    what_failed="Workspace not found",
    likely_cause=(
        "The workspace name or ID you provided does not exist or you do not have access to it."
    ),
    suggested_fix="Check the workspace name or ask your team for the correct workspace.",
    recovery_command="cheri workspace list",
)


def format_error(error: CheriError) -> str:
    """Format a CheriError as a human-readable string."""
    lines = [
        f"[red]Error:[/] {error.what_failed}",
        "",
        f"[yellow]Likely cause:[/] {error.likely_cause}",
        "",
        f"[cyan]Suggested fix:[/] {error.suggested_fix}",
    ]
    if error.recovery_command:
        lines.append("")
        lines.append(f"[green]Recovery:[/] Run [white]{error.recovery_command}[/] for next steps.")
    return "\n".join(lines)


def print_error(console: Console, error: CheriError) -> None:
    """Print a formatted CheriError to the console."""
    console.print(Panel.fit(
        format_error(error),
        title="Error",
        border_style="red",
    ))


def print_error_simple(console: Console, message: str, error: Optional[CheriError] = None) -> None:
    """Print a simple error message, optionally with a CheriError for context."""
    console.print(f"[red]Error:[/] {message}")
    if error:
        console.print(f"[cyan]Hint:[/] {error.suggested_fix}")
        if error.recovery_command:
            console.print(f"[green]Try:[/] [white]{error.recovery_command}[/]")
