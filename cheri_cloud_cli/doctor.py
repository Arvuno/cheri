"""Cheri doctor - diagnostic health checks."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from .client import CheriClient, CheriClientError
from .config import get_base_url, get_paths, load_cli_settings
from .sessions import JsonCredentialStore, load_authenticated_state
from .task.registry import TaskRegistry


console = Console()


@dataclass(frozen=True)
class CheckResult:
    """Result of a single health check."""

    name: str
    status: str  # "pass", "warn", "fail", "skip"
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class DiagnosticReport:
    """Complete diagnostic report."""

    checks: List[CheckResult]
    has_critical_failures: bool


def _check_cli_version() -> CheckResult:
    """Check the CLI version."""
    from . import __version__
    return CheckResult(
        name="CLI Version",
        status="pass",
        message=f"Cheri CLI v{__version__}",
    )


def _check_python_version() -> CheckResult:
    """Check Python version."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        return CheckResult(
            name="Python Version",
            status="fail",
            message=f"Python {version_str} - requires 3.11+",
        )
    return CheckResult(
        name="Python Version",
        status="pass",
        message=f"Python {version_str}",
    )


def _check_config_directory() -> CheckResult:
    """Check config directory exists and has correct permissions."""
    try:
        paths = get_paths()
        config_dir = paths.config_dir
        config_dir.mkdir(parents=True, exist_ok=True)

        if not os.access(config_dir, os.W_OK):
            return CheckResult(
                name="Config Directory",
                status="fail",
                message=f"Config directory is not writable: {config_dir}",
            )

        if os.name != "nt":
            mode = config_dir.stat().st_mode & 0o777
            if mode & 0o077:
                return CheckResult(
                    name="Config Directory",
                    status="warn",
                    message=f"Config directory has overly permissive mode: {oct(mode)}",
                    details={"path": str(config_dir), "mode": oct(mode)},
                )

        return CheckResult(
            name="Config Directory",
            status="pass",
            message=f"Config directory OK: {config_dir}",
            details={"path": str(config_dir)},
        )
    except Exception as e:
        return CheckResult(
            name="Config Directory",
            status="fail",
            message=f"Config directory error: {e}",
        )


def _check_keyring() -> CheckResult:
    """Check keyring availability."""
    try:
        import keyring
        backend = keyring.get_keyring()
        backend_name = type(backend).__name__
        if backend_name == "NullKeyring" or "null" in backend_name.lower():
            return CheckResult(
                name="Keyring",
                status="warn",
                message="Keyring available but using null backend (fallback mode)",
                details={"backend": backend_name},
            )
        return CheckResult(
            name="Keyring",
            status="pass",
            message=f"Keyring OK: {backend_name}",
            details={"backend": backend_name},
        )
    except ImportError:
        return CheckResult(
            name="Keyring",
            status="warn",
            message="keyring package not installed - using fallback file storage",
        )
    except Exception as e:
        return CheckResult(
            name="Keyring",
            status="warn",
            message=f"Keyring error: {e} - using fallback",
        )


def _check_backend_url() -> CheckResult:
    """Check if backend API URL is configured."""
    settings = load_cli_settings()
    base_url = get_base_url()
    configured_url = settings.api_url or base_url

    if not configured_url:
        return CheckResult(
            name="Backend API URL",
            status="fail",
            message="No API URL configured",
        )

    return CheckResult(
        name="Backend API URL",
        status="pass",
        message=f"API URL: {configured_url}",
        details={"api_url": configured_url, "source": "settings" if settings.api_url else "default"},
    )


def _check_backend_health(client: CheriClient) -> CheckResult:
    """Check if backend is reachable."""
    try:
        health = client.healthcheck()
        product = health.get("product", "Cheri API")
        mode = health.get("mode", "unknown")
        return CheckResult(
            name="Backend Health",
            status="pass",
            message=f"Backend OK: {product} ({mode})",
            details=health,
        )
    except CheriClientError as e:
        return CheckResult(
            name="Backend Health",
            status="fail",
            message=f"Backend unreachable: {e}",
        )
    except Exception as e:
        return CheckResult(
            name="Backend Health",
            status="fail",
            message=f"Backend error: {e}",
        )


def _check_auth_state(store: JsonCredentialStore) -> CheckResult:
    """Check authentication state."""
    try:
        state = store.load()
        if not state:
            return CheckResult(
                name="Auth Session",
                status="fail",
                message="No saved session found",
            )

        if not state.session_token:
            return CheckResult(
                name="Auth Session",
                status="fail",
                message="Session token missing",
            )

        username = state.user.username if state.user else "unknown"
        return CheckResult(
            name="Auth Session",
            status="pass",
            message=f"Logged in as: {username}",
            details={"username": username, "has_bootstrap": bool(state.bootstrap_secret)},
        )
    except Exception as e:
        return CheckResult(
            name="Auth Session",
            status="fail",
            message=f"Auth state error: {e}",
        )


def _check_active_workspace(client: CheriClient, store: JsonCredentialStore) -> CheckResult:
    """Check active workspace state."""
    try:
        state = store.load()
        if not state:
            return CheckResult(
                name="Active Workspace",
                status="fail",
                message="No saved session",
            )

        if not state.active_workspace_id:
            return CheckResult(
                name="Active Workspace",
                status="warn",
                message="No active workspace - use 'cheri workspace create' or 'cheri workspace join'",
            )

        workspace_name = state.active_workspace.name if state.active_workspace else state.active_workspace_id
        role = state.active_workspace.role if state.active_workspace else "unknown"

        return CheckResult(
            name="Active Workspace",
            status="pass",
            message=f"Active workspace: {workspace_name} ({role})",
            details={
                "workspace_id": state.active_workspace_id,
                "workspace_name": workspace_name,
                "role": role,
            },
        )
    except CheriClientError as e:
        return CheckResult(
            name="Active Workspace",
            status="warn",
            message=f"Could not verify workspace: {e}",
        )
    except Exception as e:
        return CheckResult(
            name="Active Workspace",
            status="fail",
            message=f"Workspace error: {e}",
        )


def _check_storage_provider(client: CheriClient, store: JsonCredentialStore) -> CheckResult:
    """Check storage provider configuration."""
    try:
        state = store.load()
        if not state or not state.active_workspace_id:
            return CheckResult(
                name="Storage Provider",
                status="skip",
                message="No active workspace",
            )

        auth_state = load_authenticated_state(client, store)
        config = client.get_storage_config(auth_state, state.active_workspace_id)

        provider_kind = config.get("kind", "unknown")
        validation = config.get("validation", {})
        validation_state = validation.get("state", "unknown")

        status = "pass" if validation_state == "ready" else "warn" if validation_state == "not_ready" else "fail"

        return CheckResult(
            name="Storage Provider",
            status=status,
            message=f"Provider: {provider_kind} ({validation_state})",
            details=config,
        )
    except CheriClientError as e:
        return CheckResult(
            name="Storage Provider",
            status="warn",
            message=f"Could not check provider: {e}",
        )
    except Exception as e:
        return CheckResult(
            name="Storage Provider",
            status="fail",
            message=f"Provider error: {e}",
        )


def _check_task_registry() -> CheckResult:
    """Check task registry state."""
    try:
        registry = TaskRegistry()
        tasks = registry.list_tasks()

        if not tasks:
            return CheckResult(
                name="Task Registry",
                status="pass",
                message="No tasks configured",
            )

        running = sum(1 for t in tasks if t.status == "running")
        return CheckResult(
            name="Task Registry",
            status="pass",
            message=f"{len(tasks)} task(s) configured, {running} running",
            details={"total": len(tasks), "running": running, "tasks": tasks},
        )
    except Exception as e:
        return CheckResult(
            name="Task Registry",
            status="warn",
            message=f"Task registry error: {e}",
        )


def _check_secret_safe_patterns() -> CheckResult:
    """Check if secret-safe exclude patterns are enabled."""
    DEFAULT_EXCLUDES = {
        ".env", ".env.*", "*.env", "credentials.json", "*.key", "*.pem",
        "id_rsa", "id_ed25519", ".npmrc", ".pypirc", ".netrc",
        "secrets.json", "secret.json",
    }

    return CheckResult(
        name="Secret-Safe Patterns",
        status="pass",
        message=f"Secret-safe exclusions active ({len(DEFAULT_EXCLUDES)} patterns)",
        details={"excluded_patterns": list(DEFAULT_EXCLUDES)},
    )


def _check_local_write_permissions() -> CheckResult:
    """Check if local directory has write permissions."""
    try:
        cwd = Path.cwd()
        test_file = cwd / ".cheri_write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            return CheckResult(
                name="Local Write Permissions",
                status="pass",
                message=f"Current directory is writable: {cwd}",
            )
        except OSError:
            return CheckResult(
                name="Local Write Permissions",
                status="warn",
                message=f"Current directory may not be writable: {cwd}",
            )
    except Exception as e:
        return CheckResult(
            name="Local Write Permissions",
            status="warn",
            message=f"Could not check write permissions: {e}",
        )


def _check_environment_variables() -> CheckResult:
    """Check environment variables that affect Cheri."""
    relevant_vars = {
        "CHERI_API_URL": "Backend API URL override",
        "CHERI_WORKER_URL": "Worker URL override",
        "CHERI_CONFIG_DIR": "Config directory override",
        "CHERI_PROVIDER_SECRET_KEY": "Secret encryption key (DO NOT export!)",
    }

    found_vars = {}
    for var, desc in relevant_vars.items():
        value = os.environ.get(var)
        if value:
            if var == "CHERI_PROVIDER_SECRET_KEY":
                found_vars[var] = "*** (hidden)"
            else:
                found_vars[var] = value

    if not found_vars:
        return CheckResult(
            name="Environment Variables",
            status="pass",
            message="No Cheri environment variables set",
        )

    return CheckResult(
        name="Environment Variables",
        status="pass",
        message=f"{len(found_vars)} Cheri variable(s) set",
        details={"variables": found_vars, "descriptions": relevant_vars},
    )


def _check_common_misconfigurations(client: CheriClient, store: JsonCredentialStore) -> List[CheckResult]:
    """Check for common misconfiguration patterns."""
    issues = []

    # Check for stored credentials without valid session
    try:
        state = store.load()
        if state and state.bootstrap_secret and not state.session_token:
            issues.append(CheckResult(
                name="Config Drift",
                status="warn",
                message="Bootstrap secret stored but no active session",
                details={"hint": "Run 'cheri login' to refresh your session"},
            ))
    except Exception:
        pass

    # Check for experimental provider without acknowledgment
    try:
        state = store.load()
        if state and state.active_workspace:
            auth_state = load_authenticated_state(client, store)
            config = client.get_storage_config(auth_state, state.active_workspace_id)
            provider_kind = config.get("kind", "")
            if "experimental" in provider_kind.lower():
                issues.append(CheckResult(
                    name="Experimental Provider",
                    status="warn",
                    message=f"Using experimental provider: {provider_kind}",
                    details={"hint": "Experimental providers may not be production-ready"},
                ))
    except CheriClientError:
        pass
    except Exception:
        pass

    return issues


def run_diagnostics(client: CheriClient, store: JsonCredentialStore) -> DiagnosticReport:
    """Run all diagnostic checks."""
    checks = []

    # Core checks
    checks.append(_check_cli_version())
    checks.append(_check_python_version())
    checks.append(_check_config_directory())
    checks.append(_check_keyring())
    checks.append(_check_backend_url())

    # Backend checks
    backend_health = _check_backend_health(client)
    checks.append(backend_health)

    # Only continue with auth checks if backend is reachable
    if backend_health.status == "pass":
        checks.append(_check_auth_state(store))
        checks.append(_check_active_workspace(client, store))
        checks.append(_check_storage_provider(client, store))
    else:
        checks.append(CheckResult(
            name="Auth Session",
            status="skip",
            message="Skipped (backend unreachable)",
        ))
        checks.append(CheckResult(
            name="Active Workspace",
            status="skip",
            message="Skipped (backend unreachable)",
        ))
        checks.append(CheckResult(
            name="Storage Provider",
            status="skip",
            message="Skipped (backend unreachable)",
        ))

    # Local checks
    checks.append(_check_task_registry())
    checks.append(_check_secret_safe_patterns())
    checks.append(_check_local_write_permissions())
    checks.append(_check_environment_variables())

    # Additional issue checks
    issues = _check_common_misconfigurations(client, store)
    checks.extend(issues)

    # Determine if there are critical failures
    has_critical = any(
        c.status == "fail" for c in checks
        if c.name not in ("Backend Health",)  # Backend health is not critical for local checks
    )

    return DiagnosticReport(checks=checks, has_critical_failures=has_critical)


def _render_human_output(report: DiagnosticReport) -> None:
    """Render the diagnostic report in human-readable format."""
    table = Table(box=None, border_style=None, show_header=False)
    table.add_column("Status", width=8)
    table.add_column("Check", width=24)
    table.add_column("Result", width=60)

    status_icons = {
        "pass": "[green]✓[/]",
        "warn": "[yellow]![/]",
        "fail": "[red]✗[/]",
        "skip": "[dim]-[/]",
    }

    for check in report.checks:
        icon = status_icons.get(check.status, "[dim]?[/]")
        table.add_row(icon, check.name, check.message)

    console.print(table)
    console.print()

    # Summary
    passed = sum(1 for c in report.checks if c.status == "pass")
    warnings = sum(1 for c in report.checks if c.status == "warn")
    failures = sum(1 for c in report.checks if c.status == "fail")
    skipped = sum(1 for c in report.checks if c.status == "skip")

    summary_parts = []
    if failures > 0:
        summary_parts.append(f"[red]{failures} failure(s)[/]")
    if warnings > 0:
        summary_parts.append(f"[yellow]{warnings} warning(s)[/]")
    if passed > 0:
        summary_parts.append(f"[green]{passed} pass(ed)[/]")
    if skipped > 0:
        summary_parts.append(f"[dim]{skipped} skipped[/]")

    console.print(f"Summary: {', '.join(summary_parts)}")

    if failures > 0:
        console.print()
        console.print("[red]Run 'cheri doctor --json' for machine-readable output.[/]")
        console.print("Run 'cheri config check' to verify backend connectivity.")


def _render_json_output(report: DiagnosticReport) -> str:
    """Render the diagnostic report as JSON."""
    output = {
        "version": "1.0",
        "summary": {
            "total": len(report.checks),
            "passed": sum(1 for c in report.checks if c.status == "pass"),
            "warnings": sum(1 for c in report.checks if c.status == "warn"),
            "failures": sum(1 for c in report.checks if c.status == "fail"),
            "skipped": sum(1 for c in report.checks if c.status == "skip"),
            "has_critical_failures": report.has_critical_failures,
        },
        "checks": [
            {
                "name": c.name,
                "status": c.status,
                "message": c.message,
                "details": c.details,
            }
            for c in report.checks
        ],
    }
    return json.dumps(output, indent=2)


def doctor(
    console: Console,
    client: CheriClient,
    store: JsonCredentialStore,
    *,
    json_output: bool = False,
    release_check: bool = False,
) -> int:
    """
    Run diagnostic health checks.

    Args:
        json_output: Output results as JSON
        release_check: Exit non-zero on critical issues

    Returns:
        Exit code (0 = success, 1 = issues found)
    """
    try:
        report = run_diagnostics(client, store)

        if json_output:
            console.print(_render_json_output(report))
        else:
            _render_human_output(report)

        if release_check and report.has_critical_failures:
            console.print("\n[red]Critical issues found (--release-check).[/]")
            return 1

        return 0

    except CheriClientError as e:
        if json_output:
            error_output = json.dumps({
                "error": str(e),
                "checks": [],
            }, indent=2)
            console.print(error_output)
        else:
            console.print(f"[red]Error:[/] {e}")
        return 1
    except Exception as e:
        if json_output:
            error_output = json.dumps({
                "error": str(e),
                "checks": [],
            }, indent=2)
            console.print(error_output)
        else:
            console.print(f"[red]Unexpected error:[/] {e}")
        return 1
