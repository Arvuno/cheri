# Provider Secret Encryption Report

## Mechanism

**Algorithm:** AES-256-GCM via Web Crypto API
**Key derivation:** HKDF-SHA256 from `CHERI_PROVIDER_SECRET_KEY` env var
**Nonce:** 12 bytes, randomly generated per encryption
**Storage format:** `{ v: 1, nonce: "<base64>", ct: "<base64>", _encrypted: true }`

## Encryption Flow

```
saveProviderSecrets(env, workspaceId, providerKind, { secret_settings: {...} })
  → rawSecret = env.CHERI_PROVIDER_SECRET_KEY
  → for each secret field: encrypt(value, rawSecret) → JSON with v/nonce/ct
  → store { workspace_id, provider_kind, updated_at, secret_settings: {...}, _encrypted: true }
```

## Decryption Flow

```
loadProviderSecrets(env, workspaceId, providerKind)
  → if !record._encrypted && rawSecret: migrate plaintext → encrypt in place
  → if record._encrypted && rawSecret: decrypt each field
  → return { secret_settings: { decrypted values } }
```

## Migration Path

On read, if `record._encrypted` is falsy and `CHERI_PROVIDER_SECRET_KEY` is set,
all plaintext secret values are encrypted in place. This is a one-time migration.
KV never stores plaintext secrets after first read with the key set.

## Guarantees

1. **No raw secrets in KV** when `CHERI_PROVIDER_SECRET_KEY` is set
2. **API responses always redact** secret fields (`***` or `""`)
3. **Migration automatic** — plaintext records encrypted on next read
4. **Without key** — falls back to storing as-is (beta limitation, documented)

## Test Verification

`tests/node/storage.test.mjs` → "provider secret encryption key CHERI_PROVIDER_SECRET_KEY encrypts secrets in KV":
- Registers S3-compatible provider with secret `SUPERSECRETACCESSKEY123456`
- Verifies KV contains `_encrypted: true`
- Verifies `JSON.stringify(rawKVValue)` does NOT contain the plaintext secret