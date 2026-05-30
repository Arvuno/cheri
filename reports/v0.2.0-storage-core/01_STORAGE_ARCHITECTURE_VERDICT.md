# 01 — Storage Architecture Verdict

## Architecture Summary

Five-layer storage architecture implemented:
1. **MetadataStore** — KV-backed (existing, no changes)
2. **BlobStorageProvider** — provider interface with 7 operations
3. **ProviderRegistry** — catalog and status computation
4. **ProviderConfigStore** — per-workspace config with secret handling
5. **StorageTransferService** — orchestrates upload/download via providers

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `worker/storage/` as new module directory | Separates abstraction from existing `worker/services/` and `worker/providers/` |
| Reuse existing `provider_config.js` for config store | Avoids duplicating workspace storage state management |
| `worker_proxy` as default transfer mode | Keeps System provider working without presigned URL complexity |
| Object key pattern `^[^/]+/[^/]+/v[0-9]+/[^/]+$` | Matches current `{workspaceId}/{fileId}/v{version}/{filename}` format |
| Provider errors extend `StorageError` | Allows structured error handling at the route layer |

## New Module Structure

```
worker/storage/
  errors.js        — StorageError, ProviderNotReadyError, etc.
  types.js         — ValidationResult, UploadTarget, etc.
  object_keys.js   — buildObjectKey, validateObjectKey
  registry.js      — getProviderStatus, getProviderCatalog, isProviderSelectable
  providers/
    base.js        — BaseStorageProvider (all methods throw not_ready by default)
    system_r2.js   — SystemStorageProvider (R2-backed, ready)
    local_dev.js   — LocalDevStorageProvider (test-only, experimental)
    s3_compatible.js — S3CompatibleStorageProvider (experimental)
  index.js         — Re-exports for convenient importing
```

## Backward Compatibility

- Existing `worker/providers/index.js` re-exports unchanged — no route changes
- File metadata shape unchanged except `provider_kind` now guaranteed
- `serializeFileRecord` unchanged — drops through normalizeStoredFileRecord
- Grant tokens unchanged — 10-minute TTL, same KV structure

## Exit Criteria Met

- ✅ System/R2 upload/download works (all 6 original worker tests pass)
- ✅ Provider abstraction in place (7 new Node tests + 9 new Python tests)
- ✅ Provider registry exists (GET /v1/providers with status/capabilities)
- ✅ Docs exist (7 new files in docs/storage/)
- ✅ Tests pass (61 Python, 7 Node storage, 6 Node worker)

## Known Limitations

- S3-compatible provider uses experimental AWS SDK imports — needs bundler verification
- `copyObject` on System provider is re-upload (not true server-side copy)
- Local dev provider not selectable via CLI (intentional — test-only)

## Next Step

Proceed to v0.3.0-provider-beta for user-selectable storage configuration.