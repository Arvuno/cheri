# Secret-Safe Task Scanning Report

## What Changed

Updated `DEFAULT_EXCLUDE_PATTERNS` in `cheri_cloud_cli/task/runtime.py` to include 13 secret-safe patterns. Added `skipped_sensitive` tracking in `TaskScanResult` and warning output in task run dry-run/noop results.

## Exclude Patterns Added

```python
".env",
".env.*",
"*.env",
".env/**",
"credentials.json",
"*.key",
"*.pem",
"id_rsa",
"id_rsa*",
"id_ed25519",
"id_ed25519*",
".npmrc",
".pypirc",
".netrc",
"secrets.json",
"secret.json",
```

## Implementation

**Path filtering** (`_path_allowed()`):
- Normalizes Windows backslashes to forward slashes
- Checks include patterns first (if any) — file must match to be allowed
- Checks exclude patterns (defaults + task-specific) — file must not match any
- Default exclusions apply to all tasks, task-specific exclusions extend them

**Skipped sensitive tracking** (`scan_task()`):
- `_collect_all_files()` collects ALL files in the target directory (including excluded)
- `_path_allowed()` filters to allowed paths vs. skipped paths
- `TaskScanResult` now has `skipped_sensitive: List[str]` field
- `TaskExecutionResult` propagates `skipped_sensitive` from `scan_task()` result

**Warning output** (`run_task()` in `task/service.py`):
- When task run results in `noop` status AND `skipped_sensitive` is non-empty, prints:
  > Note: N file(s) skipped due to potentially sensitive names (e.g. .env, credentials.json).

## Files Changed

- `cheri_cloud_cli/task/runtime.py` — 13 secret-safe patterns added, skipped_sensitive tracking
- `cheri_cloud_cli/task/models.py` — TaskScanResult.skipped_sensitive field added
- `cheri_cloud_cli/services/task_service.py` — TaskExecutionResult.skipped_sensitive field
- `cheri_cloud_cli/task/service.py` — warning output for noop+skipped
- `tests/python/test_task_runtime.py` — 19 new tests for path filtering and scanning

## Tests Added

| Test | Scenario |
|------|----------|
| `test_allows_normal_files` | readme.md, src/app.js |
| `test_excludes_git_metadata_files` | .git/config allowed, .gitignore allowed |
| `test_excludes_cheri_directory` | .cheri/tasks.json excluded |
| `test_excludes_temporary_files` | .swp, .tmp, .part, .crdownload |
| `test_excludes_os_metadata` | .DS_Store, Thumbs.db |
| `test_excludes_env_files` | .env, .env.local, .env.production, .env/** |
| `test_excludes_credentials_and_keys` | credentials.json, *.key, *.pem |
| `test_excludes_ssh_keys` | id_rsa, id_rsa.pub, id_ed25519 |
| `test_excludes_config_files` | .npmrc, .pypirc, .netrc |
| `test_excludes_secret_json` | secrets.json, secret.json (not *secrets.json) |
| `test_include_patterns_take_priority` | include *.md allows markdown |
| `test_exclude_patterns_can_extend_defaults` | task-specific .log, .bak |
| `test_windows_path_separators_normalized` | src\app.js normalized to src/app.js |
| `test_snapshot_includes_all_allowed_files` | build_snapshot returns only allowed |
| `test_snapshot_excludes_sensitive_files` | .env, credentials.json, api.key |
| `test_snapshot_records_mtime_and_size` | snapshot entries have mtime_ns and size |
| `test_scan_detects_new_file` | changed_paths includes new file |
| `test_scan_detects_modified_file_mtime` | mtime change detected |
| `test_scan_detects_deleted_file` | deleted_paths includes removed file |
| `test_scan_detects_no_changes` | empty changed_paths on stable |
| `test_scan_excludes_sensitive_files_from_results` | .env excluded from results |

## Test Results

```
python -m unittest tests.python.test_task_runtime -v
----------------------------------------------------------------------
Ran 19 tests in 0.012s
OK
```

## Limitations

- Pattern matching is glob-based (fnmatch), not regex — sufficient for common cases
- Excludes are by filename pattern only — content scanning not implemented
- `*secrets.json` not added (would exclude too broadly like `my_app_secrets.json`)
- Windows path normalization works for display but the actual path is always Posix from `Path.relative_to().as_posix()`