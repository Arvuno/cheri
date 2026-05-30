# MinIO and B2 Compatibility Report

## MinIO — Status: BETA (same as S3-compatible)

MinIO uses the S3-compatible provider interface. Same implementation path as S3-compatible.

### To Enable MinIO:

```bash
cheri storage configure --provider s3-compatible --include-experimental
# Endpoint: http://localhost:9000 (or MinIO server address)
# Bucket: your-bucket
# Region: auto
# Access key: your-access-key
# Secret access key: your-secret-key
# Force path style: true (for MinIO)
```

### Docs

- `docs/storage/MINIO_SELF_HOSTED.md` — exists, accurate for config-only
- MinIO path-style mode is supported via `force_path_style` setting
- Actual file transfer NOT implemented (same as S3-compatible)

## Backblaze B2 — Status: DOCS_ONLY

B2 uses the `backblaze-b2` provider kind with fields:
- `bucket` (required)
- `key_id` (application key id, required)
- `application_key` (application key, required, secret)

### Implementation

B2 provider definition exists in `worker/providers/index.js` but:
- `BackblazeB2StorageProvider` class in `worker/providers/backblaze.js` is scaffolded
- `validateConfig()` returns `available: false` with warning about scaffolded state
- No actual B2 API integration

### Docs

- `docs/storage/B2_S3_COMPATIBLE.md` — exists, documents B2 S3-compatible API setup
- `docs/storage/PROVIDER_MATRIX.md` — exists, shows provider capabilities

## Honest Status

| Provider | Config | Transfer | Status |
|----------|--------|----------|--------|
| MinIO | ✅ Config works | ❌ Not implemented | BETA (config-only) |
| B2 | ❌ Not configurable | ❌ Not implemented | DOCS_ONLY |

## Migration Path

Both MinIO and B2 file transfer requires implementing the actual SDK calls in the
respective provider classes. The config layer is in place. File transfer is the gap.