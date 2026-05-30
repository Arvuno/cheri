import { HttpError } from "./http.js";
import { isoNow, normalizeLogicalName, normalizeUsername, sha256 } from "../security/tokens.js";

// KV key families are intentionally grouped by domain so a future D1/Postgres
// migration can replace each namespace independently.
const KEY_PREFIX = {
  USER: "user:",
  USERNAME_INDEX: "user-name:",
  WORKSPACE: "workspace:",
  SESSION: "session:",
  FILE: "file:",
  FILE_NAME_INDEX: "file-name:",
  UPLOAD_GRANT: "upload-grant:",
  DOWNLOAD_GRANT: "download-grant:",
  INVITE: "invite:",
  ACTIVITY: "activity:",
  TASK: "task:",
  PROVIDER_SECRET: "provider-secret:",
};

export async function kvGet(env, key) {
  const raw = await env.HERMES_KV.get(key);
  return raw ? JSON.parse(raw) : null;
}

export async function kvSet(env, key, value, options = {}) {
  await env.HERMES_KV.put(key, JSON.stringify(value), options);
}

export async function kvDelete(env, key) {
  await env.HERMES_KV.delete(key);
}

export async function listJsonByPrefix(env, prefix) {
  const entries = [];
  let cursor;
  do {
    const listed = await env.HERMES_KV.list(cursor ? { prefix, cursor } : { prefix });
    for (const item of listed.keys) {
      const value = await kvGet(env, item.name);
      if (value) {
        entries.push(value);
      }
    }
    cursor = listed.list_complete ? undefined : listed.cursor;
  } while (cursor);
  return entries;
}

export async function saveUser(env, user) {
  user.updated_at = isoNow();
  await kvSet(env, `${KEY_PREFIX.USER}${user.id}`, user);
  await kvSet(env, `${KEY_PREFIX.USERNAME_INDEX}${user.username_key}`, { user_id: user.id });
}

export async function loadUser(env, userId) {
  return kvGet(env, `${KEY_PREFIX.USER}${userId}`);
}

export async function getUserByUsername(env, username) {
  const normalized = normalizeUsername(username);
  const ref = await kvGet(env, `${KEY_PREFIX.USERNAME_INDEX}${normalized}`);
  if (!ref?.user_id) {
    return null;
  }
  return loadUser(env, ref.user_id);
}

export async function saveWorkspace(env, workspace) {
  workspace.updated_at = isoNow();
  await kvSet(env, `${KEY_PREFIX.WORKSPACE}${workspace.id}`, workspace);
}

export async function loadWorkspace(env, workspaceId) {
  return kvGet(env, `${KEY_PREFIX.WORKSPACE}${workspaceId}`);
}

export async function listWorkspacesForUser(env, user) {
  const ids = [...new Set((user.workspace_memberships || []).map((membership) => membership.workspace_id))];
  const workspaces = await Promise.all(ids.map((workspaceId) => loadWorkspace(env, workspaceId)));
  return workspaces.filter(Boolean);
}

export async function saveSession(env, token, session, ttlSeconds = 7 * 24 * 3600) {
  const tokenHash = await sha256(token);
  await kvSet(env, `${KEY_PREFIX.SESSION}${tokenHash}`, session, { expirationTtl: ttlSeconds });
}

export async function deleteSession(env, token) {
  const tokenHash = await sha256(token);
  await kvDelete(env, `${KEY_PREFIX.SESSION}${tokenHash}`);
}

export async function requireUserSession(request, env) {
  const authorization = request.headers.get("Authorization") || "";
  if (!authorization.startsWith("Bearer ")) {
    throw new HttpError(401, "Unauthorized.");
  }
  const token = authorization.slice("Bearer ".length).trim();
  if (!token) {
    throw new HttpError(401, "Unauthorized.");
  }
  const tokenHash = await sha256(token);
  const session = await kvGet(env, `${KEY_PREFIX.SESSION}${tokenHash}`);
  if (!session) {
    throw new HttpError(401, "Session expired. Run `cheri login` again.");
  }
  const user = await loadUser(env, session.user_id);
  if (!user) {
    throw new HttpError(401, "User not found.");
  }
  session.last_used_at = isoNow();
  await kvSet(env, `${KEY_PREFIX.SESSION}${tokenHash}`, session, { expirationTtl: 7 * 24 * 3600 });
  return { token, session, user };
}

export function findMembership(workspace, userId) {
  return (workspace.members || []).find((member) => member.user_id === userId) || null;
}

export async function requireWorkspaceAccess(request, env, options = {}) {
  const auth = await requireUserSession(request, env);
  const requestedWorkspaceId = request.headers.get("X-Workspace-ID") || "";
  const workspaceId = requestedWorkspaceId || auth.user.last_active_workspace_id || auth.user.default_workspace_id;
  if (!workspaceId) {
    throw new HttpError(400, "Active workspace is required.");
  }
  const workspace = await loadWorkspace(env, workspaceId);
  if (!workspace) {
    throw new HttpError(404, "Workspace not found.");
  }
  const membership = findMembership(workspace, auth.user.id);
  if (!membership) {
    throw new HttpError(403, "Workspace access denied.");
  }
  if (options.admin && membership.role !== "admin") {
    throw new HttpError(403, "Admin access required.");
  }
  return { ...auth, workspace, membership };
}

export function ensureUserWorkspaceMembership(user, workspaceId, role, joinedAt = isoNow()) {
  const existing = (user.workspace_memberships || []).find((membership) => membership.workspace_id === workspaceId);
  if (existing) {
    existing.role = existing.role || role;
    return existing;
  }
  const membership = { workspace_id: workspaceId, role, joined_at: joinedAt };
  user.workspace_memberships = [...(user.workspace_memberships || []), membership];
  return membership;
}

export function ensureWorkspaceMember(workspace, userId, username, role, joinedAt = isoNow()) {
  const existing = (workspace.members || []).find((member) => member.user_id === userId);
  if (existing) {
    existing.role = existing.role || role;
    return existing;
  }
  const member = { user_id: userId, username, role, joined_at: joinedAt };
  workspace.members = [...(workspace.members || []), member];
  return member;
}

function resolveFileNameKey(file) {
  if (file.logical_name_key) {
    return file.logical_name_key;
  }
  if (file.name_key) {
    return file.name_key;
  }
  return normalizeLogicalName(file.logical_name || file.name || "").toLowerCase();
}

export async function saveFileRecord(env, file) {
  await kvSet(env, `${KEY_PREFIX.FILE}${file.workspace_id}:${file.id}`, file);
  await kvSet(env, `${KEY_PREFIX.FILE_NAME_INDEX}${file.workspace_id}:${resolveFileNameKey(file)}`, { file_id: file.id });
}

export async function loadFileRecord(env, workspaceId, fileId) {
  return kvGet(env, `${KEY_PREFIX.FILE}${workspaceId}:${fileId}`);
}

export async function getFileByName(env, workspaceId, filename) {
  const nameKey = normalizeLogicalName(filename).toLowerCase();
  const ref = await kvGet(env, `${KEY_PREFIX.FILE_NAME_INDEX}${workspaceId}:${nameKey}`);
  if (!ref?.file_id) {
    return null;
  }
  return loadFileRecord(env, workspaceId, ref.file_id);
}

export async function listFilesByWorkspace(env, workspaceId) {
  return listJsonByPrefix(env, `${KEY_PREFIX.FILE}${workspaceId}:`);
}

export async function deleteFileRecord(env, file) {
  await kvDelete(env, `${KEY_PREFIX.FILE}${file.workspace_id}:${file.id}`);
  await kvDelete(env, `${KEY_PREFIX.FILE_NAME_INDEX}${file.workspace_id}:${resolveFileNameKey(file)}`);
}

async function saveGrant(env, prefix, token, payload, ttlSeconds = 10 * 60) {
  const tokenHash = await sha256(token);
  await kvSet(env, `${prefix}:${tokenHash}`, payload, { expirationTtl: ttlSeconds });
}

async function loadGrant(env, prefix, token) {
  const tokenHash = await sha256(token);
  return kvGet(env, `${prefix}:${tokenHash}`);
}

async function deleteGrant(env, prefix, token) {
  const tokenHash = await sha256(token);
  await kvDelete(env, `${prefix}:${tokenHash}`);
}

export function saveUploadGrant(env, token, payload, ttlSeconds) {
  return saveGrant(env, KEY_PREFIX.UPLOAD_GRANT.slice(0, -1), token, payload, ttlSeconds);
}

export function loadUploadGrant(env, token) {
  return loadGrant(env, KEY_PREFIX.UPLOAD_GRANT.slice(0, -1), token);
}

export function deleteUploadGrant(env, token) {
  return deleteGrant(env, KEY_PREFIX.UPLOAD_GRANT.slice(0, -1), token);
}

export function saveDownloadGrant(env, token, payload, ttlSeconds) {
  return saveGrant(env, KEY_PREFIX.DOWNLOAD_GRANT.slice(0, -1), token, payload, ttlSeconds);
}

export function loadDownloadGrant(env, token) {
  return loadGrant(env, KEY_PREFIX.DOWNLOAD_GRANT.slice(0, -1), token);
}

export function deleteDownloadGrant(env, token) {
  return deleteGrant(env, KEY_PREFIX.DOWNLOAD_GRANT.slice(0, -1), token);
}

export async function saveInvite(env, invite) {
  await kvSet(env, `${KEY_PREFIX.INVITE}${invite.code}`, invite, { expirationTtl: 7 * 24 * 3600 });
}

export function loadInvite(env, code) {
  return kvGet(env, `${KEY_PREFIX.INVITE}${code}`);
}

export async function listInvitesByWorkspace(env, workspaceId) {
  const invites = await listJsonByPrefix(env, KEY_PREFIX.INVITE);
  return invites.filter((invite) => invite.workspace_id === workspaceId);
}

export async function saveTaskRecord(env, task) {
  await kvSet(env, `${KEY_PREFIX.TASK}${task.workspace_id}:${task.id}`, task);
}

export function loadTaskRecord(env, workspaceId, taskId) {
  return kvGet(env, `${KEY_PREFIX.TASK}${workspaceId}:${taskId}`);
}

export async function listTasksByWorkspace(env, workspaceId) {
  return listJsonByPrefix(env, `${KEY_PREFIX.TASK}${workspaceId}:`);
}

export async function deleteTaskRecord(env, workspaceId, taskId) {
  await kvDelete(env, `${KEY_PREFIX.TASK}${workspaceId}:${taskId}`);
}

// ---- AES-GCM provider secret encryption helpers ----
const ALGORITHM = "AES-GCM";
const KEY_LENGTH = 256;
const NONCE_LENGTH = 12;
const CURRENT_ENC_VERSION = 1;

async function deriveKey(rawSecret) {
  const encoder = new TextEncoder();
  const keyMaterial = await globalThis.crypto.subtle.importKey(
    "raw", encoder.encode(rawSecret), "HKDF", false, ["deriveKey"],
  );
  return globalThis.crypto.subtle.deriveKey(
    { name: "HKDF", hash: "SHA-256", salt: encoder.encode("cheri-provider-secret-v1"), info: new Uint8Array(0) },
    keyMaterial,
    { name: ALGORITHM, length: KEY_LENGTH },
    false,
    ["encrypt", "decrypt"],
  );
}

function b64Encode(bytes) {
  return globalThis.btoa(String.fromCharCode(...bytes));
}

function b64Decode(base64) {
  const binary = globalThis.atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function encryptSecret(plaintext, rawSecret) {
  if (!rawSecret) return plaintext;
  const key = await deriveKey(rawSecret);
  const nonce = globalThis.crypto.getRandomValues(new Uint8Array(NONCE_LENGTH));
  const ciphertext = await globalThis.crypto.subtle.encrypt(
    { name: ALGORITHM, iv: nonce },
    key,
    new TextEncoder().encode(plaintext),
  );
  return JSON.stringify({ v: CURRENT_ENC_VERSION, nonce: b64Encode(nonce), ct: b64Encode(new Uint8Array(ciphertext)) });
}

async function decryptSecret(encryptedPayload, rawSecret) {
  if (!rawSecret) return encryptedPayload;
  const payload = JSON.parse(encryptedPayload);
  if (payload.v !== CURRENT_ENC_VERSION) throw new Error(`Unsupported secret payload version: ${payload.v}`);
  const key = await deriveKey(rawSecret);
  const decrypted = await globalThis.crypto.subtle.decrypt(
    { name: ALGORITHM, iv: b64Decode(payload.nonce) },
    key,
    b64Decode(payload.ct),
  );
  return new TextDecoder().decode(decrypted);
}

function isEncryptedSecretRecord(record) {
  return record && typeof record === "object" && record.v === CURRENT_ENC_VERSION;
}

export async function saveProviderSecrets(env, workspaceId, providerKind, payload) {
  const key = `${KEY_PREFIX.PROVIDER_SECRET}${workspaceId}:${providerKind}`;
  const rawSecret = env?.CHERI_PROVIDER_SECRET_KEY;
  const secretSettings = payload?.secret_settings || {};
  const encryptedSecrets = {};
  for (const [k, v] of Object.entries(secretSettings)) {
    if (typeof v === 'string' && v) {
      encryptedSecrets[k] = rawSecret ? await encryptSecret(v, rawSecret) : v;
    } else {
      encryptedSecrets[k] = v;
    }
  }
  const record = {
    workspace_id: workspaceId,
    provider_kind: providerKind,
    updated_at: isoNow(),
    secret_settings: encryptedSecrets,
    _encrypted: !!rawSecret,
  };
  await kvSet(env, key, record);
}

export async function loadProviderSecrets(env, workspaceId, providerKind) {
  const rawSecret = env?.CHERI_PROVIDER_SECRET_KEY;
  const record = await kvGet(env, `${KEY_PREFIX.PROVIDER_SECRET}${workspaceId}:${providerKind}`);
  if (!record) return null;
  if (!isEncryptedSecretRecord(record) && !record._encrypted && record.secret_settings) {
    const migrated = {};
    for (const [k, v] of Object.entries(record.secret_settings)) {
      if (typeof v === 'string' && v && rawSecret) {
        migrated[k] = await encryptSecret(v, rawSecret);
      } else {
        migrated[k] = v;
      }
    }
    const key = `${KEY_PREFIX.PROVIDER_SECRET}${workspaceId}:${providerKind}`;
    const newRecord = { ...record, secret_settings: migrated, _encrypted: !!rawSecret };
    await kvSet(env, key, newRecord);
    return { secret_settings: migrated };
  }
  if (record._encrypted && rawSecret && record.secret_settings) {
    const decrypted = {};
    for (const [k, v] of Object.entries(record.secret_settings)) {
      if (typeof v === 'string' && v) {
        try {
          const parsed = JSON.parse(v);
          if (parsed.v === CURRENT_ENC_VERSION) {
            decrypted[k] = await decryptSecret(v, rawSecret);
          } else {
            decrypted[k] = v;
          }
        } catch {
          decrypted[k] = v;
        }
      } else {
        decrypted[k] = v;
      }
    }
    return { secret_settings: decrypted };
  }
  return record;
}

export async function deleteProviderSecrets(env, workspaceId, providerKind) {
  await kvDelete(env, `${KEY_PREFIX.PROVIDER_SECRET}${workspaceId}:${providerKind}`);
}
