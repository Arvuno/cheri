# 09 — Next v0.3.0-provider-beta Plan

## Scope

v0.3.0 adds user-selectable storage provider configuration.

## Tasks

### 10. Storage Provider Configuration UX

Add `cheri storage configure --provider <kind>` command:
- System provider: just confirm warning (no credentials)
- S3-compatible: prompt for endpoint, bucket, region, access_key_id, secret_access_key
- Security warning before entering third-party credentials
- Validate before saving (call `POST /v1/providers/validate`)
- Failed validation does not corrupt existing workspace config

### 11. S3-Compatible Provider Beta

Complete `worker/storage/providers/s3_compatible.js`:
- Add multipart upload support (if straightforward)
- Add checksum verification after upload
- Add `copyObject` for migration
- If any of these are too risky, mark as `not_ready` with clear messaging

### 12. MinIO Support Path

Ensure S3-compatible design works for MinIO:
- `force_path_style: true` documented and tested
- MinIO-specific endpoint format documented
- Local testing example in `docs/storage/MINIO_SELF_HOSTED.md`

### 13. Backblaze B2 Path

Documented in `docs/storage/B2_S3_COMPATIBLE.md`:
- B2 S3-compatible endpoint configuration
- Key differences from AWS S3

### 14. Storage Migration Design CLI

```bash
cheri storage migrate plan --to s3-compatible
cheri storage migrate dry-run --to s3-compatible
```

Output includes: file count, total size, operations needed, rollback plan.
Destructive migration NOT implemented in v0.3.0.

### 15. Tests for v0.3

- configure System provider
- reject invalid provider config (bad endpoint, missing credentials)
- secrets not echoed to output
- experimental provider requires explicit confirmation
- migration dry-run does not modify files
- provider status appears in workspace status

### 16. Documentation Updates

- README: add "storage provider architecture" section
- `docs/storage/PROVIDER_MATRIX.md`: update with v0.3 status
- `docs/storage/S3_COMPATIBLE_PROVIDER.md`: update after S3 beta
- `docs/TROUBLESHOOTING.md`: add storage provider troubleshooting

### 17. Reports for v0.3

Create `reports/v0.3.0-provider-beta/` with 9 reports.

## Exit Criteria for v0.3.0

- Users can see provider options via `cheri storage providers`
- System provider remains safe default
- Experimental providers are gated behind flag/confirmation
- S3-compatible path is either beta-working or honestly marked `not_ready`
- MinIO and B2 paths documented
- No provider secrets leak in CLI/API/test output