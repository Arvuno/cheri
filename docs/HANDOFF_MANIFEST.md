# Handoff Manifest Schema

This document describes the `cheri-handoff.json` manifest format used by Cheri's agent artifact handoff feature.

## Schema Version

Current schema version: `1.1`

v1.0 manifests (without `file_id`, `storage_key`, `provider_id`, `uploaded_at`, and `upload_status` fields on FileEntry) are still supported and load correctly. Missing fields default to null/empty.

## Overview

The manifest is a JSON file that describes a handoff bundle — the metadata, included files, and any skipped sensitive files. The manifest itself is included in the handoff bundle and can be used to verify integrity.

## Field Reference

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Manifest format version. Current: `"1.0"` |
| `handoff_id` | string | Yes | Unique identifier for this handoff. UUID format recommended. |
| `name` | string | Yes | Human-readable name for the handoff. |
| `description` | string | No | Detailed description of what this handoff contains. |
| `tags` | array[string] | No | Tags for categorization (e.g., `["release", "v0.5.0"]`) |
| `generated_at` | string | Yes | ISO 8601 timestamp when the manifest was generated. |
| `source_path` | string | Yes | Original filesystem path that was scanned. |
| `source_context` | string | No | Either `"directory"` or `"file"`. Indicates the type of source. |
| `files` | array[FileEntry] | Yes | List of files included in the handoff. |
| `skipped_sensitive` | array[string] | No | List of file paths skipped due to secret-safe exclusions. Paths are relative to source_path. |
| `notes` | string | No | Free-form notes from the handoff creator. |
| `agent_name` | string | No | Name of the agent that generated the artifacts (e.g., `"claude-code"`, `"codex"`). |
| `tool_name` | string | No | Name of the specific tool or process that generated the artifacts. |
| `version_label` | string | No | Version label for the artifacts (e.g., `"v0.5.0"`, `"release-candidate"`). |
| `created_by` | string | No | Username of the Cheri user who created the handoff. |

### Git Context

When the source path is inside a Git repository, the manifest includes a `git_context` object:

| Field | Type | Description |
|-------|------|-------------|
| `branch` | string | Current Git branch name. |
| `commit_hash` | string | Short form of the current HEAD commit hash (first 12 characters). |
| `dirty` | boolean | `true` if there are uncommitted changes, `false` otherwise. |
| `remote_url` | string | URL of the `origin` remote. Credentials embedded in the URL are redacted. |

### FileEntry

Each entry in the `files` array represents a file in the handoff:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `relative_path` | string | Yes | Path relative to the source_path. Use forward slashes (`/`) as separator. |
| `size` | integer | Yes | File size in bytes. |
| `checksum` | string | Yes | SHA-256 hex digest of the file content. |
| `content_type` | string | No | MIME type hint, inferred from file extension. |
| `skipped` | boolean | No | `true` if the file was skipped during scanning. Included for completeness but skipped files appear in `skipped_sensitive` instead. |
| `file_id` | string | No | Unique identifier assigned after successful upload. Present on v1.1 manifests; null on v1.0. |
| `storage_key` | string | No | Storage namespace key where the file content is stored (e.g., `handoffs/{handoff_id}/README.md`). Present on v1.1 manifests; null on v1.0. |
| `provider_id` | string | No | Identifier for the storage provider used for this file. Present on v1.1 manifests; null on v1.0. |
| `uploaded_at` | string | No | ISO 8601 timestamp when the file was uploaded to storage. Present on v1.1 manifests; null on v1.0. |
| `upload_status` | string | No | Upload result status. One of: `"success"`, `"partial_failed"`, `"failed"`. Present on v1.1 manifests; absent on v1.0. |

## Example Manifest

```json
{
  "schema_version": "1.1",
  "handoff_id": "hnd_7f3a9bc2d081",
  "name": "v0.5 implementation report",
  "description": "Implementation artifacts from the v0.5 development cycle",
  "tags": ["release", "v0.5.0", "implementation"],
  "generated_at": "2026-05-30T15:30:00Z",
  "source_path": "/home/user/projects/cheri-app/reports/v0.5",
  "source_context": "directory",
  "git_context": {
    "branch": "main",
    "commit_hash": "abc123def456",
    "dirty": false,
    "remote_url": "https://github.com/user/cheri-app.git"
  },
  "files": [
    {
      "relative_path": "README.md",
      "size": 1234,
      "checksum": "3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b",
      "content_type": "text/markdown",
      "file_id": "file_a1b2c3d4e5f6",
      "storage_key": "handoffs/hnd_7f3a9bc2d081/README.md",
      "provider_id": "provider_workspace_01",
      "uploaded_at": "2026-05-30T15:30:05Z",
      "upload_status": "success"
    },
    {
      "relative_path": "impl/report.json",
      "size": 45678,
      "checksum": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
      "content_type": "application/json",
      "file_id": "file_b2c3d4e5f6a7",
      "storage_key": "handoffs/hnd_7f3a9bc2d081/impl/report.json",
      "provider_id": "provider_workspace_01",
      "uploaded_at": "2026-05-30T15:30:06Z",
      "upload_status": "success"
    }
  ],
  "skipped_sensitive": [
    ".env",
    "credentials.json"
  ],
  "notes": "Generated after successful v0.5 implementation pass.",
  "agent_name": "claude-code",
  "tool_name": "implementation",
  "version_label": "v0.5.0",
  "created_by": "alice"
}
```

## Integrity Verification

To verify the integrity of a handoff bundle:

1. Load `cheri-handoff.json`
2. For each file in `files`, recalculate SHA-256 and compare to the stored `checksum`
3. Verify `schema_version` is supported
4. Check that all expected files are present in the bundle

## Secret-Safe Exclusions

The `skipped_sensitive` array lists files that were excluded based on name patterns. The file contents are never read or included. Patterns include:

- `.env`, `.env.*`, `*.env`
- `credentials.json`, `secrets.json`, `secret.json`
- `*.key`, `*.pem`
- `id_rsa`, `id_ed25519`
- `.npmrc`, `.pypirc`, `.netrc`
- `.git` directory contents

The `include_sensitive` flag can override this behavior with explicit user confirmation.

## Notes on Metadata Safety

- Manifests are stored in the workspace and visible to all workspace members.
- **Never include actual secret values** in the manifest fields (description, notes, tags, etc.).
- The `skipped_sensitive` list contains only file names, not file contents.
- Git context remote URLs have embedded credentials redacted before storage.