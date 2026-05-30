# 05 — Storage CLI Commands Report

## New Commands

Added `cheri storage` command group with three subcommands:

```
cheri storage           — list providers (default)
cheri storage providers — list all providers
cheri storage status    — show active workspace provider status
cheri storage check     — verify backend and provider connectivity
```

## Implementation

**Module:** `cheri_cloud_cli/storage.py`

**Functions:**
- `list_storage_providers(client, include_experimental=False)` — renders provider table
- `show_storage_status(client, store, workspace_id=None)` — renders active workspace status panel
- `check_storage_connectivity(client)` — reports backend health and provider count

**CLI registration** in `cheri_cloud_cli/cli.py`:
```python
@cli.group("storage", ...)
def storage_group(ctx): ...

@storage_group.command("providers", ...)
def storage_providers_cmd(include_experimental): ...

@storage_group.command("status", ...)
@workspace_option
def storage_status_cmd(workspace): ...

@storage_group.command("check", ...)
def storage_check_cmd(): ...
```

## Output Examples

```
$ cheri storage providers
┌────────────────────────────────────────────────────────────────┐
│  Storage Providers                                             │
├────┬─────────────────────────┬────────────┬──────────┬────────┤
│ #  │ Provider               │ Status     │ Type     │ Notes  │
├────┼─────────────────────────┼────────────┼──────────┼────────┤
│ 1  │ System (recommended)   │ Ready      │ Temporary│ Reset: daily. Recommended for quick start. │
│ 2  │ S3-compatible          │ Coming soon│ Persistent│ Coming soon for active workspace use. │
└────┴─────────────────────────┴────────────┴──────────┴────────┘

$ cheri storage status
┌────────────────────────────────────────────────────────────────┐
│  Storage Status                                           [OK] │
│  Workspace   : docs (ws_abc123)                               │
│  Provider    : System (recommended)                           │
│  Kind        : system                                          │
│  State       : ready                                           │
│  Available   : Yes                                            │
│  Reset policy : daily                                          │
└────────────────────────────────────────────────────────────────┘
```

## Provider Gating

- Experimental providers shown only with `--include-experimental` flag
- System provider shown by default (ready, selectable)
- S3-compatible shown only with `CHERI_EXPERIMENTAL_PROVIDERS=1` in environment

## Tests

9 new Python tests in `tests/python/test_storage.py`:
- `test_lists_providers_without_experimental`
- `test_lists_providers_with_experimental`
- `test_warns_about_experimental_when_excluded`
- `test_handles_client_error_gracefully`
- `test_shows_status_for_active_workspace`
- `test_handles_no_active_workspace`
- `test_handles_not_logged_in`
- `test_reports_backend_health`
- `test_handles_backend_unreachable`

## Backward Compatibility

- Existing file/workspace/task commands unchanged
- No new required configuration
- `cheri storage` works for non-logged-in users (shows providers, check)