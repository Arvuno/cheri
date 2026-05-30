# Next v0.6 Reliability Plan

## Context

v0.5.1-handoff-content successfully implemented real file upload/download for handoff push/pull. The v0.6 release should focus on reliability hardening.

## Identified Issues

### 1. Node Worker Test Failures (Pre-existing)
- `worker.test.mjs`: register endpoint returns 500 instead of 201
- `storage.test.mjs`: register endpoint response structure mismatch

**Recommendation:** Investigate and fix register endpoint. This blocks confident deployment.

### 2. Worker Test Infrastructure
- Tests use mocked KV but real register endpoint calls
- Could isolate handoff tests from register dependency

**Recommendation:** Add handoff-specific unit tests that mock KV directly.

### 3. Pull Without manifest_file_id
- If old handoff from v0.5.0 doesn't have manifest_file_id, pull falls back to backend metadata
- Backend metadata may not have full manifest JSON stored

**Recommendation:** When manifest unavailable on pull, show clear error with "run 'cheri handoff show' to check status"

### 4. No Retry on Upload Failure
- Push fails a file once and moves on (correct behavior for partial failure)
- But no retry mechanism for transient failures (network blip)

**Recommendation:** Add optional `--retry` flag to push for transient failure retry.

### 5. No Progress Reporting During Upload
- Large handoffs show no progress until complete
- User sees silent delay during upload

**Recommendation:** Add per-file progress (e.g., "Uploading 3/12: src/app.js")

## Suggested v0.6 Focus Areas

### A. Reliability Hardening
1. Fix register endpoint (unblock tests)
2. Add retry logic for transient upload failures
3. Add progress reporting for large handoffs
4. Improve error messages for pull without manifest

### B. Testing Coverage
1. Add Node.js unit tests for handoff service functions (mock KV)
2. Add integration tests for full push → pull cycle
3. Add test for partial failure scenario

### C. Documentation
1. Document partial failure behavior in CLI help
2. Document pull requirements (manifest must be stored)
3. Add troubleshooting section for common handoff issues

## Exit Criteria for v0.6

| Criterion | Target |
|-----------|--------|
| All Node worker tests pass | 100% |
| Push retry on transient failure | Working |
| Pull progress reporting | Working |
| Clear error on pull without manifest | Working |
| Integration test for push→pull cycle | Written and passing |

## Not in Scope for v0.6

- Bidirectional sync (handshake/merge) — beyond handoff scope
- Multiple concurrent handoffs — workspace-level concern
- Handoff expiration/cleanup — separate feature