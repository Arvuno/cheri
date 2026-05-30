# Remaining Risks and v0.2.0 Plan

## v0.1.0 Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Keyring fallback in shared environments | MEDIUM | Warning printed; keyring fallback not encrypted |
| Credentials.json migration is one-time | LOW | Migration note in file prevents re-migration |
| No E2E tests for auth flow | MEDIUM | Worker tests cover backend; CLI auth flow manual |
| No integration tests for Worker + DB | LOW | FakeKV/FakeR2 used in tests; real env separate |
| README claims "beta foundation" not explicit | LOW | Version 0.1.0b1 communicates this |
| docs/DEPLOYMENT.md not written | LOW | Self-hosting instructions deferred |

## v0.2.0-storage-core — Priority Work

### Must Have

1. **Storage provider interface** — Unified `StorageProvider` ABC with:
   - `validate_config()` — async validation of provider settings
   - `put_object()` / `get_object()` / `delete_object()` / `list_objects()`
   - `stat_object()` / `generate_upload_url()` / `generate_download_url()`

2. **S3-compatible provider** — boto3-based implementation:
   - `put_object()` → `client.put_object(Bucket=bucket, Key=key, Body=data)`
   - `get_object()` → `client.get_object(Bucket=bucket, Key=key)`
   - Upload presigning via `client.generate_presigned_url()`
   - Credential fields: endpoint, bucket, region, access_key_id, secret_access_key

3. **Provider credential storage** — Keyring-backed per workspace:
   - Each workspace has provider config stored in KV
   - Secret-bearing fields stored in OS keyring, not KV
   - Migration path for existing System-only workspaces

4. **Provider catalog update** — Worker `GET /v1/providers`:
   - S3-compatible: `selectable: true` (when implemented)
   - Backblaze B2: `selectable: true` (when implemented)
   - Remove `coming_soon` from implemented providers

5. **Provider validation route** — `POST /v1/providers/validate`:
   - Call provider-specific validation (e.g., boto3 head_bucket for S3)
   - Return structured validation state with errors/warnings

### Should Have

6. **Upload/download with non-System providers** — End-to-end flow:
   - CLI sends provider config on workspace create
   - Worker uses correct provider adapter for upload grants
   - R2 replaced by S3/B2/etc. for actual storage

7. **Error handling for provider failures** — Structured errors:
   - S3: handle 403 (bad credentials), 404 (bucket not found), 503 (throttling)
   - GDrive: handle 401 (refresh token expired), 403 (insufficient permissions)
   - B2: handle 401 (bad key), 404 (bucket not found)

### Could Have

8. **Encrypted at-rest for non-keyring environments** — Using bootstrap-derived key
9. **Secret rotation** — Allow updating provider credentials without recreation
10. **Multi-provider workspaces** — Single workspace with files on multiple providers

## v0.1.0 Exit Confirmation

All exit criteria from the original task were met:
- [x] License exists (MIT)
- [x] Credentials not plaintext with keyring available
- [x] `.env` and common secret files excluded from task scanning by default
- [x] Worker tests run (6/6)
- [x] Python tests pass (52/52)
- [x] CI workflow exists
- [x] Non-System providers not misleadingly exposed
- [x] README accurately describes product limitations
- [x] v0.1.0-foundation reports exist (8/8)

## Recommended Next Step

Tag `v0.1.0b1`, then begin v0.2.0-storage-core with the storage provider interface design doc.