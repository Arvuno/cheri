# Storage Provider Contract

> Date: 2026-05-30
> Status: v0.2.0-storage-core

---

## Interface

Every blob storage provider implements the `BlobStorageProvider` interface.

```typescript
interface BlobStorageProvider {
  // Identity
  readonly id: string;           // Provider kind, e.g. "system"
  readonly label: string;        // Human-readable label

  // Status — one of: ready, experimental, not_ready, deprecated
  readonly status: ProviderStatus;

  // Capabilities — which operations are supported
  readonly capabilities: ProviderCapabilities;

  // Lifecycle
  validateConfig(config: ProviderConfig, env: Env): Promise<ValidationResult>;
  createUploadTarget(context: UploadContext): Promise<UploadTarget>;
  completeUpload(context: CompleteUploadContext): Promise<void>;
  createDownloadTarget(context: DownloadContext): Promise<DownloadTarget>;
  deleteObject(context: DeleteObjectContext): Promise<void>;
  headObject(context: HeadObjectContext): Promise<ObjectStat | null>;
  listObjects?(context: ListObjectsContext): Promise<ObjectListing>;
  copyObject?(context: CopyObjectContext): Promise<void>;
}

// Capability flags
interface ProviderCapabilities {
  upload: boolean;           // putObject
  download: boolean;        // getObject
  delete: boolean;          // deleteObject
  list: boolean;            // listObjects
  signedUploadUrl: boolean; // generateUploadTarget returns direct URL
  signedDownloadUrl: boolean; // generateDownloadTarget returns direct URL
  multipart: boolean;        // Supports chunked/multipart upload
  checksum: boolean;         // Checksum verification after upload
  serverSideCopy: boolean;   // copyObject
}

// Provider status
type ProviderStatus = "ready" | "experimental" | "not_ready" | "deprecated";

// Validation
interface ValidationResult {
  state: "pending" | "configured" | "ready" | "misconfigured" | "validated-config";
  available: boolean;
  errors: string[];
  warnings: string[];
}
```

---

## Required Methods

### `validateConfig(config, env)`

Checks that the provider is correctly configured for the current deployment.

**System provider** — checks `HERMES_BUCKET` binding exists.

**S3-compatible** — checks endpoint is reachable and credentials are valid.

**Returns:** `ValidationResult`
- `state: "ready", available: true` — Provider can handle requests
- `state: "misconfigured", available: false` — Provider is not usable, errors array explains why
- `state: "validated-config", available: false` — Config is valid but provider not enabled in this deployment

---

### `createUploadTarget(context)`

Prepares an upload operation and returns where/how to upload.

**Context:**
```typescript
interface UploadContext {
  workspace: Workspace;
  file: FileRecord;
  expires_at: string;  // ISO 8601
}
```

**Returns:** `UploadTarget`
```typescript
interface UploadTarget {
  mode: "worker_proxy" | "direct";  // worker_proxy = PUT through Worker; direct = signed URL
  upload_url?: string;                // Required if mode = "direct"
  provider_object_key: string;
  provider_object_id: string;
  headers?: Record<string, string>;   // For worker_proxy mode
  expires_at: string;
}
```

**worker_proxy mode** — client PUTs file to `/v1/transfers/upload/{grantToken}`. Worker proxies to provider. Used by System provider.

**direct mode** — client PUTs directly to `upload_url` (a signed URL). Used by S3-compatible providers that support presigned URLs.

---

### `completeUpload(context)`

Called after a successful upload to perform post-upload steps (e.g., verifying checksum, updating metadata).

**Context:**
```typescript
interface CompleteUploadContext {
  workspace: Workspace;
  file: FileRecord;
  provider_object_key: string;
  provider_object_id: string;
}
```

**Returns:** `void`

**Behavior for System provider:** Calls `statObject` to confirm the blob exists and update the file record with final size/etag.

---

### `createDownloadTarget(context)`

Prepares a download operation.

**Context:**
```typescript
interface DownloadContext {
  workspace: Workspace;
  file: FileRecord;
  expires_at: string;
}
```

**Returns:** `DownloadTarget`
```typescript
interface DownloadTarget {
  mode: "worker_proxy" | "direct";
  download_url?: string;           // Required if mode = "direct"
  provider_object_key: string;
  provider_object_id: string;
  headers?: Record<string, string>;
  expires_at: string;
}
```

---

### `deleteObject(context)`

Deletes a blob from the provider.

**Context:**
```typescript
interface DeleteObjectContext {
  providerObjectKey: string;
  providerObjectId: string;
}
```

**Returns:** `void`

Throws `STORAGE_OBJECT_NOT_FOUND` if the object does not exist (provider may have already cleaned it up).

---

### `headObject(context)`

Gets metadata for a single object without returning the body.

**Context:**
```typescript
interface HeadObjectContext {
  providerObjectKey: string;
  providerObjectId: string;
}
```

**Returns:** `ObjectStat | null`
```typescript
interface ObjectStat {
  provider_object_key: string;
  provider_object_id: string;
  size: number;
  content_type: string;
  etag: string;
  uploaded_at: string;
}
```

Returns `null` if the object does not exist.

---

## Optional Methods

### `listObjects(context)`

Lists objects with a prefix.

**Context:**
```typescript
interface ListObjectsContext {
  prefix?: string;       // Filter to keys starting with this prefix
  cursor?: string;       // Pagination cursor
  limit?: number;       // Max results (default 100)
}
```

**Returns:** `ObjectListing`
```typescript
interface ObjectListing {
  objects: ObjectStat[];
  next_cursor?: string;
  has_more: boolean;
}
```

**Used by:** `cleanupExpiredSystemFiles` only.

---

### `copyObject(context)`

Copies a blob within the same provider (server-side copy).

**Context:**
```typescript
interface CopyObjectContext {
  source_key: string;
  source_id: string;
  dest_key: string;
  dest_id: string;
  metadata?: Record<string, string>;
}
```

**Returns:** `void`

Used by migration tooling.

---

## Error Codes

All provider errors extend `StorageError`:

```javascript
// Provider not available in this deployment
class ProviderNotReadyError extends StorageError {
  code = "PROVIDER_NOT_READY";
  httpStatus = 503;
}

// Provider config is invalid (missing fields, malformed values)
class ProviderConfigInvalidError extends StorageError {
  code = "PROVIDER_CONFIG_INVALID";
  httpStatus = 400;
}

// Required secret is missing from env or KV store
class ProviderSecretMissingError extends StorageError {
  code = "PROVIDER_SECRET_MISSING";
  httpStatus = 500;
}

// Upload failed (network, bucket permissions, etc.)
class StorageUploadFailedError extends StorageError {
  code = "STORAGE_UPLOAD_FAILED";
  httpStatus = 500;
}

// Download failed
class StorageDownloadFailedError extends StorageError {
  code = "STORAGE_DOWNLOAD_FAILED";
  httpStatus = 500;
}

// Object not found in provider
class StorageObjectNotFoundError extends StorageError {
  code = "STORAGE_OBJECT_NOT_FOUND";
  httpStatus = 404;
}
```

---

## Provider Definitions

Stored in `worker/services/provider_config.js` as `PROVIDER_DEFINITIONS`:

```typescript
const PROVIDER_DEFINITIONS = {
  "system": {
    kind: "system",
    label: "System (recommended)",
    status: "ready",           // Not explicit in current code, inferred from capabilities
    capabilities: {
      upload: true,
      download: true,
      delete: true,
      list: true,
      signedUploadUrl: false,  // Uses worker_proxy
      signedDownloadUrl: false,
      multipart: false,
      checksum: false,
      serverSideCopy: false,
    },
    // ... other fields
  },
  "s3-compatible": {
    kind: "s3-compatible",
    label: "S3-compatible",
    status: "experimental",
    // ...
  },
  // ...
};
```

---

## Status Lifecycle

| Status | Meaning | Provider visible in catalog? | Can be selected by users? |
|---|---|---|---|
| `ready` | Production-ready | Yes, always | Yes, if selectable |
| `experimental` | Works but may change | Yes, with flag | Yes, with explicit acknowledgment |
| `not_ready` | Scaffolded but not functional | Yes | No |
| `deprecated` | Still works but will be removed | Yes | Warns users |

---

## Provider Catalog API

`GET /v1/providers` returns an array of provider catalog entries:

```json
{
  "providers": [
    {
      "kind": "system",
      "label": "System (recommended)",
      "status": "ready",
      "capabilities": {
        "upload": true,
        "download": true,
        "delete": true,
        "list": true,
        "signedUploadUrl": false,
        "signedDownloadUrl": false,
        "multipart": false,
        "checksum": false,
        "serverSideCopy": false
      },
      "temporary": true,
      "experimental": false,
      "selectable": true,
      "coming_soon": false,
      "reset_policy": "daily"
    }
  ]
}
```

Secrets are never included. `credential_fields` shows which fields are needed but not their values.

---

## Implementation Notes

1. **Worker runtime constraints:** Providers run inside Cloudflare Workers. Avoid Node.js-only SDKs that haven't been bundled for the Workers runtime. The `@aws-sdk/client-s3` package works in Workers when properly bundled.

2. **Provider instantiation:** `instantiateStorageProvider(env, providerConfig)` in `provider_config.js` creates instances. No provider class is instantiated until needed.

3. **Provider separation:** Each provider is a single `.js` file under `worker/providers/`. The provider file exports a class that extends `BaseStorageProvider`.

4. **Base class:** `BaseStorageProvider` in `worker/providers/base.js` provides default implementations that throw `PROVIDER_NOT_READY`. Providers only override what they support.

5. **Testing:** Providers that cannot run in a Worker test environment (e.g., Local filesystem provider) are implemented as test adapters with clear "test-only" markers in their docstrings.