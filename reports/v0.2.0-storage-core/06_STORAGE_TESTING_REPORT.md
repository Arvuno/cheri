# 06 — Storage Testing Report

## Test Suite

### Worker Tests (Node.js)

**File:** `tests/node/worker.test.mjs` (existing, 6 tests — all pass)
**File:** `tests/node/storage.test.mjs` (new, 7 tests — all pass)

New storage tests:
1. `storage providers endpoint returns catalog with no secrets` ✅
2. `experimental providers are hidden unless include_experimental=1` ✅
3. `provider validate endpoint accepts system provider and returns redacted config` ✅
4. `file upload includes provider_id in metadata when using system provider` ✅
5. `storage providers returns experimental status for s3-compatible` ✅
6. `system provider is the only ready provider in default catalog` ✅
7. `file list response includes provider metadata` ✅

### Python Tests

**File:** `tests/python/test_storage.py` (new, 9 tests — all pass)

- `test_lists_providers_without_experimental` ✅
- `test_lists_providers_with_experimental` ✅
- `test_warns_about_experimental_when_excluded` ✅
- `test_handles_client_error_gracefully` ✅
- `test_shows_status_for_active_workspace` ✅
- `test_handles_no_active_workspace` ✅
- `test_handles_not_logged_in` ✅
- `test_reports_backend_health` ✅
- `test_handles_backend_unreachable` ✅

Plus 52 existing Python tests in `tests/python/` — all continue to pass.

## Coverage Summary

| Component | Tested |
|---|---|
| Provider registry and catalog | ✅ |
| System provider (R2) upload/download | ✅ |
| Provider validation | ✅ |
| Experimental provider gating | ✅ |
| Secret redaction in API | ✅ |
| File metadata includes provider_id | ✅ |
| CLI provider list formatting | ✅ |
| CLI storage status | ✅ |
| CLI storage check | ✅ |

## Gaps (Not Covered in v0.2.0)

- S3-compatible provider actual upload/download (requires real credentials)
- Local dev provider (test-only, implicitly tested via storage.test.mjs)
- Migration dry-run (v0.3.0 scope)
- `cheri storage configure` command (v0.3.0 scope)

## Verification Commands

```bash
node tests/node/worker.test.mjs      # 6/6 pass
node tests/node/storage.test.mjs     # 7/7 pass
python -m unittest discover -s tests/python -p "test_*.py"  # 61/61 pass
```

## Known Test Limitations

- S3-compatible integration tests need real S3 bucket (marked experimental)
- Local dev provider tests are implicit (no dedicated test adapter tests)
- Provider config persistence tests need full KV integration