# S3-Compatible Beta Status Report

## Status: CONFIG_ONLY (not BETA_WORKING)

Config shape validation works. Actual file transfer is scaffolded but not enabled.

## What Works

- `POST /v1/providers/validate` accepts S3-compatible config
- Validation returns correct `state: "validated-config", available: false`
- Warnings include: "S3-compatible transport is scaffolded but not enabled"
- Config saves to workspace storage via `/v1/storage/configure`
- Secrets are AES-GCM encrypted when `CHERI_PROVIDER_SECRET_KEY` is set

## What Does NOT Work

- Upload: `createUploadGrant()` calls `provider.createUploadTarget()` → returns `worker_proxy` mode
- The worker proxy routes (`PUT /v1/transfers/upload/:token`, `GET /v1/transfers/download/:token`)
  are implemented and forward to the actual provider, but the S3 provider's `putObject()`/`getObject()`
  throw `503 "S3-compatible cannot store files in this deployment"` because `supportsDirectTransfers: false`
- Download: same — `createDownloadGrant()` → worker proxy → 503 from S3 provider

## Implementation Path to BETA_WORKING

1. Implement actual S3 `putObject()`/`getObject()` in `worker/providers/s3.js` using `@aws-sdk/client-s3`
2. Configure presigned URL generation or use worker-to-S3 direct transfer
3. Add MinIO path-style support (`force_path_style: true` in settings)
4. Test with real S3-compatible endpoint (MinIO or LocalStack)

## Current S3 Provider Fields

```javascript
{ key: "endpoint", label: "Endpoint URL", required: true, secret: false }
{ key: "bucket", label: "Bucket name", required: true, secret: false }
{ key: "region", label: "Region", required: true, secret: false, default: "auto" }
{ key: "access_key_id", label: "Access key id", required: true, secret: false }
{ key: "secret_access_key", label: "Secret access key", required: true, secret: true }
```

## CLI Behavior

```
cheri storage configure --provider s3-compatible
  → Prompts for all 5 fields
  → Validates via /v1/providers/validate
  → Shows warnings about scaffolded status
  → Configures workspace (secrets encrypted)
  → "Provider is not available. Use anyway?" prompt
```

## Honest Status Note

Until actual S3 put/get is implemented, S3-compatible is a config-only provider.
The CLI and docs clearly state this. Users can configure it but cannot transfer files.