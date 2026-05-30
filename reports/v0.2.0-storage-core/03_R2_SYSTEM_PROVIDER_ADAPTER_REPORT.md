# 03 — R2 System Provider Adapter Report

## Implementation

`worker/storage/providers/system_r2.js` wraps the existing `HERMES_BUCKET` R2 binding.

## Key Methods

```javascript
async putObject({ providerObjectKey, body, contentType, metadata }) {
  await this.env.HERMES_BUCKET.put(providerObjectKey, body, {
    httpMetadata: { contentType },
    customMetadata: metadata,
  });
}

async getObject({ providerObjectKey }) {
  const object = await this.env.HERMES_BUCKET.get(providerObjectKey);
  if (!object) throw new StorageObjectNotFoundError(...);
  return { body: object.body, size: object.size, ... };
}

async deleteObject({ providerObjectKey }) {
  // Idempotent — ignore NotFound errors
  await this.env.HERMES_BUCKET.delete(providerObjectKey);
}

async listObjects({ prefix }) {
  const listed = await this.env.HERMES_BUCKET.list({ prefix });
  return { objects: listed.objects.map(...), has_more: listed.truncated };
}

async headObject({ providerObjectKey }) {
  const head = await this.env.HERMES_BUCKET.head(providerObjectKey);
  return head ? { size, content_type, etag, uploaded_at } : null;
}

async copyObject({ sourceKey, destKey }) {
  // Re-upload from source stream (no server-side copy in R2)
  const src = await this.env.HERMES_BUCKET.get(sourceKey);
  await this.env.HERMES_BUCKET.put(destKey, src.body, { httpMetadata: src.httpMetadata });
}
```

## Validation

```javascript
async validateConfig() {
  if (!this.env?.HERMES_BUCKET) {
    return { state: "misconfigured", available: false, errors: ["HERMES_BUCKET not configured"] };
  }
  return { state: "ready", available: true, warnings: ["Files are reset daily."] };
}
```

## Transfer Mode

Always `worker_proxy` — file bytes flow through the Worker. No presigned URLs.

## Object Key Format

`{workspaceId}/{fileId}/v{version}/{safeLogicalName}`

Examples:
- `wksp_abc123/file_xyz789/v1/notes.md`
- `wksp_abc123/file_xyz789/v2/notes.md`

## vs Previous Implementation

| Aspect | Before | After |
|---|---|---|
| Location | `worker/providers/system.js` | `worker/storage/providers/system_r2.js` |
| Extends | `BaseStorageProvider` | `BaseStorageProvider` |
| putObject | same | same |
| getObject | same | same (throws StorageObjectNotFoundError) |
| deleteObject | swallowed errors | idempotent (ignores NotFound) |
| headObject | returned null on missing | returns null on missing |
| copyObject | N/A | re-upload from source |

## Test Results

```
node tests/node/worker.test.mjs      # ✅ 6/6 pass (file upload/download via system)
node tests/node/storage.test.mjs     # ✅ 7/7 pass
```

## Backward Compatibility

- Existing upload grant → PUT → consumeUpload → putObject → R2 ✅
- Existing download grant → GET → consumeDownload → getObject → R2 ✅
- No changes to API routes or grant token format