# Handoff Manifest Report

## Overview

The handoff manifest (`cheri-handoff.json`) is the core artifact of the handoff system. It describes what files are included, includes metadata about the source and agent, and provides integrity verification through checksums.

## Manifest Generation Flow

```
User runs:
  cheri handoff create ./reports --name "v0.5 report"

CLI:
  1. Validates path exists
  2. Calls create_manifest(source_path="./reports", name="v0.5 report", ...)
  3. scan_directory() walks the filesystem
  4. For each file: calculate_checksum(), get_content_type()
  5. _get_git_context() captures Git state (if available)
  6. Returns manifest dict
  7. write_manifest() writes to cheri-handoff.json
  8. Display summary panel
```

## Schema

Current version: `1.0`

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Always `"1.0"` |
| `handoff_id` | string | UUID v4 (auto-generated) |
| `name` | string | Human-readable name |
| `generated_at` | string | ISO 8601 UTC timestamp |
| `source_path` | string | Absolute path of source |
| `files` | array | List of included files |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Detailed description |
| `tags` | array[string] | Categorization tags |
| `source_context` | string | `"directory"` or `"file"` |
| `git_context` | object | Git state (branch, commit, dirty, remote) |
| `skipped_sensitive` | array[string] | Excluded file paths |
| `notes` | string | Creator notes |
| `agent_name` | string | Agent type (e.g., `"claude-code"`) |
| `tool_name` | string | Tool that produced artifacts |
| `version_label` | string | Version tag for artifacts |
| `created_by` | string | Cheri username |

### FileEntry Fields

| Field | Type | Description |
|-------|------|-------------|
| `relative_path` | string | Path relative to source (forward slashes) |
| `size` | integer | File size in bytes |
| `checksum` | string | SHA-256 hex digest |
| `content_type` | string | MIME type (inferred from extension) |
| `skipped` | boolean | Only if file was skipped during scan |

## Implementation

### `create_manifest()` Function

```python
def create_manifest(
    source_path: str,
    name: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    agent_name: Optional[str] = None,
    tool_name: Optional[str] = None,
    version_label: Optional[str] = None,
    include_sensitive: bool = False,
    notes: str = "",
) -> dict:
```

Located in: `cheri_cloud_cli/handoff/service.py`

Steps:
1. Validate path exists
2. Call `scan_directory()` to get files and skipped list
3. Call `_get_git_context()` to capture Git state
4. Build and return manifest dict
5. Add `_file_count` and `_total_size` as convenience fields

### `scan_directory()` Function

Located in: `cheri_cloud_cli/handoff/__init__.py`

Uses `os.walk()` with `followlinks=False` to traverse directories:
- Skips `.git` directories
- Respects `DEFAULT_EXCLUDE_PATTERNS`
- Calculates SHA-256 for each file
- Returns `(list[HandoffFile], list[str])`

### Checksum Calculation

```python
def calculate_checksum(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
```

### Content Type Detection

Based on file extension mapping to MIME types. Returns `None` for unknown extensions.

## Git Context

```python
def _get_git_context(source_path: str) -> Optional[dict]:
    # Runs: git rev-parse --show-toplevel
    # Runs: git rev-parse --abbrev-ref HEAD
    # Runs: git rev-parse HEAD
    # Runs: git status --porcelain
    # Runs: git remote get-url origin
    # Redacts credentials from remote URL
```

Returns `None` if:
- Git not installed
- Path not inside a git repo
- Any git command times out (5 second limit)

## Example Output

```json
{
  "schema_version": "1.0",
  "handoff_id": "hnd_7f3a9bc2d081",
  "name": "v0.5 implementation report",
  "description": "Implementation artifacts from v0.5 dev cycle",
  "tags": ["release", "v0.5.0"],
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
      "checksum": "3a4b5c6d7e8f...",
      "content_type": "text/markdown"
    }
  ],
  "skipped_sensitive": [".env", "credentials.json"],
  "notes": "Generated after successful v0.5 implementation.",
  "agent_name": "claude-code",
  "tool_name": "implementation",
  "version_label": "v0.5.0",
  "created_by": "alice"
}
```

## Integrity Verification

To verify a handoff bundle:

1. Load `cheri-handoff.json`
2. For each entry in `files`:
   - Read the file at `source_path / relative_path`
   - Calculate SHA-256
   - Compare to stored `checksum`
3. Report any mismatches

## Backend Storage

The manifest JSON is stored:
- **Locally**: Written to source directory as `cheri-handoff.json`
- **Backend**: Metadata fields (not full manifest) stored in KV

Backend record (`POST /v1/handoffs`):
```json
{
  "handoff_id": "...",
  "name": "...",
  "description": "...",
  "tags": [...],
  "source_path": "...",
  "file_count": 5,
  "total_size": 1024,
  "manifest_path": "cheri-handoff.json",
  "manifest_checksum": "",
  "agent_name": "claude-code",
  "tool_name": "...",
  "version_label": "...",
  "git_branch": "main",
  "git_commit": "abc123def456",
  "notes": "..."
}
```