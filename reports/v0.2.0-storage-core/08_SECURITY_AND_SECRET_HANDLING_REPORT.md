# 08 — Security and Secret Handling Report

## Secret Storage

Provider secrets stored in KV under `provider-secret:{workspace_id}:{provider_kind}`.
Not stored in workspace metadata, session tokens, or bootstrap secrets.

## Redaction

`redactProvider()` in `worker/services/provider_config.js` replaces secret field values with `"***"` before returning to API clients.

```javascript
// From worker/services/provider_config.js
for (const field of definition.fields) {
  if (field.secret && providerConfig.secret_fields?.includes(field.key)) {
    redactedSettings[field.key] = "***";
  }
}
```

## Provider Catalog API

`GET /v1/providers` never includes secret values:
- `credential_fields` shows which fields exist and their labels
- Field values are never included
- Experimental flag is included but not secret content

## Transfer Security

- Grant tokens hashed with SHA-256 before KV storage
- Grant TTL: 10 minutes
- Presigned URLs (S3-compatible) expire at grant expiry time
- No secrets in grant tokens (only workspace_id, file_id, provider_kind)

## What Was NOT Implemented in v0.2.0

- Encryption layer for provider secrets at rest in KV (future work)
- Secret rotation mechanism
- Per-file encryption

## Test Coverage

- Provider validate endpoint returns redacted config (no secret_access_key exposed)
- Storage provider catalog shows credential_fields but no secret values

## Cloudflare Worker Constraints

- Secrets stored in Cloudflare Workers environment bindings (typed as `R2Bucket`, `KVNamespace`)
- No Cloudflare Workers secret storage API used in v0.2.0 — secrets go to KV
- Future: consider Workers Secrets API for per-workspace provider credentials