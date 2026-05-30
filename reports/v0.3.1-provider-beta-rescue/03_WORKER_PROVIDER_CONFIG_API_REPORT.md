# Worker Provider Config API — Implementation Report

## Routes Implemented

### `GET /v1/storage/config`
- Requires: authenticated session + workspace access
- Returns: `{ workspace_id, workspace_name, provider }` with secrets redacted
- Redaction: secret fields set to `***` or empty string via `redactProvider()`

### `POST /v1/storage/configure`
- Requires: authenticated session + workspace access + admin role
- Behavior: validate FIRST, save SECOND
- If validation fails: existing config unchanged, returns errors
- If validation succeeds: saves new storage state, returns `{ ok, workspace_id, provider }`
- Uses `createWorkspaceStorageState()` → `prepareProviderForWorkspace()` → `saveProviderSecrets()`

### `POST /v1/providers/validate`
- Public route (no auth required for catalog)
- Input: `{ provider, allow_experimental }`
- Validates provider config by instantiating provider and calling `validateConfig()`
- Returns redacted provider config with `validation` state
- S3-compatible returns `state: "validated-config", available: false, warnings: [...]`

---

## Provider Config Flow

```
CLI build ProviderConfig
  → client.validate_provider_config() → POST /v1/providers/validate
  → POST /v1/storage/configure → createWorkspaceStorageState()
  → prepareProviderForWorkspace() → saves encrypted secrets to KV
```

---

## Secret Encryption (worker/lib/storage.js)

`saveProviderSecrets()` — AES-GCM encrypts secrets before KV storage:
- Key: `provider-secret:{workspaceId}:{providerKind}`
- Format: `{ v: 1, nonce: "<base64>", ct: "<base64>", _encrypted: true }`
- Uses `CHERI_PROVIDER_SECRET_KEY` via HKDF to derive AES-256 key

`loadProviderSecrets()` — decrypts on read, migrates plaintext records:
- If record has no `_encrypted` flag and raw secret key is set: encrypt in place
- If record is encrypted: decrypt and return plaintext settings
- Returns `{ secret_settings: { ... } }` with decrypted values

---

## Files

- `worker/index.js` — routes for `/v1/storage/config`, `/v1/storage/configure`, `/v1/providers/validate`
- `worker/providers/index.js` — `validateProviderSelection()`, `prepareProviderForWorkspace()`, `createWorkspaceStorageState()`, `redactProvider()`
- `worker/lib/storage.js` — `saveProviderSecrets()`, `loadProviderSecrets()`, `deleteProviderSecrets()`