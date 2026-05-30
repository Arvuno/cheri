# Provider Matrix

> Date: 2026-05-30
> Status: v0.2.0-storage-core

## Provider Status Summary

| Provider | Status | Selectable | Transfer | Notes |
|---|---|---|---|---|
| `System (recommended)` | Ready | Yes | Working | Uses Cloudflare R2 via HERMES_BUCKET. Temporary — files reset daily. |
| `S3-compatible` | Beta (MinIO verified) | Behind flag | Beta | Full S3 CRUD + presigned URLs. MinIO e2e: 8/8 PASS. Requires CHERI_EXPERIMENTAL_PROVIDERS=1. |
| `Local Dev` | Experimental | No | Test-only | In-memory Map, not persisted. Worker tests only. |
| `Google Drive` | Not Ready | No | Not active | Scaffolded. Coming soon. |
| `Backblaze B2` | Not Ready | No | Not active | Scaffolded. S3-compatible API possible. |

---

## Provider Capabilities

| Capability | System | S3-compatible | Local Dev |
|---|---|---|---|
| Upload (putObject) | ✅ | ✅ | ✅ |
| Download (getObject) | ✅ | ✅ | ✅ |
| Delete (deleteObject) | ✅ | ✅ | ✅ |
| List (listObjects) | ✅ | ✅ | ✅ |
| Head (headObject) | ✅ | ✅ | ✅ |
| Copy (copyObject) | ✅ | ✅ | ❌ |
| Signed upload URL | ❌ | ✅ | ❌ |
| Signed download URL | ❌ | ✅ | ❌ |
| Multipart upload | ❌ | ✅ | ❌ |
| Checksum verification | ❌ | ✅ | ❌ |

---

## Selection Constraints

- **System** — selectable by default, no flag required. Requires warning acknowledgment.
- **S3-compatible** — requires `CHERI_EXPERIMENTAL_PROVIDERS=1` AND `experimental_acknowledged: true` in selection payload.
- **Local Dev** — not selectable via CLI, test-only.
- **Google Drive, Backblaze B2** — coming soon, not selectable yet.

---

## Credentials

Provider credentials are never stored in:
- Bootstrap secret
- Session token
- Invite code

They live in workspace storage configuration under `workspace.storage.provider.settings` for non-secrets, and in KV under `provider-secret:{workspace_id}:{provider_kind}` for secrets.

---

## System Provider

- **Binding:** `HERMES_BUCKET` (R2)
- **Validation:** checks `env.HERMES_BUCKET` exists and is accessible
- **Temporary:** Files are reset daily via `cleanupExpiredSystemFiles` scheduled handler
- **Object key format:** `{workspaceId}/{fileId}/v{version}/{safeLogicalName}`

---

## S3-Compatible Provider

- **Status:** experimental
- **Validation:** Checks endpoint, bucket, and credentials by performing a list operation
- **Capabilities:** Full S3 CRUD + presigned URLs + multipart
- **Requires:** `endpoint`, `bucket`, `region`, `access_key_id`, `secret_access_key`
- **MinIO support:** Set `force_path_style: true` for MinIO endpoint compatibility

---

## Local Dev Provider

- **Status:** test-only (experimental)
- **Storage:** In-memory Map — blobs lost on worker restart
- **Not selectable** via CLI in any deployment mode
- **Use cases:** Worker unit tests, local integration tests without Cloudflare credentials