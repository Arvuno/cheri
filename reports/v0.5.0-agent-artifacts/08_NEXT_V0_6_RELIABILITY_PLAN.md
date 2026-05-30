# Next Version: v0.6.0-Reliability Plan

## Rationale

v0.5.0-agent-artifacts introduced the handoff feature. v0.6.0 should focus on reliability improvements — making the feature production-ready by addressing known gaps and hardening the implementation.

## Priority Areas

### 1. Storage Provider Integration for Handoff Files

**Current State**: Handoff metadata is stored in KV, but file content upload is not implemented.

**Goal**: When `cheri handoff push` is called, files should actually be uploaded to the workspace's storage provider.

**Tasks**:
- Integrate file upload into handoff push flow
- Use existing `POST /v1/files/upload-grant` mechanism
- Update manifest with storage keys
- Support download of handoff file content

### 2. End-to-End Verification Testing

**Current State**: Unit tests and worker tests exist, but no E2E flow test.

**Goal**: Add Playwright or similar E2E tests that:
- Create a handoff
- Push to workspace
- List handoffs
- Pull handoff
- Verify file integrity

**Tasks**:
- Add E2E test for handoff flow
- Add test for CLI handoff commands against real backend

### 3. Handoff Search/Filter

**Current State**: List shows all handoffs, no filtering.

**Goal**: Add filtering by:
- Agent name (`--agent claude-code`)
- Tags (`--tag release`)
- Date range
- File count / size range

**Tasks**:
- Add query params to `GET /v1/handoffs`
- Update CLI to support `--agent`, `--tag` filters

### 4. Handoff Delete/Archive

**Current State**: Handoffs persist indefinitely.

**Goal**: Allow users to:
- Archive old handoffs
- Delete handoffs they created
- Admin bulk delete

**Tasks**:
- `DELETE /v1/handoffs/:id` route
- `cheri handoff delete` CLI command
- Retention policy option

### 5. Handoff Diff/Compare

**Current State**: Each handoff is independent.

**Goal**: Compare two handoffs:
- What files changed?
- What was added/removed?

**Tasks**:
- `cheri handoff diff <handoff-id-1> <handoff-id-2>`
- Use manifest checksums to detect changes

### 6. Progress Indicator for Large Handoffs

**Current State**: Upload shows minimal feedback.

**Goal**: Rich progress display:
- Files scanned: X/Y
- Uploaded: A/B
- Speed: bytes/sec
- ETA

**Tasks**:
- Update CLI progress display
- Add progress callback to file upload

## Lower Priority

### 7. Webhook Notifications

When a handoff is created, notify team via webhook.

### 8. Handoff Comments/Review

Allow team members to add comments to handoffs.

### 9. Handoff Categories

Organize handoffs into categories beyond tags.

## Version Goals

| Goal | Target |
|------|--------|
| Storage provider integration | Must have |
| E2E tests | Should have |
| Search/filter | Should have |
| Delete/archive | Could have |
| Diff/compare | Could have |
| Progress indicator | Could have |

## Breaking Changes to Avoid

- CLI command signatures should remain stable
- Manifest schema should remain backward compatible
- No removal of existing functionality

## Migration Path

If manifest schema needs changes in future:
- Version the schema (`schema_version` field)
- Support reading older versions
- Warn when writing older versions

## Verification Criteria for v0.6.0

```
v0.6.0-reliability decision: READY
storage integration: PASS / FAIL
e2e tests: PASS / FAIL
search/filter: PASS / FAIL
delete/archive: PASS / FAIL
diff/compare: PASS / FAIL
next version: v0.7.0-features
```