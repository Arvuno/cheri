# System R2 Provider

> Date: 2026-05-30
> Status: Ready (default provider)

## Overview

The System provider uses Cloudflare R2 through the `HERMES_BUCKET` binding. It is the default and only production-ready provider in v0.2.0.

## Binding Requirements

```javascript
// wrangler.toml
[[r2_buckets]]
binding = "HERMES_BUCKET"
bucket_name = "cheri-files"  // or your configured bucket name
```

```javascript
// Worker env type
interface Env {
  HERMES_BUCKET: R2Bucket;
  HERMES_KV: KVNamespace;
}
```

## Provider Definition

```javascript
{
  kind: "system",
  label: "System (recommended)",
  status: "ready",
  temporary: true,
  resetPolicy: "daily",
  integrationStatus: "connected",
  selectable: true,
  experimental: false,
  fields: [],  // No user-configurable fields
}
```

## Capabilities

| Capability | Supported |
|---|---|
| putObject | ✅ |
| getObject | ✅ |
| deleteObject | ✅ |
| listObjects | ✅ |
| headObject | ✅ |
| copyObject | ✅ (via re-upload) |
| signedUploadUrl | ❌ |
| signedDownloadUrl | ❌ |
| multipart | ❌ |
| checksum | ❌ |

## Object Key Format

```
{workspace_id}/{file_id}/v{version}/{safeLogicalName}
```

Example: `wksp_abc123/file_xyz789/v1/notes.md`

Keys do NOT include a `workspaces/` or `files/` prefix in the current implementation (that prefix is reserved for future canonical format). The format is workspace-scoped and versioned.

## Upload Flow

1. `createUploadGrant` generates a `worker_proxy` target
2. Client PUTs file to `/v1/transfers/upload/{token}`
3. `consumeUpload` calls `provider.putObject()` with the file body
4. `provider.statObject()` is called to get final size/etag
5. File record updated with sync_status = "synced"

## Download Flow

1. `createDownloadGrant` generates a `worker_proxy` target
2. Client GETs `/v1/transfers/download/{token}`
3. `consumeDownload` calls `provider.getObject()` and streams the body
4. Activity event appended, grant deleted

## Limitations

- **Temporary storage:** Files are reset daily by `cleanupExpiredSystemFiles`
- **No presigned URLs:** All transfers go through the Worker (latency overhead)
- **No server-side copy:** Copy implemented as re-upload from source object
- **No checksum verification:** MD5/SHA-256 not validated after upload
- **No multipart:** Large file uploads must fit within a single putObject call

## Environment Variables

| Variable | Effect |
|---|---|
| `CHERI_EXPERIMENTAL_PROVIDERS=1` | Enables experimental provider selection UI |

## Validation

```javascript
async validateConfig() {
  if (!this.env?.HERMES_BUCKET) {
    return { state: "misconfigured", available: false, errors: ["HERMES_BUCKET is not configured"] };
  }
  return { state: "ready", available: true, warnings: ["Files are reset daily."] };
}
```