# Storage E2E Audit — v0.9

**Date:** 2026-05-30
**Branch:** v0.9-s3-e2e-and-type-cleanup

---

## S3-Compatible Provider Status

### What Works

| Feature | Status |
|---------|--------|
| Provider config (endpoint, bucket, region, keys) | Working — validated, redacted in API responses |
| Secret encryption (CHERI_PROVIDER_SECRET_KEY) | Working — secrets encrypted in KV |
| `putObject` (worker→S3 via SDK) | Working — raw S3 PutObjectCommand |
| `getObject` (S3→worker via SDK) | Working — raw S3 GetObjectCommand |
| `deleteObject` / `headObject` / `listObjects` | Working |
| Presigned URL generation (`createUploadTarget`/`createDownloadTarget`) | Implemented — returns `mode: "direct"` + presigned URL |
| CLI upload (`requests.put` to grant URL) | Working — proxy through worker |
| CLI download (`requests.get` from grant URL) | Working — proxy through worker |
| MinIO path-style (`force_path_style: true`) | Config exists and passed to SDK client |
| Provider hidden behind `CHERI_EXPERIMENTAL_PROVIDERS=1` | Correct |

### What Does NOT Work

| Feature | Status |
|---------|--------|
| **Direct-to-S3 upload** (CLI→S3 presigned URL) | Not implemented — presigned URL generated but never exposed to CLI; all uploads go through worker proxy |
| **Direct-to-S3 download** (CLI→S3 presigned URL) | Not implemented — same as upload |
| **Multipart upload** | Declared in capabilities but not implemented (single-shot PutObject only) |
| **generateUploadTarget signature** | `file_service.js` calls with `{ providerObjectKey, providerObjectId }` but S3 provider's `createUploadTarget` expects `{ workspace, file, expires_at }` — interfaces misaligned |
| **Backblaze B2 implementation** | Schema defined in `provider_config.js` but no `backblaze.js` class exists in `worker/storage/providers/` |
| **S3-compatible e2e test** | No test coverage — only `system` provider is tested end-to-end |

---

## Upload Flow (Proxy Mode — Current)

```
CLI ──► Worker ──► S3
         │
  POST /v1/files/upload-grant
         │
  PUT /v1/transfers/upload/${token}
  (body: file bytes)
         │
  provider.putObject()
  (S3 PutObjectCommand)
```

The presigned URL from `createUploadTarget` is generated and stored in the grant's `target` field but **never exposed to the CLI**. The CLI always uses the worker proxy endpoint.

---

## MinIO Path-Style Requirements

- MinIO requires path-style: `http://localhost:9000/bucket/key`
- `force_path_style: true` in SDK config handles this
- The `scripts/dev/minio-smoke.sh` confirms path-style PUT/GET works with Basic auth
- Backblaze B2 uses virtual-hosted style and requires `force_path_style: false`

---

## Backblaze B2 vs MinIO

| Aspect | MinIO | Backblaze B2 |
|--------|-------|--------------|
| URL style | Path-style only | Virtual-hosted |
| `force_path_style` | Must be `true` | Must be `false` |
| Auth | AWS Signature v4 | B2-specific |
| AWS SDK v3 | Fully compatible | Compatible |
| Presigned URLs | Supported | Supported |
| Implementation | `s3_compatible.js` works | No implementation class |

---

## Actions Needed

1. **Write `minio-e2e.sh`** — full CLI→Worker→MinIO upload/download test
2. **Add storage provider e2e tests** — test S3-compatible `putObject`/`getObject` directly against MinIO
3. **Fix Backblaze B2** — create `worker/storage/providers/backblaze_b2.js` or document it remains docs-only
4. **Optionally expose direct-to-S3 mode** — if desired, extract presigned URL from grant and return directly to CLI (separate enhancement, not v0.9 scope)

---

## Verdict

S3-compatible provider **upload/download via worker proxy works**. The missing piece is **integration test coverage** against a real MinIO instance. Presigned direct-to-S3 is a future enhancement.

**MinIO e2e: IMPLEMENT** — create `scripts/dev/minio-e2e.sh`
**B2: KEEP DOCS_ONLY** — no implementation class, mark as experimental/docs-only