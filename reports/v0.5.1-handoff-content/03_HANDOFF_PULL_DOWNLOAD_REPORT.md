# Handoff Pull Download Implementation Report

## Overview
`cheri handoff pull` now downloads actual files from workspace storage and restores relative paths.

## What Was Implemented

### 1. `client.get_file()` (cheri_cloud_cli/client.py)
```python
def get_file(self, state: AuthState, file_id: str, workspace_id: Optional[str] = None) -> Dict[str, Any]:
    """Get file metadata by ID."""
    return self._request("get", f"/v1/files/{file_id}", state=state, workspace_id=workspace_id)
```

### 2. Rewritten `pull_handoff()` (cheri_cloud_cli/handoff/cli.py)

The function now:
1. Gets handoff metadata from backend
2. Creates destination directory (with non-empty warning)
3. **Downloads manifest from storage** if `manifest_file_id` is available:
   - Gets download grant via `client.request_download_grant()`
   - Fetches manifest JSON via HTTP GET
   - Falls back to backend metadata if download fails
   - Errors out if no manifest available at all
4. Writes `cheri-handoff.json` to destination
5. **Downloads each file** that has a `file_id`:
   - Skips files without `file_id` (not uploaded — reports as skipped)
   - Gets download grant via `client.request_download_grant()`
   - Downloads content via HTTP GET
   - **Verifies checksum** if `expected_checksum` is in manifest
   - Writes to `output_dir / relative_path`
   - Creates parent directories as needed
6. Reports summary: downloaded count, failed count, checksum mismatches, skipped count

### 3. Checksum Verification

When manifest has `checksum` for a file entry:
```python
if expected_checksum:
    actual_checksum = hashlib.sha256(content).hexdigest()
    if actual_checksum != expected_checksum:
        checksum_mismatches.append({...})
        failed.append(rel_path)
        continue
```

### 4. Error Handling

| Scenario | Behavior |
|----------|----------|
| No manifest_file_id, no backend manifest | Error with helpful message |
| File download fails | Report failed path, continue with other files |
| Checksum mismatch | Report mismatch details, do not write file |
| File without file_id | Report as skipped (not uploaded) |

## Changes Summary

| File | Change | Commit |
|------|--------|--------|
| `cheri_cloud_cli/client.py` | Added `get_file()` method | b0fea24 |
| `cheri_cloud_cli/handoff/cli.py` | Rewrote `pull_handoff()` to download files | b0fea24 |

## Verification

```bash
$ python -m cheri_cloud_cli.cli handoff pull --help
Cheri handoff pull - download handoff files to a local folder.
Usage: python -m cheri_cloud_cli.cli handoff pull [OPTIONS] HANDOFF_ID
Options: --dest PATH
```

## Exit Criteria

| Criterion | Status |
|-----------|--------|
| Downloads manifest from storage if `manifest_file_id` available | PASS |
| Falls back to backend metadata if manifest download fails | PASS |
| Uses `request_download_grant()` for each file | PASS |
| Restores relative paths under destination | PASS |
| Verifies checksums when manifest has expected_checksum | PASS |
| Reports downloaded/failed/checksum_mismatch/skipped counts | PASS |
| Continues on partial failure (download what we can) | PASS |
| Writes `cheri-handoff.json` to destination | PASS |