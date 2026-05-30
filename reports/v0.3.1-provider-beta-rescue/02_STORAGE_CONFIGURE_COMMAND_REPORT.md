# Storage Configure Command — Implementation Report

## Commands Implemented

### `cheri storage configure [--provider <kind>] [--include-experimental] [--workspace <id>]`

**Location:** `cheri_cloud_cli/storage.py` → `configure_storage_provider()`

**Flow:**
1. Load authenticated state
2. Resolve target workspace
3. Fetch current storage config
4. Determine target provider (interactive or explicit)
5. Check experimental gate
6. Prompt for required fields (secret fields use `hide_input=True`)
7. Build `ProviderConfig` payload
8. Validate via `POST /v1/providers/validate`
9. If validation errors: abort, leave existing config unchanged
10. Save via `POST /v1/storage/configure`
11. Render result with validation state

**Key behavior:**
- System provider configurable without credentials
- S3-compatible requires endpoint, bucket, region, access_key_id, secret_access_key
- Experimental providers require `--include-experimental` or `CHERI_EXPERIMENTAL_PROVIDERS=1`
- Validation failure does NOT overwrite existing config
- CLI never echoes secret field values

### `cheri storage migrate plan --to <provider> [--workspace <id>]`

Non-destructive. Shows source/target, migration considerations, warnings.
No files copied or modified.

### `cheri storage migrate dry-run --to <provider> [--workspace <id>]`

Non-destructive simulation. Shows step-by-step what would happen.
No config changed, no files copied.

---

## API Coverage

| Route | Worker | CLI | Notes |
|-------|--------|-----|-------|
| `GET /v1/providers` | ✅ | ✅ `cheri storage providers` | |
| `GET /v1/storage/config` | ✅ | ❌ | `cheri storage status` uses workspace list |
| `POST /v1/storage/configure` | ✅ | ✅ `cheri storage configure` | |
| `POST /v1/providers/validate` | ✅ | ✅ (used by configure) | |
| `POST /v1/storage/use` | ❌ | ✅ (alias to configure) | |

---

## Files Changed

- `cheri_cloud_cli/storage.py` — configure_storage_provider, storage_migrate_plan, storage_migrate_dry_run
- `cheri_cloud_cli/providers/catalog.py` — ProviderOption, iter_provider_options, find_provider_option
- `cheri_cloud_cli/cli.py` — registered `storage configure` and `storage migrate` commands
- `cheri_cloud_cli/contracts.py` — ProviderConfig, ProviderFieldSpec, ProviderValidationState, ProviderMetadata