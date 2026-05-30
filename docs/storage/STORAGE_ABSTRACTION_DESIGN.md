# Storage Abstraction Design

> Date: 2026-05-30
> Status: Architecture — v0.2.0-storage-core

---

## Overview

Cheri's storage layer is partitioned into five distinct concerns:

1. **MetadataStore** — KV-backed persistence for file records, grants, workspace config
2. **BlobStorageProvider** — interface for storing/retrieving raw file bytes
3. **ProviderRegistry** — catalog of available providers, their capabilities, and runtime status
4. **ProviderConfigStore** — per-workspace storage provider configuration with secret management
5. **StorageTransferService** — orchestrates upload/download grants and provider calls

The existing `worker/services/provider_config.js` and `worker/providers/` directory already provide a partial implementation of items 2–5. This design formalizes the contract and fills gaps.

---

## A. Layer Architecture

### MetadataStore (`worker/lib/storage.js`)

No changes required to existing KV operations. File records, grants, and workspace metadata continue to use the same key families.

```
user:{id}
workspace:{id}
session:{hash}
file:{workspace_id}:{file_id}
file-name:{workspace_id}:{name_key}
upload-grant:{hash}
download-grant:{hash}
provider-secret:{workspace_id}:{provider_kind}
task:{workspace_id}:{task_id}
activity:{workspace_id}
invite:{code}
```

### BlobStorageProvider

Every provider implements the `BlobStorageProvider` contract (see `PROVIDER_CONTRACT.md`). Instances are created by `StorageTransferService` based on workspace provider configuration.

### ProviderRegistry

The registry maps provider `kind` → provider class and definition. It also computes per-provider status: `ready`, `experimental`, `not_ready`, `deprecated`.

Existing: `worker/services/provider_config.js` — `PROVIDER_DEFINITIONS`, `PROVIDER_CLASSES`, `providerCatalog()`, `getProviderDefinition()`

### ProviderConfigStore

Per-workspace storage configuration. Workspace objects carry `storage.provider` which contains `kind`, `settings`, `secret_fields`, etc.

Existing: `worker/services/provider_config.js` — `resolveWorkspaceProviderConfig()`, `prepareProviderForWorkspace()`, `createWorkspaceStorageState()`, `getWorkspaceProviderConfig()`

### StorageTransferService

Orchestrates the full upload/download lifecycle. Replaces direct calls to provider methods from `file_service.js`.

New module: `worker/storage/transfer_service.js`

---

## B. Storage Object Identity

### Canonical Object Key Format

```
workspaces/{workspace_id}/files/{file_id}/v{version}/{safe_filename}
```

Where:
- `workspace_id` — stable workspace identifier (e.g., `wksp_abc123`)
- `file_id` — stable file identifier (e.g., `file_xyz789`)
- `version` — positive integer, starts at 1
- `safe_filename` — sanitized logical name via `safeLogicalName()` from `security/tokens.js`

Example:
```
workspaces/wksp_abc123/files/file_xyz789/v1/notes.md
workspaces/wksp_abc123/files/file_xyz789/v2/notes.md
```

### Key Properties

- **Workspace-scoped:** Each key is scoped to a single workspace. Cross-workspace access is impossible by construction.
- **Versioned:** Each upload creates a new version with a new key. Old versions are retained in the file's `history` array.
- **Traversal-safe:** `safeLogicalName` strips path components and normalizes the filename. No user-supplied path segments appear in the key.
- **Deterministic:** Same logical name in same workspace at same version always produces the same key.

### Object Key Validation

The system never trusts user-supplied filenames for key construction. `safeLogicalName` is applied before any key construction. Keys are validated to match the pattern `^workspaces/[^/]+/files/[^/]+/v[0-9]+/[^/]+$` before any provider operation.

---

## C. Metadata Shape

File records stored in KV under `file:{workspace_id}:{file_id}`:

```typescript
interface FileRecord {
  // Identity
  id: string;                    // "file_{ulid}"
  workspace_id: string;         // "wksp_{ulid}"

  // Naming
  logical_name: string;         // Original filename, e.g. "notes.md"
  logical_name_key: string;     // Lowercase normalized for lookups

  // Storage
  provider_id: string;          // Provider kind, e.g. "system", "s3-compatible"
  provider_object_key: string;   // Full object key in provider
  provider_object_id: string;    // Provider-specific object identifier

  // Content
  size: number;                  // Bytes, 0 to 1_073_741_824
  content_type: string;          // MIME type
  checksum: string;              // SHA-256 if provided by client

  // Timestamps
  created_at: string;           // ISO 8601
  uploaded_at: string;           // ISO 8601, set when blob confirmed stored
  updated_at: string;           // ISO 8601

  // Authorship
  created_by: string;           // Username
  uploaded_by: string;          // Username (same as created_by for v1)
  last_modified_by: string;     // Username

  // Versioning
  version: number;              // Starts at 1, increments on re-upload
  revision_marker: string;       // Human-readable, e.g. "v2"
  remote_revision: string;      // Provider-specific ETag or version marker

  // Sync
  sync_status: SyncStatus;       // "upload_pending" | "uploaded" | "synced"
  local_modified_at: string;     // Client-side mtime if provided

  // Conflict
  conflict_state: ConflictState; // "clear" | "conflict" | "resolved"
  conflict_details?: object;

  // Status
  status: FileStatus;            // "upload_pending" | "uploaded" | "available" | "deleted"
  deleted_at?: string;

  // History
  history: FileHistoryEntry[];   // Previous versions
}

type SyncStatus = "upload_pending" | "uploaded" | "synced";
type FileStatus = "upload_pending" | "uploaded" | "available" | "deleted";
type ConflictState = "clear" | "conflict" | "resolved";

interface FileHistoryEntry {
  version: number;
  revision_marker: string;
  provider_object_key: string;
  provider_object_id: string;
  checksum: string;
  size: number;
  updated_at: string;
  last_modified_by: string;
  sync_status: SyncStatus;
}
```

### Field Preservation

All existing fields (from v0.1.x) are preserved. New fields (`provider_id`, `provider_object_key`, `provider_object_id`) are populated from the provider config at file creation time.

---

## D. Workspace Storage Config

Stored in `workspace.storage.provider`:

```typescript
interface WorkspaceStorageConfig {
  provider: ProviderConfig;
  registry?: {
    normalized_file_registry: boolean;
    conflict_detection_ready: boolean;
    version_comparison_ready: boolean;
    remote_revision_lookup_ready: boolean;
    incremental_sync_ready: boolean;
    provider_change_tracking_ready: boolean;
  };
  updated_at: string;
}

interface ProviderConfig {
  kind: string;                 // "system" | "s3-compatible" | ...
  label: string;
  temporary: boolean;
  recommended: boolean;
  selectable: boolean;
  coming_soon: boolean;
  experimental: boolean;
  warning_acknowledged: boolean;
  reset_policy: string;
  settings: Record<string, string>;  // Non-secret settings only
  secret_fields: string[];          // Keys of secret fields
  secret_ref: string;               // KV key for secrets if any
  metadata?: object;                // Provider catalog metadata
  validation?: {
    state: ProviderValidationState;
    available: boolean;
    checked_at: string;
    warnings: string[];
    errors: string[];
  };
}

type ProviderValidationState = "pending" | "configured" | "ready" | "misconfigured" | "validated-config";
```

---

## E. Security

### Secret Handling

- Provider secrets (S3 access keys, etc.) are stored in KV under `provider-secret:{workspace_id}:{provider_kind}`
- Secrets are never returned by API responses — `redactProvider()` replaces secret field values with `"***"`
- Secrets are merged into `providerConfig.settings` at runtime via `resolveWorkspaceProviderConfig()`
- No secrets appear in logs, activity feed, or error messages

### Signed URLs

- Upload/download grants use short-lived tokens (10 minutes TTL)
- Grant tokens are hashed before KV storage (`sha256`)
- Provider `generateUploadTarget`/`generateDownloadTarget` can return signed URLs if the provider supports it (future)
- `worker_proxy` mode remains the default for System/R2

### Input Validation

- `safeLogicalName` applied to all filenames before key construction
- Object keys validated against pattern before provider operations
- File size enforced: 0 to 1 GB per upload grant

---

## F. Migration Design

### Storage Migration CLI

```bash
cheri storage migrate plan --to <provider-id>
cheri storage migrate dry-run --to <provider-id>
```

### Migration Plan Output

```
Source provider:    system (Cloudflare R2)
Target provider:    s3-compatible
Files to migrate:  47
Total size:         1.2 GB
Operations needed:
  - Upload 47 objects to target provider
  - Verify 47 checksums
  - Switch workspace default provider
  - Keep rollback: original provider remains usable

Unsupported features:
  - Incremental sync not available on target
  - Direct download URLs not available

Estimated time:     ~5 minutes (depends on bandwidth)
Rollback:           Run with --rollback flag
```

### Migration Steps

1. **Dry-run:** List all files, compute total size, verify target provider reachable
2. **Prepare:** Store rollback info in workspace metadata
3. **Copy:** For each file, copy blob to target provider using `copyObject` if supported, or re-upload
4. **Verify:** Compare size and checksum between source and target
5. **Switch:** Update workspace storage config to point to new provider
6. **Rollback plan:** Store original provider config in a separate KV key

---

## G. Provider Lifecycle

1. **Definition** — Provider is defined in `PROVIDER_DEFINITIONS` with `kind`, `label`, `fields`, capabilities, and lifecycle flags
2. **Registration** — Provider class is added to `PROVIDER_CLASSES` mapping
3. **Catalog exposure** — `GET /v1/providers` returns public-facing provider info
4. **Validation** — `provider.validateConfig()` checks env bindings and credentials
5. **Instantiation** — `instantiateStorageProvider(env, providerConfig)` creates provider instance
6. **Runtime** — Provider methods called by `StorageTransferService` during file operations
7. **Deprecation** — Provider marked `deprecated: true` in definitions; system warns users but keeps working