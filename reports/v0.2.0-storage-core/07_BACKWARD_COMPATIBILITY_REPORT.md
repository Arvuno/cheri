# 07 — Backward Compatibility Report

## API Routes — Unchanged

All existing routes continue to work with identical paths and methods:
- `POST /v1/files/upload-grant` → same response shape
- `PUT /v1/transfers/upload/{token}` → same behavior
- `POST /v1/files/{id}/complete` → same response shape
- `GET /v1/files/{id}/download-grant` → same response shape
- `GET /v1/transfers/download/{token}` → same streaming behavior
- `GET /v1/files` → same file list response shape

## Grant Tokens — Unchanged

10-minute TTL, same hash format, same KV structure. No migration needed.

## File Metadata — Preserved

All existing fields in `FileRecord` preserved:
- `id`, `workspace_id`, `logical_name`, `logical_name_key`
- `provider_object_key`, `provider_object_id`
- `size`, `content_type`, `checksum`
- `created_at`, `updated_at`, `uploaded_at`
- `uploaded_by`, `last_modified_by`
- `version`, `revision_marker`, `remote_revision`
- `sync_status`, `conflict_state`, `status`
- `history[]` array for version chain

New fields added (non-breaking):
- `provider_id` — populated from provider config.kind

## Workspace Storage Config — Unchanged

`workspace.storage.provider` object format unchanged:
```javascript
{
  kind: "system",  // or "s3-compatible" etc.
  label: "...",
  settings: {...},
  validation: {...},
  // ...
}
```

## Activity Events — Unchanged

`file_uploaded`, `file_modified`, `file_downloaded` events — same payload shape.

## Provider Catalog API — Extended

`GET /v1/providers` existed before — still returns all providers. Now includes:
- `status` field (ready/experimental/not_ready/deprecated)
- `capabilities` object
- `experimental` flag

No changes to existing response structure — only additions.

## What IS New

- `worker/storage/` module with `BlobStorageProvider` interface
- `provider_id` field in file metadata (backwards compatible — same value as `provider_kind`)
- `cheri storage` CLI commands (additive, no breaking change)
- New error codes in `StorageError` hierarchy

## Breaking Changes — None

No existing functionality removed or changed in a breaking way.

## Migration Path

Existing workspaces with no `workspace.storage.provider` config continue to use `system` as the implicit default (via `getWorkspaceProviderConfig` fallback).