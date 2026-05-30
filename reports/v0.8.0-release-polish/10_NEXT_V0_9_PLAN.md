# Next v0.9 Plan

> Date: 2026-05-30

## v0.8.0-release-polish Summary

**Status:** READY_WITH_LIMITATIONS

**Critical tests:** ALL PASSED
- Python tests: 149/149 ✅
- Worker tests: 7/7 ✅
- Storage tests: 13/13 ✅
- npm test: PASS ✅
- Ruff: PASS ✅
- Package build: 0.8.0b1 ✅

**Limitations documented:**
- Mypy: 49 pre-existing type errors
- S3-compatible: upload/download e2e not tested
- Ruff E402: circular import with noqa

## v0.9 Priority Features

### P0 — S3-Compatible Provider E2E (Critical Path)

**Why:** S3-compatible is the path to persistent storage beyond Cloudflare R2.

**Tasks:**
1. Implement full CLI → Worker → S3 upload via presigned URLs
2. Implement full CLI → Worker → S3 download via presigned URLs
3. Add checksum verification end-to-end
4. Configure MinIO in CI/CD for automated testing
5. Test with real S3 bucket, MinIO, Backblaze B2

**Success criteria:**
- `cheri file upload test.txt` → S3-compatible → verified by download
- MinIO smoke test in CI passes
- Backblaze B2 works (if credentials provided)

### P1 — Type Cleanup Sprint

**Why:** 49 mypy errors are accumulating debt.

**Tasks:**
1. Audit 49 mypy errors by category
2. Fix simple ones with type: ignore or minor refactors
3. Create type stubs for keyring if needed
4. Add mypy to CI gate

**Success criteria:**
- mypy errors < 20

### P2 — Multipart Upload (Large Files)

**Why:** Current single-part upload limited to 5GB.

**Tasks:**
1. Implement multipart upload for S3-compatible provider
2. Add progress reporting for large files
3. Handle upload interruption gracefully

### P3 — Documentation

**Why:** Storage providers need clearer documentation.

**Tasks:**
1. Complete `docs/storage/MINIO_E2E_TESTING.md` with full flow
2. Add `docs/storage/BACKBLAZE_B2.md`
3. Update `docs/storage/PROVIDER_MATRIX.md` with e2e status

## v0.9 Out of Scope

- Bidirectional sync (complex, requires design)
- Conflict resolution UI (needs UX work)
- Google Drive provider (low priority, API complexity)

## Suggested Branch Structure

```bash
git checkout -b v0.9-s3-e2e
git checkout -b v0.9-type-cleanup
git checkout -b v0.9-multipart
```

## Release Criteria for v0.9

- [ ] S3-compatible upload/download e2e verified
- [ ] Mypy errors < 20
- [ ] MinIO in CI
- [ ] Multipart upload working
- [ ] All tests pass