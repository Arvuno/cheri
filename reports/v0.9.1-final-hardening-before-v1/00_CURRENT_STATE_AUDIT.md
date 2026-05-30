# v0.9.1-final-hardening-before-v1 — Current State Audit

**Date:** 2026-05-30
**Branch:** `v0.9-s3-e2e-and-type-cleanup`
**Commit:** `f16e481`

---

## Version State

| Source | Version | Notes |
|--------|---------|-------|
| `cheri_cloud_cli.__version__` | `0.8.0b1` | Package version |
| `setup.py --version` | `0.8.0b1` | Build version |
| `CHANGELOG.md` latest | `0.9.0-s3-e2e-and-type-cleanup` | Unreleased |

**Note:** Version in `__init__.py` is `0.8.0b1` but CHANGELOG refers to `0.9.0-s3-e2e-and-type-cleanup`. Needs version bump to `0.9.1-final-hardening-before-v1`.

---

## Test Results

| Test Suite | Command | Result | Details |
|------------|---------|--------|---------|
| Python unit tests | `python -m unittest discover -s tests/python -p "test_*.py"` | ✅ PASS | 149/149 tests passed |
| Worker Node tests | `node tests/node/worker.test.mjs` | ✅ PASS | 8/8 ok |
| Storage Node tests | `node tests/node/storage.test.mjs` | ✅ PASS | 14/14 ok |
| npm test | `npm test` | ✅ PASS | Worker + Python tests pass |
| ruff | `ruff check .` | ✅ PASS | All checks passed |

---

## Mypy Type Check

| Metric | Value |
|--------|-------|
| Initial error count | 26 |
| Target |< 10 |
| Status | ❌ NOT MET |

**Files with errors:**
- `cheri_cloud_cli/contracts.py` — 2 errors (SessionContext, ProviderObjectRef Any types)
- `cheri_cloud_cli/task/scheduler.py` — 1 error (suffix annotation missing)
- `cheri_cloud_cli/retry.py` — 1 error (with_retry kwargs type)
- `cheri_cloud_cli/providers/catalog.py` — 1 error (object not iterable)
- `cheri_cloud_cli/storage.py` — 3 errors (WorkspaceSummary.get, AuthState assignment)
- `cheri_cloud_cli/workspace/service.py` — 3 errors (recent_items type narrowing)
- `cheri_cloud_cli/services/watch_service.py` — 4 errors (Popen overload, TaskRuntimeState assignment)
- `cheri_cloud_cli/handoff/cli.py` — 5 errors (Rich Console.input default kwarg)
- `cheri_cloud_cli/init.py` — 2 errors (None attribute access)
- `cheri_cloud_cli/doctor.py` — 2 errors (generator type, TaskDefinition.get)
- `cheri_cloud_cli/cli.py` — 2 errors (isinstance arg, Command.get_command)

---

## Provider Capability Status

| Provider | Status | upload | download | delete | list | signedUploadUrl | signedDownloadUrl | multipart | checksum |
|---------|--------|--------|----------|--------|------|----------------|-------------------|-----------|---------|
| System (R2) | ✅ Ready | true | true | true | true | false | false | false | false |
| S3-compatible | ⚠️ Beta (MinIO verified) | true | true | true | true | true | true | **true** ⚠️ | true |
| Local Dev | 🔧 Experimental | — | — | — | — | — | — | — | — |
| Backblaze B2 | 📄 Docs-only | — | — | — | — | — | — | — | — |
| Google Drive | 📄 Not Ready | — | — | — | — | — | — | — | — |

### Issues Identified

1. **S3-compatible `multipart: true`** — The `CAPABILITIES_S3_COMPATIBLE` in `types.js` declares `multipart: true`, but the S3-compatible provider class does NOT implement multipart upload. This is a false capability claim.

2. **S3-compatible `signedUploadUrl/signedDownloadUrl: true`** — These are implemented in the provider class (`createUploadTarget`/`createDownloadTarget`) but the CLI does NOT use direct-to-S3 presigned URL mode. All transfers go through worker proxy. Claiming `true` is misleading.

3. **System `checksum: false`** — The types.js declares `checksum: false` for System, but the CHANGELOG for v0.9.0 mentions "SHA256 checksum verification" in MinIO e2e. Need to verify if System actually verifies checksums.

4. **S3-compatible `serverSideCopy: true`** — Declared in `CAPABILITIES_S3_COMPATIBLE` but not implemented in the provider class.

---

## Remaining Blockers for v1.0

| Blocker | Severity | Notes |
|---------|----------|-------|
| Mypy error count (26) | HIGH | Must reduce to < 10 for CI gate |
| S3-compatible multipart false claim | HIGH | Declared but not implemented |
| S3-compatible direct presigned URL claim | MEDIUM | Internal feature, not CLI mode |
| Version mismatch | MEDIUM | `__version__` is 0.8.0b1, CHANGELOG says 0.9.0 |
| Backblaze B2 docs-only status | LOW | Correctly documented but no implementation |
| Google Drive docs-only | LOW | Correctly documented |

---

## MinIO E2E Test

| Item | Status |
|------|--------|
| MinIO e2e script exists | ✅ `scripts/dev/minio-e2e.py` |
| Shell wrapper | ✅ `scripts/dev/minio-e2e.sh` |
| Run command | `python scripts/dev/minio-e2e.py` (Python script, not bash) |

---

## Summary

- Branch is clean (only untracked `requirements-dev.txt` and `system_audit_report/`)
- All tests pass (Python149, Worker 8, Storage 14, npm test, ruff)
- Mypy has 26 errors — needs reduction before CI gate
- Provider capability matrix has false claims for S3-compatible (multipart, serverSideCopy)
- S3-compatible signed URL claims are technically true but misleading about CLI direct mode
- Version needs bump to reflect actual release intent
