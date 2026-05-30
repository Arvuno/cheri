# Storage E2E MinIO Report

> Date: 2026-05-30

## MinIO Smoke Test

Script: `scripts/dev/minio-smoke.sh`

### Results

**Infrastructure Test:** PASSED
- MinIO container starts successfully
- Health check endpoint responds
- Bucket creation works (via API)
- File upload via raw API works (with AWS4-HMAC-SHA256 auth)

**Note:** Raw MinIO API requires AWS Signature Version 4. The Cheri handoff CLI upload uses direct-to-worker flow (not direct-to-S3), so this is not blocking.

## S3-Compatible Provider Status

| Component | Status | Notes |
|-----------|--------|-------|
| Config validation | ✅ Implemented | Worker-side validateConfig() works |
| Upload (presigned URL) | ✅ Implemented | Worker returns presigned PUT URL |
| Download (presigned URL) | ✅ Implemented | Worker returns presigned GET URL |
| Full CLI→Worker→S3 upload | ⚠️ PENDING | Not e2e tested |
| Full CLI→Worker→S3 download | ⚠️ PENDING | Not e2e tested |

## Worker Storage Tests (Mock)

Storage tests (`tests/node/storage.test.mjs`) verify:
- Provider catalog with no secrets exposed
- Experimental provider gating
- System provider ready status
- File upload with provider_id metadata
- Secret encryption when CHERI_PROVIDER_SECRET_KEY set

All 13 tests pass with mock storage.

## Files Created

- `scripts/dev/minio-smoke.sh` — MinIO infrastructure test script
- `docs/storage/MINIO_E2E_TESTING.md` — Manual testing guide

## Known Limitations

1. **Full upload/download e2e not tested** — CLI→Worker→S3 presigned URL flow needs real S3-compatible bucket
2. **MinIO AWS4 auth required** — Raw MinIO API requires proper signing
3. **No CI/CD MinIO** — Docker-in-Docker or external service needed for automated testing

## Result

**MANUAL_ONLY** — MinIO infrastructure works. Full S3-compatible e2e pending v0.9.