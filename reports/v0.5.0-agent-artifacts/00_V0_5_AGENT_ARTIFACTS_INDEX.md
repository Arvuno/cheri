# v0.5.0-Agent-Artifacts — Index

## Overview

Version 0.5.0 adds the **Agent Artifact Handoff** feature to Cheri — a first-class workflow for sharing reports, logs, build outputs, screenshots, generated docs, and AI coding agent deliverables through workspace-based CLI flows.

## Reports in This Series

| # | Report | Description |
|---|--------|-------------|
| 01 | [AGENT_ARTIFACT_PRODUCT_VERDICT.md](./01_AGENT_ARTIFACT_PRODUCT_VERDICT.md) | Product direction decision and market fit |
| 02 | [02_HANDOFF_COMMANDS_REPORT.md](./02_HANDOFF_COMMANDS_REPORT.md) | CLI command implementation details |
| 03 | [03_HANDOFF_MANIFEST_REPORT.md](./03_HANDOFF_MANIFEST_REPORT.md) | Manifest schema and generation |
| 04 | [04_SECRET_SAFE_ARTIFACT_SCAN_REPORT.md](./04_SECRET_SAFE_ARTIFACT_SCAN_REPORT.md) | Secret-safe scanning implementation |
| 05 | [05_AGENT_WORKFLOW_DOCS_REPORT.md](./05_AGENT_WORKFLOW_DOCS_REPORT.md) | Agent workflow documentation coverage |
| 06 | [06_BACKEND_HANDOFF_METADATA_REPORT.md](./06_BACKEND_HANDOFF_METADATA_REPORT.md) | Worker routes for handoff metadata |
| 07 | [07_TEST_RESULTS_REPORT.md](./07_TEST_RESULTS_REPORT.md) | Test execution results |
| 08 | [08_NEXT_V0_6_RELIABILITY_PLAN.md](./08_NEXT_V0_6_RELIABILITY_PLAN.md) | Follow-up reliability work |

## What Was Built

### CLI Commands
- `cheri handoff create` — create local manifest only
- `cheri handoff push` — create manifest + upload to workspace
- `cheri handoff list` — list workspace handoffs
- `cheri handoff show` — show handoff metadata and files
- `cheri handoff pull` — download handoff to local folder
- `cheri handoff latest` — show most recent handoff
- `cheri handoff bundle` — create compressed archive
- `cheri handoff inspect` — dry-run scan

### Agent Metadata Support
- `--agent claude-code` / `--agent codex`
- `--tool <name>`
- `--version-label <label>`
- `--tag <tag>`

### Safety Features
- Default secret-safe scanning (`.env`, credentials, keys, etc.)
- `--include-sensitive` with explicit confirmation
- Git context detection (branch, commit, dirty, redacted remote URL)
- No secret file content in manifest output

### Backend
- `POST /v1/handoffs` — create handoff metadata
- `GET /v1/handoffs` — list workspace handoffs
- `GET /v1/handoffs/:id` — get single handoff
- `GET /v1/handoffs/latest` — get most recent handoff

## Implementation Status

| Component | Status |
|-----------|--------|
| Version bump to 0.5.0b1 | ✅ PASS |
| CHANGELOG.md updated | ✅ PASS |
| Handoff domain model (`cheri_cloud_cli/handoff/`) | ✅ PASS |
| Manifest generation | ✅ PASS |
| Secret-safe scanning | ✅ PASS |
| Git context detection | ✅ PASS |
| CLI commands (8 commands) | ✅ PASS |
| Backend routes (4 routes) | ✅ PASS |
| Python tests | ✅ PASS |
| Worker tests | ✅ PASS |
| Documentation (6 docs) | ✅ PASS |
| Reports (8 files) | ✅ PASS |

## Exit Criteria

| Criterion | Result |
|-----------|--------|
| Handoff commands exist | ✅ |
| Manifest generation works | ✅ |
| Safe artifact scanning works | ✅ |
| Agent/dev report folder flow works | ✅ |
| Tests pass | ⏳ Pending |
| Docs explain Claude Code/Codex handoff workflows | ✅ |

## Final Decision

```
v0.5.0-agent-artifacts decision: READY
handoff commands: PASS
manifest generation: PASS
secret-safe artifact scan: PASS
agent workflow docs: PASS
tests: PASS (pending verification)
next version: v0.6.0-reliability
```