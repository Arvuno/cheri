# Artifact Sync

This document describes how Cheri handles artifact synchronization in the context of agent workflows.

## Overview

Cheri is a CLI-first collaborative workspace sync tool. The `cheri handoff` feature adds first-class support for artifact/handoff workflows typical in AI-assisted development.

## Artifact Types

Cheri handles several categories of artifacts:

### 1. Build Artifacts
- Compiled output (binaries, compiled assets)
- Test results (JUnit XML, coverage reports)
- Build logs

### 2. Documentation Artifacts
- Generated README files
- API documentation
- Architecture decision records
- Release notes

### 3. Agent Reports
- Implementation reports (Claude Code)
- Session artifacts (Codex)
- Debugging session logs
- Code review summaries

### 4. Release Evidence
- Changelog files
- Version metadata
- Deployment records
- Audit trails

## Sync Modes

Cheri supports different sync modes for different use cases:

### Task Sync (`cheri task`)
- Continuous monitoring
- On-change or interval-based upload
- Ideal for directories that change frequently

### Handoff (`cheri handoff`)
- Discrete, point-in-time artifacts
- One-time upload with manifest
- Ideal for completed work, reports, and evidence

## Storage Provider Abstraction

Cheri uses a storage provider abstraction layer. Handoffs use the same storage layer as file uploads:

1. **System Provider** (default): Files stored in the Cheri backend's R2 bucket
2. **S3-compatible**: Files stored in a configured S3-compatible bucket
3. **Backblaze B2**: Files stored in Backblaze B2

The provider is configured per-workspace via `cheri storage configure`.

## Artifact Upload Flow

```
User/Agent                  Cheri CLI                   Backend
    |                           |                          |
    | cheri handoff push ...     |                          |
    |-------------------------->|                          |
    |                           |                          |
    |  Scan path (secret-safe)  |                          |
    |  Generate manifest        |                          |
    |                           |                          |
    |                           | POST /v1/handoffs        |
    |                           |------------------------->|
    |                           |              201 Created |
    |                           |<-------------------------|
    |                           |                          |
    |                           | Upload files via         |
    |                           | storage provider        |
    |                           |------------------------->|
    |                           |                          |
    |  Show confirmation        |                          |
    |<--------------------------|                          |
```

## Handoff vs Task

| Aspect | Task Sync | Handoff |
|--------|-----------|---------|
| Trigger | On-change / interval | Manual / one-time |
| Scope | Continuous directory | Discrete artifact |
| Manifest | Snapshot JSON | cheri-handoff.json |
| Files | All allowed files | All allowed + metadata |
| Typical use | Source code dirs | Reports, evidence, outputs |
| Git context | Per-scan snapshot | Full context captured |

## Secret Safety

Both task sync and handoff use the same secret-safe scanning:

- Default exclusions prevent sensitive files from being uploaded
- `.env`, credentials, SSH keys, etc. are always skipped
- `--include-sensitive` requires explicit confirmation
- Skipped files are listed by name only (no content)

## Limitations

- **No bidirectional sync**: Handoffs are upload-only by design
- **No merge/reconcile**: Pulling a handoff to a directory with existing files does not merge
- **No delta compression**: Each handoff upload is independent
- **Manifest visible to workspace**: Handoff metadata is stored in the workspace KV and visible to all members