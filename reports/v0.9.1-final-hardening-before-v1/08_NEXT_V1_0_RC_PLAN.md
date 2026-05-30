# Next v1.0 RC Plan

**Date:** 2026-05-30

---

## Summary

The next step is to produce a clean v1.0 RC commit. This document outlines the remaining tasks.

---

## Remaining Tasks for v1.0 RC

### 1. Version Bump (Required)

**File:** `cheri_cloud_cli/__init__.py`

**Current:** `__version__ = "0.8.0b1"`

**Required:** Update to match CHANGELOG intent. Options:
- `0.9.1` — if continuing the minor version sequence
- `1.0.0-rc1` — if entering RC phase

Also update `setup.py --version` output if it reads from a different source.

### 2. Update CHANGELOG Version Header (Required)

**File:** `CHANGELOG.md`

**Current:** `[0.9.0-s3-e2e-and-type-cleanup]`

**Required:** Update to reflect actual release version (e.g., `[0.9.1]` or `[1.0.0-rc1]`)

### 3. Update README Version Badge (If Needed)

**File:** `README.md`

**Current:** `![Version](https://img.shields.io/badge/Version-0.8.0b1-blue?style=flat-square)`

**Required:** Update to match new version.

---

## Optional Enhancements for v1.0 RC

### 1. MinIO E2E in CI

The MinIO e2e test script exists at `scripts/dev/minio-e2e.py` but was not run in this pass. For v1.0 RC, consider:

- Adding MinIO e2e to the CI pipeline (requires Docker in CI)
- Or documenting that MinIO e2e is a manual pre-release check

### 2. Multipart Upload (Future)

Multipart upload is declared as NOT IMPLEMENTED. If needed for v1.0, it requires:
- Implementation in S3-compatible provider
- CLI integration for large file handling
- Tests

### 3. Backblaze B2 Real Implementation (Future)

B2 is currently docs-only. A real implementation would:
- Create `worker/storage/providers/b2.py`
- Implement upload/download/delete/list
- Add e2e tests

---

## Hard Rules for v1.0 RC

| Rule | Status |
|------|--------|
| Do not publish to PyPI | ✅ Will not happen |
| Do not force push | ✅ Will not happen |
| Do not commit secrets | ✅ Verified |
| Do not claim unsupported capabilities | ✅ Fixed |
| Do not mark B2 as supported unless real upload/download works | ✅ Fixed |
| Do not mark direct-to-S3 as supported unless CLI actually uses presigned URL directly | ✅ Fixed |
| Do not mark multipart as supported unless implemented and tested | ✅ Fixed |
| Keep System provider default | ✅ Verified |
| Keep S3-compatible as beta verified through Worker-proxy flow with MinIO | ✅ Verified |
| Keep upload-only sync messaging | ✅ Verified |
| All critical tests must pass | ✅ Verified |

---

## Commit Message

When ready to commit:

```
chore(release): harden Cheri before v1.0 RC
```

Files to stage:
- `cheri_cloud_cli/` (Python fixes)
- `worker/storage/` (capability fixes)
- `docs/storage/` (doc fixes)
- `scripts/dev/v1-readiness-gate.sh` (new)
- `reports/` (new reports)
- `README.md` (if version badge updated)
- `CHANGELOG.md` (if version header updated)
- `setup.py`, `pyproject.toml`, `package.json` (if version updated)

Do NOT stage:
- `dist/` or `build/` directories
- `.egg-info/` directories
- `.env` files
- Credentials files
- `.key`, `.pem`, `id_rsa`, `id_ed25519` files
- `node_modules/`
- `.log` files

---

## After v1.0 RC

For v1.0 final release, consider:

1. **Bidirectional sync** — The biggest missing feature
2. **Conflict resolution UI** — Needed for team workflows
3. **Google Drive provider** — Docs-only since v0.3
4. **Multipart upload** — For large file support
5. **Backblaze B2 real provider** — Beyond docs-only
