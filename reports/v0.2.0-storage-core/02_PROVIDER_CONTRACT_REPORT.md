# 02 — Provider Contract Report

## Contract Implementation

All providers implement `BlobStorageProvider` interface:

```javascript
interface BlobStorageProvider {
  id: string;          // provider kind, e.g. "system"
  label: string;      // human-readable
  status: string;     // "ready" | "experimental" | "not_ready" | "deprecated"
  capabilities: ProviderCapabilities;

  validateConfig(config, env): Promise<ValidationResult>;
  createUploadTarget(context): Promise<UploadTarget>;
  completeUpload(context): Promise<void>;
  createDownloadTarget(context): Promise<DownloadTarget>;
  deleteObject(context): Promise<void>;
  headObject(context): Promise<ObjectStat | null>;
  listObjects?(context): Promise<ObjectListing>;
  copyObject?(context): Promise<void>;
}
```

## Provider Status Matrix

| Provider | Status | validateConfig | putObject | getObject | deleteObject | headObject | listObjects | createUploadTarget |
|---|---|---|---|---|---|---|---|---|
| System | ready | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ worker_proxy |
| Local Dev | experimental (test-only) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ worker_proxy |
| S3-compatible | experimental | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ direct (presigned) |

## Capabilities by Provider

| Capability | System | S3-compatible | Local Dev |
|---|---|---|---|
| upload | ✅ | ✅ | ✅ |
| download | ✅ | ✅ | ✅ |
| delete | ✅ | ✅ | ✅ |
| list | ✅ | ✅ | ✅ |
| signedUploadUrl | ❌ | ✅ | ❌ |
| signedDownloadUrl | ❌ | ✅ | ❌ |
| multipart | ❌ | ✅ | ❌ |
| checksum | ❌ | ✅ | ❌ |
| serverSideCopy | ❌ | ✅ | ❌ |

## Error Codes

Defined in `worker/storage/errors.js`:
- `PROVIDER_NOT_READY` (503)
- `PROVIDER_CONFIG_INVALID` (400)
- `PROVIDER_SECRET_MISSING` (500)
- `STORAGE_UPLOAD_FAILED` (500)
- `STORAGE_DOWNLOAD_FAILED` (500)
- `STORAGE_OBJECT_NOT_FOUND` (404)
- `INVALID_OBJECT_KEY` (400)

## Validation States

| State | Meaning | available |
|---|---|---|
| `pending` | Not yet validated | false |
| `configured` | Config provided but not checked | false |
| `ready` | Config valid and provider operational | true |
| `misconfigured` | Config invalid | false |
| `validated-config` | Config valid but not enabled | false |

## Provider Catalog API

`GET /v1/providers` returns entries without secrets:
```json
{
  "providers": [{
    "kind": "system",
    "label": "System (recommended)",
    "status": "ready",
    "capabilities": {...},
    "selectable": true,
    "experimental": false,
    "credential_fields": []
  }]
}
```

## Test Coverage

- Provider catalog exposes system as ready and other providers as coming soon
- Experimental providers hidden unless include_experimental=1
- Provider validate endpoint accepts system and returns redacted config
- No secrets in provider API responses