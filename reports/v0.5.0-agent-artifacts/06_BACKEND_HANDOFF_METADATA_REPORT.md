# Backend Handoff Metadata Report

## Overview

Handoff metadata (not file content — files use storage provider abstraction) is stored and managed via four Worker routes:

- `POST /v1/handoffs` — create handoff metadata
- `GET /v1/handoffs` — list workspace handoffs
- `GET /v1/handoffs/:id` — get single handoff
- `GET /v1/handoffs/latest` — get most recent handoff

## Implementation

### Worker Routes

Located in: `worker/index.js`

```javascript
// GET /v1/handoffs — list workspace handoffs
if (path === "/v1/handoffs" && request.method === "GET") {
  const access = await requireWorkspaceAccess(request, env);
  return json({ handoffs: await listWorkspaceHandoffs(env, access.workspace.id) }, 200, request, env);
}

// POST /v1/handoffs — create handoff metadata
if (path === "/v1/handoffs" && request.method === "POST") {
  await enforceRateLimit(request, env, "handoff-create", { limit: 30, windowSeconds: 10 * 60 });
  const access = await requireWorkspaceAccess(request, env);
  const body = await parseJson(request);
  return json({ handoff: await createHandoff(env, access.workspace, access.user, body) }, 201, request, env);
}

// GET /v1/handoffs/latest — get most recent handoff
if (path === "/v1/handoffs/latest" && request.method === "GET") {
  const access = await requireWorkspaceAccess(request, env);
  return json({ handoff: await getLatestHandoff(env, access.workspace.id) }, 200, request, env);
}

// GET /v1/handoffs/:id — get handoff by ID
if (path.match(/^\/v1\/handoffs\/[^/]+$/) && request.method === "GET") {
  const access = await requireWorkspaceAccess(request, env);
  const handoffId = path.split("/")[3];
  return json({ handoff: await getHandoff(env, access.workspace, handoffId) }, 200, request, env);
}
```

### Handoff Service

Located in: `worker/handoff/service.js`

```javascript
export async function createHandoff(env, workspace, user, body)
export async function getHandoff(env, workspace, handoffId)
export async function listWorkspaceHandoffs(env, workspaceId)
export async function getLatestHandoff(env, workspaceId)
```

## KV Storage

Handoffs are stored in the Cheri KV store:

- **Key pattern**: `handoff:{workspace_id}:{handoff_id}`
- **Index key**: `handoff_index:{workspace_id}`

The index stores an array of `{ id, created_at }` entries (most recent first), keeping the last 100 handoffs.

## Data Model

### HandoffRecord

```javascript
{
  id: string,                    // handoff_id
  workspace_id: string,
  name: string,
  description: string,
  tags: string[],
  source_path: string,
  file_count: number,
  total_size: number,
  manifest_path: string,
  manifest_checksum: string,
  agent_name: string | null,
  tool_name: string | null,
  version_label: string | null,
  git_branch: string | null,
  git_commit: string | null,
  notes: string,
  status: string,                // "created"
  created_at: string,            // ISO timestamp
  created_by: string,            // username
}
```

## Authorization

All routes require:
1. Valid user session (via `requireUserSession`)
2. Workspace membership (via `requireWorkspaceAccess`)

Cross-workspace access is denied:
- Dave cannot access Carol's handoffs in Carol's workspace
- If Dave tries to access Carol's handoff ID with his workspace, the service returns `null` (or 401)

## Rate Limiting

`POST /v1/handoffs` is rate-limited:
- 30 requests per 10-minute window
- Key: `handoff-create:{user_id}`

## CLI Integration

The Python CLI uses `cheri_cloud_cli/client.py` methods:

```python
def list_handoffs(self, state: AuthState, workspace_id: str) -> List[Dict[str, Any]]
def get_handoff(self, state: AuthState, handoff_id: str) -> Dict[str, Any]
def get_latest_handoff(self, state: AuthState, workspace_id: str) -> Dict[str, Any]
def create_handoff(self, state: AuthState, workspace_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]
```

## Limitations

### What is NOT stored in backend:
- Full manifest (stored locally at source_path)
- File content (handled via storage provider abstraction)
- Skipped sensitive file contents (never stored)

### What IS stored:
- Handoff metadata (name, description, tags, etc.)
- Git context (branch, commit, dirty, redacted remote)
- File count and total size
- Agent/tool metadata

### Privacy
- Manifest is NOT stored in backend (only local file)
- Handoff metadata is visible to all workspace members
- No secret values are stored

## Tests

Worker tests verify:
1. Create handoff metadata
2. List workspace handoffs
3. Get single handoff
4. Get latest handoff
5. Unauthorized access denied (no token)
6. Cross-workspace access denied
7. Workspace membership required

See: `tests/node/worker.test.mjs` — `handoff routes create, list, show, and get latest handoff metadata`