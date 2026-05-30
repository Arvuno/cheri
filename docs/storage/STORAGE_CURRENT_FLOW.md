# Storage Current Flow — Implementation Note

> Date: 2026-05-30
> Purpose: Internal audit before architectural changes. Not for external distribution.

---

## 1. R2 Binding Usage

### Bindings used

| Binding | Type | Used in |
|---|---|---|
| `HERMES_KV` | KV Namespace | All metadata (users, workspaces, files, grants, tasks, sessions) |
| `HERMES_BUCKET` | R2 Bucket | Blob storage via SystemStorageProvider |

### `worker/lib/storage.js`

Exports a full KV wrapper with helpers:
- `kvGet`, `kvSet`, `kvDelete` — raw JSON KV operations
- `saveFileRecord`, `loadFileRecord`, `getFileByName`, `listFilesByWorkspace`, `deleteFileRecord`
- `saveUploadGrant`, `loadUploadGrant`, `deleteUploadGrant` — 10-minute TTL grants
- `saveDownloadGrant`, `loadDownloadGrant`, `deleteDownloadGrant` — 10-minute TTL grants
- `saveWorkspace`, `loadWorkspace`
- `saveProviderSecrets`, `loadProviderSecrets`, `deleteProviderSecrets` — per workspace, per provider kind

KV key families:
```
user:{id}
user-name:{normalized_username}
workspace:{id}
session:{sha256(token)}
file:{workspace_id}:{file_id}
file-name:{workspace_id}:{name_key}
upload-grant:{sha256(token)}
download-grant:{sha256(token)}
provider-secret:{workspace_id}:{provider_kind}
task:{workspace_id}:{task_id}
activity:{workspace_id}
invite:{code}
```

### `worker/providers/system.js`

`SystemStorageProvider` directly calls `this.env.HERMES_BUCKET.put/get/delete/list/head`.

### `worker/services/file_service.js`

Imports `instantiateStorageProvider`, `resolveWorkspaceProviderConfig` from `provider_config.js`. Does NOT import anything from `storage.js` directly for blob operations — all blob I/O goes through the provider interface.

---

## 2. Upload Grant Flow

```
CLI: cheri file upload ./notes.md
  → Python: upload_file() in cheri_cloud_cli/files.py
  → HTTP POST /v1/files/upload-grant
  → Worker: createUploadGrant(env, workspace, user, body, origin)

Step-by-step inside createUploadGrant():
1. Validate filename, size (0 to 1 GB)
2. getWorkspaceStorageProvider(env, workspace)
   → resolveWorkspaceProviderConfig(env, workspace)  // merges secrets
   → instantiateStorageProvider(env, providerConfig)  // returns SystemStorageProvider
3. provider.validateConfig() → checks HERMES_BUCKET available
4. getFileByName(env, workspace.id, logicalName) → check for duplicate
5. createFileRegistryRecord() → creates file metadata with provider_kind from providerConfig
   - provider_object_key = "{workspaceId}/{fileId}/v{version}/{safeLogicalName}"
   - status = "upload_pending"
6. saveFileRecord(env, file)
7. createGrantToken() → random token
8. provider.generateUploadTarget({ workspace, file, expires_at })
   - SystemStorageProvider returns { mode: "worker_proxy", provider_object_key, headers: {} }
9. saveUploadGrant(env, token, { workspace_id, file_id, provider_kind, provider_object_key, provider_object_id, content_type, expires_at, target }, 10*60)
10. Return { file_id, provider, upload_url: "{origin}/v1/transfers/upload/{token}", expires_at }
```

Then CLI uploads via PUT to the grant URL. Worker handles it:

```
CLI: PUT /v1/transfers/upload/{token} body: <file-bytes>
  → Worker: consumeUpload(env, token, request)
  → loadUploadGrant(env, token) → grant
  → loadWorkspace, loadFileRecord
  → getWorkspaceStorageProvider(env, workspace)
  → provider.putObject({ providerObjectKey, providerObjectId, body, contentType, metadata })
    → SystemStorageProvider: HERMES_BUCKET.put(providerObjectKey, body, { httpMetadata: { contentType } })
  → provider.statObject({ providerObjectKey, providerObjectId })
  → applyProviderStatToFileRecord(file, providerStat)
  → saveFileRecord(env, updatedFileRecord)
  → deleteUploadGrant(env, token)
  → return { ok: true, file_id }
```

---

## 3. Download Grant Flow

```
CLI: cheri file download notes.md
  → HTTP GET /v1/files/{file_id}/download-grant
  → Worker: createDownloadGrant(env, workspace, user, fileId, origin)

Steps:
1. loadFileRecord(env, workspace.id, fileId)
2. getWorkspaceStorageProvider(env, workspace)
3. createGrantToken()
4. provider.generateDownloadTarget({ workspace, file, expires_at })
   → SystemStorageProvider: { mode: "worker_proxy", provider_object_key, headers: {} }
5. saveDownloadGrant(env, token, { workspace_id, file_id, provider_kind, provider_object_key, provider_object_id, expires_at, target }, 10*60)
6. Return { file_id, filename, provider, download_url: "{origin}/v1/transfers/download/{token}", expires_at }
```

Then CLI downloads via GET from the grant URL:

```
CLI: GET /v1/transfers/download/{token}
  → Worker: consumeDownload(env, token)
  → loadDownloadGrant → grant
  → loadWorkspace, loadFileRecord
  → getWorkspaceStorageProvider(env, workspace)
  → provider.getObject({ providerObjectKey, providerObjectId })
    → SystemStorageProvider: HERMES_BUCKET.get(providerObjectKey)
  → appendActivity(env, workspace.id, requested_by, "file_downloaded", ...)
  → deleteDownloadGrant(env, token)
  → return Response(object.body, headers)
```

---

## 4. File Metadata Shape

KV record under `file:{workspace_id}:{file_id}`:

```javascript
{
  id: "file_abc123...",        // stable file id
  workspace_id: "wksp_xyz...",
  logical_name: "notes.md",
  logical_name_key: "notesmd",  // lowercase, normalized
  provider_kind: "system",
  provider_object_key: "wksp_xyz/file_abc123/v1/notes.md",
  provider_object_id: "wksp_xyz/file_abc123/v1/notes.md",
  size: 12345,
  content_type: "text/markdown",
  checksum: "",
  local_modified_at: "",
  created_at: "2026-05-30T10:00:00Z",
  uploaded_at: "",
  updated_at: "2026-05-30T10:00:00Z",
  uploaded_by: "alice",
  last_modified_by: "alice",
  version: 1,
  revision_marker: "v1",
  remote_revision: "",
  sync_status: "upload_pending",   // upload_pending → uploaded → synced
  conflict_state: "clear",
  status: "upload_pending",         // upload_pending | uploaded | available
  history: [],
}
```

On re-upload (same filename):
- `existingFile` is passed to `createFileRegistryRecord`
- Version increments, new object key created with `/v{version}/`
- Previous entry pushed to `history` array
- `sync_status` reset to `upload_pending`

---

## 5. Provider Selection / Validation Points

### Where provider is selected

`normalizeProviderSelection(env, selection)` in `provider_config.js`:
- Default: `kind = "system"`
- System requires `warning_acknowledged: true`
- Experimental providers require `experimental_acknowledged: true` AND `CHERI_EXPERIMENTAL_PROVIDERS=1` env var

### Where provider is validated

1. **Pre-upload:** `provider.validateConfig()` in `createUploadGrant` — if `!available`, throws 503
2. **Pre-object-operation:** Each provider method (putObject, getObject) does availability check
3. **Workspace resolution:** `resolveWorkspaceProviderConfig` merges secrets from KV into providerConfig.settings

### Provider catalog (`providerCatalog(env, options)`)

`GET /v1/providers` returns all defined providers with their metadata. Experimental providers are filtered unless `include_experimental=1` query param is set.

---

## 6. Hardcoded System Provider Assumptions

| Location | Assumption |
|---|---|
| `normalizeProviderSelection()` | `kind` defaults to `"system"` |
| `PROVIDER_DEFINITIONS` | Only `system` has `selectable: true` |
| `provider_config.js:validateProviderSelection` | Uses `instantiateStorageProvider` which returns SystemStorageProvider by default |
| `file_service.js:cleanupExpiredSystemFiles` | Specifically checks `providerConfig.kind === "system"` and only cleans up system workspaces |
| `storage_registry.js:createFileRegistryRecord` | Calls `getWorkspaceProviderConfig(workspace)` to get `provider_kind` — but if no workspace storage config exists, this returns `null` for provider_kind |
| `SystemStorageProvider.validateConfig()` | Checks `env?.HERMES_BUCKET` exists; if not, returns `misconfigured` |
| All `generateUploadTarget`/`generateDownloadTarget` | Return `worker_proxy` mode — no direct R2 signed URL generation exists |

---

## 7. Backwards Compatibility Requirements

The following MUST remain working through the abstraction refactor:

1. **Existing file upload/download** — No change to CLI behavior or API route shapes
2. **Grant tokens** — Same 10-minute TTL, same grant structure in KV
3. **File metadata fields** — All existing fields preserved, provider_id and storage_key added (not replacing)
4. **Activity events** — `file_uploaded`, `file_modified`, `file_downloaded` — same payload shape
5. **Workspace storage config** — `workspace.storage.provider` object structure preserved
6. **Provider catalog API** — `GET /v1/providers` already exists and returns correct shape
7. **System provider** — Must remain the default, safe, recommended choice
8. **No new required fields** — Existing workspaces with no storage config should continue using system implicitly

---

## 8. Object Key Strategy

Current: `buildProviderObjectReference()` produces:
```
{workspaceId}/{fileId}/v{version}/{safeLogicalName}
```

Properties:
- Unique per file version (supports versioning via history array)
- Does NOT include raw user filename (uses `safeLogicalName` which normalizes)
- `safeLogicalName` from `security/tokens.js` — needs verification that it prevents path traversal
- No tenant prefix needed beyond workspace_id (workspace isolation is implicit)

Potential issues to address in design:
- Filename collision across different workspaces with same name — workspace_id included so this is fine
- Path traversal in safeLogicalName — needs audit
- No support for provider-specific key prefixes (e.g., S3 prefix per workspace) — will need to address in S3 provider config

---

## 9. What's Missing for Multi-Provider

1. **Provider interface for grant generation** — `generateUploadTarget`/`generateDownloadTarget` are per-provider but always return `worker_proxy` mode for System. For S3-compatible, these would need to return signed URL or different mode.
2. **No multipart upload support** — Current interface is single `putObject` call. S3 multipart would need different abstraction.
3. **No object listing by prefix** — `listObjects` exists in provider interface but is not called in production code paths (only in `cleanupExpiredSystemFiles`).
4. **No copy object** — No provider method for server-side copy.
5. **No checksum verification** — metadata has `checksum` field but it's not validated after upload.
6. **Provider secret storage** — Uses KV but secrets are stored as JSON with no encryption layer.