/**
 * Handoff service for the Worker.
 * Manages handoff metadata (not file storage — files go through storage provider abstraction).
 */

// Note: workspace parameter already contains members array from requireWorkspaceAccess

const HANDOFF_KV_PREFIX = "handoff:";

/**
 * Create a new handoff record in KV.
 * Does NOT upload files — files are handled separately via storage provider.
 */
export async function createHandoff(env, workspace, user, body) {
  const id = body.handoff_id || `hnd_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;

  // Validate workspace membership
  const membership = workspace.members?.find((m) => m.user_id === user.id);
  if (!membership) {
    throw new Error("Unauthorized: user is not a workspace member");
  }

  const now = new Date().toISOString();

  const record = {
    id,
    workspace_id: workspace.id,
    name: body.name || "",
    description: body.description || "",
    tags: body.tags || [],
    source_path: body.source_path || "",
    file_count: body.file_count || 0,
    total_size: body.total_size || 0,
    manifest_path: body.manifest_path || "cheri-handoff.json",
    manifest_checksum: body.manifest_checksum || "",
    agent_name: body.agent_name || null,
    tool_name: body.tool_name || null,
    version_label: body.version_label || null,
    git_branch: body.git_branch || null,
    git_commit: body.git_commit || null,
    notes: body.notes || "",
    status: "created",
    created_at: now,
    created_by: user.username,
  };

  // Store in KV (use HERMES_KV for compatibility with test harness)
  const kvKey = `${HANDOFF_KV_PREFIX}${workspace.id}:${id}`;
  const kv = env.HERMES_KV || env.CHERI_KV;
  await kv.put(kvKey, JSON.stringify(record));

  // Also add to workspace handoff index (sorted by creation time)
  const indexKey = `handoff_index:${workspace.id}`;
  const existingIndex = await kv.get(indexKey);
  const index = existingIndex ? JSON.parse(existingIndex) : [];
  index.unshift({ id, created_at: now });
  // Keep only last 100
  if (index.length > 100) {
    index.length = 100;
  }
  await kv.put(indexKey, JSON.stringify(index));

  return record;
}

/**
 * Get a handoff by ID within a workspace.
 */
export async function getHandoff(env, workspace, handoffId) {
  const kv = env.HERMES_KV || env.CHERI_KV;
  const kvKey = `${HANDOFF_KV_PREFIX}${workspace.id}:${handoffId}`;
  const raw = await kv.get(kvKey);
  if (!raw) {
    return null;
  }
  const record = JSON.parse(raw);

  // Verify workspace match
  if (record.workspace_id !== workspace.id) {
    return null;
  }

  return record;
}

/**
 * List handoffs for a workspace (most recent first).
 */
export async function listWorkspaceHandoffs(env, workspaceId) {
  const kv = env.HERMES_KV || env.CHERI_KV;
  const indexKey = `handoff_index:${workspaceId}`;
  const existingIndex = await kv.get(indexKey);
  if (!existingIndex) {
    return [];
  }

  const index = JSON.parse(existingIndex);
  const records = [];

  for (const entry of index) {
    const kvKey = `${HANDOFF_KV_PREFIX}${workspaceId}:${entry.id}`;
    const raw = await kv.get(kvKey);
    if (raw) {
      records.push(JSON.parse(raw));
    }
  }

  return records;
}

/**
 * Get the most recent handoff for a workspace.
 */
export async function getLatestHandoff(env, workspaceId) {
  const handoffs = await listWorkspaceHandoffs(env, workspaceId);
  return handoffs[0] || null;
}

/**
 * Update handoff metadata fields.
 */
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

  // Verify workspace match
  if (record.workspace_id !== workspace.id) {
    throw new Error("Handoff not found");
  }

  // Only allow certain fields to be updated
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