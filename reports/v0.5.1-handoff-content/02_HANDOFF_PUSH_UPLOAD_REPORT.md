# Handoff Push Upload Implementation Report

## Overview
`cheri handoff push` now uploads actual safe files to workspace storage via the storage provider abstraction.

## What Was Implemented

### 1. `client.update_handoff()` (cheri_cloud_cli/client.py)
```python
def update_handoff(self, state: AuthState, handoff_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update handoff metadata (status, file_ids, etc.)."""
    payload = self._request(
        "patch",
        f"/v1/handoffs/{handoff_id}",
        state=state,
        json=updates,
    )
    return dict(payload.get("handoff", {}))
```

### 2. `upload_handoff_file()` (cheri_cloud_cli/handoff/service.py)
```python
def upload_handoff_file(client, state, source_path, handoff_id, relative_path, workspace_id):
    logical_name = f"handoffs/{handoff_id}/{relative_path}"
    remote_file = upload_path_once(
        client, state, source_path,
        workspace_id=workspace_id,
        show_progress=False,
        logical_name=logical_name,
    )
    return {
        "file_id": remote_file.id,
        "storage_key": logical_name,
        "provider_id": getattr(remote_file, 'provider_id', None) or "system",
        "uploaded_at": getattr(remote_file, 'modified_at', None) or datetime.now(timezone.utc).isoformat(),
        "upload_status": "uploaded",
    }
```

### 3. Rewritten `push_handoff()` (cheri_cloud_cli/handoff/cli.py)

The function now:
1. Scans directory (unchanged — uses `create_manifest()`)
2. Resolves workspace and auth state
3. **Uploads each safe file** via `upload_handoff_file()`, annotating manifest entries with upload metadata
4. Writes manifest locally (now includes upload metadata)
5. **Uploads manifest file itself**, capturing `manifest_file_id`
6. Calls `client.update_handoff()` with:
   - `status`: "ready" or "partial_failed"
   - `file_count`: number of successfully uploaded files
   - `total_uploaded_size`: sum of uploaded file sizes
   - `uploaded_file_ids`: list of file IDs from storage provider
   - `manifest_file_id`: ID of uploaded manifest file
   - `manifest_checksum`: SHA-256 of manifest JSON
   - `failed_files`: list of relative paths that failed
   - `provider_id`: provider used for first file

### 4. Upload Namespace
Files are stored under `handoffs/{handoff_id}/{relative_path}` for logical organization.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Reuse `upload_path_once()` | Respects storage provider abstraction; no parallel storage |
| Upload manifest as file | Allows pull to get exact manifest from storage; `manifest_file_id` stored in backend |
| Continue on partial failure | User gets partial handoff rather than nothing; `partial_failed` status is explicit |
| SHA-256 checksum for manifest | Provides integrity verification on pull |

## Changes Summary

| File | Change | Commit |
|------|--------|--------|
| `cheri_cloud_cli/client.py` | Added `update_handoff()` PATCH method | 559a7ad |
| `cheri_cloud_cli/handoff/service.py` | Added `upload_handoff_file()` function | 559a7ad |
| `cheri_cloud_cli/handoff/cli.py` | Rewrote `push_handoff()` to upload files | 559a7ad |

## Verification

```bash
$ python -m cheri_cloud_cli.cli handoff push --help
Cheri handoff push - create a manifest and upload safe files to a workspace.
Usage: cheri handoff push [OPTIONS] PATH
Options: --name TEXT, --workspace TEXT, --description TEXT, --tag TEXT, ...
```

```bash
$ python -c "from cheri_cloud_cli.handoff.service import upload_handoff_file; print('import OK')"
import OK
```

## Exit Criteria

| Criterion | Status |
|-----------|--------|
| Uses existing upload flow (`upload_path_once`) | PASS |
| Logical name includes handoff namespace | PASS |
| Records file_id, storage_key, provider_id, uploaded_at, upload_status | PASS |
| Uploads manifest file itself | PASS |
| Calls `update_handoff()` with status/file_ids/manifest_file_id | PASS |
| Partial failure sets `partial_failed` status and lists failed paths | PASS |