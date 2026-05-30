# README Public Polish Report

> Date: 2026-05-30

## Changes Made

### Badges
- Added Version badge (0.8.0b1)
- Changed Status from "Beta" to "Public Beta"

### Current Status Table
- Added "v0.8.0-public-beta" header
- Clarified S3-compatible as "upload/download e2e pending"
- Added "Daily file reset" limitation

### Storage Provider Status Table (New)
Added explicit storage provider matrix:

| Provider | Status | Notes |
|----------|--------|-------|
| System (recommended) | Production-ready | Cloudflare R2, daily reset |
| S3-compatible | Experimental | MinIO/B2 tested via config validation |
| Google Drive | Docs-only | Not implemented |
| Backblaze B2 | Docs-only | S3-compatible mode possible |

### Agent Handoff Section (New)
Added prominent section for agent handoff commands:
- `cheri handoff push`
- `cheri handoff pull`
- `cheri handoff list`
- `cheri handoff diff`

### Roadmap Section (New)
Added forward-looking roadmap table with v0.9 targets.

### Known Limitations
- S3-compatible upload/download e2e pending
- Daily file reset (System provider)
- No bidirectional sync
- No conflict resolution

## Verification

- All claims match current implementation status
- No false claims of production-readiness
- Storage provider status honestly labeled
- Version badges consistent with 0.8.0b1

## Result

**PASS** — README is GitHub-ready with honest status reporting.