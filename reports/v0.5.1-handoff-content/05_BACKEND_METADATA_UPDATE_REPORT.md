# Backend Metadata Update Report

## Overview
Worker added `PATCH /v1/handoffs/:id` route and `updateHandoff()` service function for updating handoff metadata after upload.

## Changes

### Worker PATCH Route (worker/index.js)

```javascript
} else if (method === "PATCH" && pathname === `/v1/handoffs/${handoffId}`) {
  requireWorkspaceAccess(env, ctx, state);
  const workspace = state.workspace;
  const user = state.user;

  const body = await request.json();
  const allowedFields = [
    "status", "file_count", "total_uploaded_size", "uploaded_file_ids",
    "manifest_file_id", "manifest_checksum", "failed_files", "provider_id",
  ];
  const updates = {};
  for (const field of allowedFields) {
    if (body[field] !== undefined) {
      updates[field] = body[field];
    }
  }

  const updated = await handoffService.updateHandoff(env, workspace, user, handoffId, updates);

  return new Response(JSON.stringify({ handoff: updated }), {
    headers: { "Content-Type": "application/json" },
  });
}
```

### updateHandoff Service Function (worker/handoff/service.js)

```javascript
export async function updateHandoff(env, workspace, user, handoffId, updates) {
  const membership = workspace.members?.find((m) => m.user_id === user.id);
  if (!membership) {
    throw new Error("Unauthorized: user is not a workspace member");
  }

  const kv = env.HERMES_KV || env.CHERI_KV;
  const kvKey = `${HANDOFF_KV_PREFIX}${workspace.id}:${handoffId}`;
  const raw = await kv.get(kvKey);
  if (!raw) {
    throw new Error("Handoff not found");
  }

  const record = JSON.parse(raw);
  if (record.workspace_id !== workspace.id) {
    throw new Error("Handoff not found");
  }

  const allowedFields = [
    "status", "file_count", "total_uploaded_size", "uploaded_file_ids",
    "manifest_file_id", "manifest_checksum", "failed_files", "provider_id",
  ];

  for (const field of allowedFields) {
    if (updates[field] !== undefined) {
      record[field] = updates[field];
    }
  }

  record.updated_at = new Date().toISOString();
  await kv.put(kvKey, JSON.stringify(record));

  return record;
}
```

## Security

| Check | Implementation |
|-------|----------------|
| Workspace membership required | `workspace.members?.find((m) => m.user_id === user.id)` |
| Workspace ownership verified | `if (record.workspace_id !== workspace.id)` returns error |
| Only allowed fields updated | Whitelist approach — only listed fields can be set |
| No secrets stored | `failed_files` is list of paths (strings), not content |

## Fields That Can Be Updated

| Field | Type | Description |
|-------|------|-------------|
| status | string | "created" / "uploading" / "ready" / "partial_failed" |
| file_count | int | Number of successfully uploaded files |
| total_uploaded_size | int | Sum of sizes of uploaded files |
| uploaded_file_ids | list[str] | File IDs from storage provider |
| manifest_file_id | string | File ID of uploaded manifest JSON |
| manifest_checksum | string | SHA-256 of manifest JSON |
| failed_files | list[str] | Relative paths that failed to upload |
| provider_id | string | Storage provider used (e.g., "system") |

## Exit Criteria

| Criterion | Status |
|-----------|--------|
| PATCH route exists in worker/index.js | PASS |
| updateHandoff() function exists in worker/handoff/service.js | PASS |
| Workspace membership check | PASS |
| Only allowed fields can be updated | PASS |
| Returns updated record | PASS |
| All service functions exported | PASS |