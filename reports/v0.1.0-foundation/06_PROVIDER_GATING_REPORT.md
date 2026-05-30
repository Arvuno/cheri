# Provider Gating Report

## What Changed

Confirmed and documented provider gating behavior in both CLI and Worker. Non-System providers are clearly marked as coming soon and cannot be selected in the default public flow.

## Provider Status (v0.1.0)

| Provider | Selectable | Coming Soon | Experimental | Status |
|----------|------------|-------------|--------------|--------|
| System (recommended) | Yes | No | No | Working |
| S3-compatible | No | Yes | Yes | Scaffolded |
| Google Drive | No | Yes | Yes | Scaffolded |
| Backblaze B2 | No | Yes | Yes | Scaffolded |

## CLI Gating (`cheri_cloud_cli/providers/catalog.py`)

**Default flow** (`prompt_for_provider()`):
- Only shows selectable providers OR experimental providers with `CHERI_EXPERIMENTAL_PROVIDERS=1`
- If user tries to select a non-selectable provider, raises `ClickException`: "X is coming soon and cannot be selected in the public setup flow yet."
- If provider validation fails or is unavailable, shows warning panel and asks confirmation

**Experimental flag**:
- `CHERI_EXPERIMENTAL_PROVIDERS=1` env var enables experimental provider selection
- When enabled, providers with `experimental: True` become selectable
- Strong warning must still be acknowledged before proceeding

## Worker Gating (`worker/providers/index.js`)

**Provider catalog** (`/v1/providers`):
- System: `selectable: true`, `coming_soon: false`
- S3-compatible: `selectable: false`, `coming_soon: true`, `experimental: true`
- Google Drive: `selectable: false`, `coming_soon: true`, `experimental: true`
- Backblaze B2: `selectable: false`, `coming_soon: true`, `experimental: true`

**Selection validation** (`validateProviderSelection()`):
- Rejects non-System provider selections unless `allow_experimental` is True
- Non-System providers return `{ state: "not_ready", available: false }` in validation

## Files Changed

- `docs/provider-matrix.md` — confirmed accurate, no changes needed
- Worker provider catalog — already correct, verified by worker tests

## User Experience

When a user runs `cheri register`:
1. Provider table shows only System as selectable
2. System is pre-selected with a warning about daily reset
3. User must acknowledge the warning to continue
4. Other providers show "Coming soon" status and cannot be selected

With `CHERI_EXPERIMENTAL_PROVIDERS=1`:
1. All providers are shown in the table
2. Experimental providers can be selected
3. A strong warning is displayed before proceeding

## Next for v0.2.0

- S3-compatible provider: full boto3 integration with bucket/endpoint/credentials
- Provider-specific credential input prompts (already scaffolded in ProviderFieldSpec)
- Backend validation endpoint for each provider type
- Encrypted credential storage per workspace