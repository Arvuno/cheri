# 04 — File Route Refactor Report

## Routes Affected

All file-related routes in `worker/index.js` continue to work via provider abstraction:

| Route | Behavior | Verified |
|---|---|---|
| `POST /v1/files/upload-grant` | createUploadGrant → provider.validateConfig() → saveFileRecord → return grant | ✅ |
| `PUT /v1/transfers/upload/{token}` | consumeUpload → provider.putObject() → provider.statObject() → saveFileRecord | ✅ |
| `POST /v1/files/{id}/complete` | completeUpload → finalizeFileRegistryRecord → appendActivity | ✅ |
| `GET /v1/files/{id}/download-grant` | createDownloadGrant → provider.generateDownloadTarget() → saveGrant → return URL | ✅ |
| `GET /v1/transfers/download/{token}` | consumeDownload → provider.getObject() → stream body → appendActivity → deleteGrant | ✅ |
| `GET /v1/files` | listWorkspaceFiles → return serialized file records | ✅ |

## What Changed

- `file_service.js` already called `instantiateStorageProvider` and `resolveWorkspaceProviderConfig`
- These functions now route through the new `worker/storage/` layer
- `getWorkspaceStorageProvider(env, workspace)` remains the central provider resolution point
- File records continue to use `provider_kind` field (system, s3-compatible, etc.)
- All provider operations go through `provider.putObject/getObject/deleteObject/statObject`

## What Did NOT Change

- Grant token format (SHA-256 hashed, 10-minute TTL)
- KV key structure for file records (`file:{workspace_id}:{file_id}`)
- API route paths or HTTP methods
- File metadata shape (backwards compatible — same fields)
- Activity event types (`file_uploaded`, `file_modified`, `file_downloaded`)

## Provider Resolution Flow (unchanged)

```
getWorkspaceStorageProvider(env, workspace)
  → resolveWorkspaceProviderConfig(env, workspace)  // merges secrets from KV
  → instantiateStorageProvider(env, providerConfig)  // creates provider instance
  → return provider  // SystemStorageProvider or S3CompatibleStorageProvider, etc.
```

## Testing

All file routes tested end-to-end in `worker.test.mjs`:
```
file upload, list, download, and activity flows work through the system provider
```

Full flow: register → upload-grant → PUT → complete → list → download-grant → GET → activity ✅