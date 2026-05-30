# S3-Compatible Provider — Plan

> Date: 2026-05-30
> Status: **experimental** — partial implementation in v0.2.0, beta-ready in v0.3.0

## Overview

The S3-compatible provider allows Cheri to use any S3-style object storage backend (AWS S3, MinIO, Backblaze B2, etc.) instead of Cloudflare R2. This breaks the hard dependency on Cloudflare for blob storage.

## Current Status (v0.2.0)

**Implemented:**
- `worker/storage/providers/s3_compatible.js` — scaffolded provider class
- `validateConfig()` — checks endpoint, bucket, region, credentials
- `putObject()` — uploads via AWS SDK S3 client
- `getObject()` — downloads via AWS SDK S3 client
- `deleteObject()` — deletes via AWS SDK S3 client
- `headObject()` — metadata via AWS SDK S3 client
- `listObjects()` — listing via AWS SDK S3 client
- `createUploadTarget()` — returns presigned PUT URL (direct mode)
- `createDownloadTarget()` — returns presigned GET URL (direct mode)

**Not yet implemented:**
- Full multipart upload support
- Checksum verification after upload
- Server-side copy (copyObject)

## Provider Definition

```javascript
{
  kind: "s3-compatible",
  label: "S3-compatible",
  status: "experimental",
  selectable: false,  // Requires CHERI_EXPERIMENTAL_PROVIDERS=1
  comingSoon: false,
  experimental: true,
  fields: [
    { key: "endpoint", label: "Endpoint URL", required: true, secret: false },
    { key: "bucket", label: "Bucket name", required: true, secret: false },
    { key: "region", label: "Region", required: true, secret: false, default: "auto" },
    { key: "access_key_id", label: "Access key id", required: true, secret: false },
    { key: "secret_access_key", label: "Secret access key", required: true, secret: true },
    { key: "force_path_style", label: "Force path-style URLs", required: false, secret: false },
  ],
}
```

## Required Configuration

| Field | Description | Example |
|---|---|---|
| `endpoint` | S3 endpoint URL | `https://s3.amazonaws.com` or `http://localhost:9000` |
| `bucket` | Bucket name | `my-cheri-workspace` |
| `region` | AWS region | `us-east-1` or `auto` |
| `access_key_id` | AWS access key | `AKIAIOSFODNN7EXAMPLE` |
| `secret_access_key` | AWS secret | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `force_path_style` | Use path-style URLs (MinIO) | `true` for MinIO, `false` for AWS S3 |

## MinIO Support

To use MinIO for local development or self-hosted teams:

```javascript
{
  kind: "s3-compatible",
  settings: {
    endpoint: "http://localhost:9000",
    bucket: "cheri-workspace",
    region: "us-east-1",
    access_key_id: "minioadmin",
    secret_access_key: "minioadmin",
    force_path_style: true,  // Required for MinIO
  }
}
```

See `docs/storage/MINIO_SELF_HOSTED.md` for full local setup instructions.

## Backblaze B2 Support

Backblaze B2 supports S3-compatible API. Configure it like any S3 endpoint:

```javascript
{
  kind: "s3-compatible",
  settings: {
    endpoint: "https://s3.us-west-002.backblazeb2.com",
    bucket: "my-cheri-bucket",
    region: "us-west-002",
    access_key_id: "<B2 application key ID>",
    secret_access_key: "<B2 application key>",
  }
}
```

See `docs/storage/B2_S3_COMPATIBLE.md` for full instructions.

## Transfer Modes

| Mode | Description | Use case |
|---|---|---|
| `worker_proxy` | Client uploads to Worker, Worker forwards to S3 | System provider default |
| `direct` | Client uploads directly to presigned S3 URL | S3-compatible provider |

The S3-compatible provider uses `direct` mode for both upload and download, generating presigned URLs that expire after the grant TTL (10 minutes).

## Migration from System Provider

See `docs/storage/STORAGE_ABSTRACTION_DESIGN.md` §F for migration design.

```bash
# Dry-run migration
cheri storage migrate plan --to s3-compatible

# Execute migration (beta in v0.3)
cheri storage migrate --to s3-compatible --execute
```

## Security Notes

- Secrets stored in KV under `provider-secret:{workspace_id}:s3-compatible`, not in workspace metadata
- Presigned URLs expire after 10 minutes (same as grant TTL)
- Secrets never returned by API — `redactProvider()` masks them as `***`
- Endpoint must use `https://` in production

## Next Steps for v0.3.0-provider-beta

1. Complete S3-compatible provider with checksum verification
2. Add `copyObject` for migration support
3. Add MinIO-specific validation and compatibility notes
4. Build `cheri storage configure --provider s3-compatible` flow
5. Test with real S3 bucket, MinIO, and Backblaze B2