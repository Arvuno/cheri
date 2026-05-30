# Storage Migration Dry-Run Report

## Non-Destructive Implementation

Both `cheri storage migrate plan` and `cheri storage migrate dry-run` are
non-destructive. They read current config and display information only.

## `cheri storage migrate plan --to <provider>`

**Output:**
- Active workspace and current provider
- Target provider
- Migration considerations table:
  - Files: "File records will NOT be copied or migrated automatically"
  - Provider switch: "New uploads will go to {target}"
  - Original files: "Files in the original provider remain until manually migrated"
  - Rollback: "You can re-configure back to the original provider at any time"
  - Credentials: "Target provider credentials will be validated before switching"
- Explicit warnings: "No files were copied or modified"

## `cheri storage migrate dry-run --to <provider>`

**Output:**
- Workspace, source, target info
- "No files were copied or modified." / "No provider configuration was changed."
- Step-by-step table:
  1. Validate target provider config (risk: None — read-only check)
  2. Save new provider to workspace storage (risk: Config write, reversible)
  3. Existing files stay in source provider (risk: None)
  4. New uploads go to target provider (risk: None)
- "To execute this migration: cheri storage configure --provider {target}"

## Implementation

`cheri_cloud_cli/storage.py` → `storage_migrate_plan()` and `storage_migrate_dry_run()`

Both read current config via `client.get_storage_config()`, compare with target,
and render a `rich.Panel` + `rich.Table` output. No mutations.

## Files Affected

- `cheri_cloud_cli/storage.py` — both functions implemented
- `cheri_cloud_cli/cli.py` — `storage migrate plan` and `storage migrate dry-run` registered