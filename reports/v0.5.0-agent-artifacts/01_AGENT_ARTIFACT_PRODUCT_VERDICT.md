# Agent Artifact Product Verdict

## Decision: Proceed with Agent Artifact Handoff as v0.5.0

Cheri's differentiation is now **Agent/Dev Artifact Handoff**: sharing reports, logs, build outputs, screenshots, generated docs, and AI coding agent deliverables through workspace-based CLI flows.

## Rationale

### Market Fit

AI coding agents (Claude Code, Codex, Cursor, etc.) are becoming a significant part of developer workflows. These agents produce artifacts — reports, logs, generated code, build outputs — that teams want to share, review, and preserve.

Existing tools:
- Git: good for code, not for artifacts/reports
- Slack/Teams: good for ephemeral sharing, not for preservation
- S3/Google Drive: good for storage, not for workspace visibility

**Cheri's workspace-based handoff fills this gap**: an agent can produce artifacts, run `cheri handoff push`, and the team immediately sees the handoff in their workspace context.

### Why Not Bidirectional Sync?

Bidirectional sync would require:
- Merge conflict resolution
- Real-time change detection
- More complex data model

For artifact handoff, discrete uploads are cleaner and more appropriate. The recipient pulls the artifact and continues from there. This is analogous to handing off a USB drive — not a shared Google Doc.

### Risk Assessment

| Risk | Mitigation |
|------|------------|
| No real backend need | Backend uses existing KV and storage abstraction; minimal new code |
| Secret exposure | Secret-safe scanning with default exclusions; explicit `--include-sensitive` |
| Agent adoption uncertain | Agent workflows are CLI-based; easy to integrate into any agent's shell commands |
| Metadata visibility | Workspace members can see manifest; no secret values stored |

## Implementation Choices

### CLI-First

All handoff operations are available via CLI, making them scriptable and integrable into CI/CD pipelines and agent workflows.

### Manifest-First

The manifest (`cheri-handoff.json`) is the core artifact. It can be inspected, verified, and used without needing Cheri backend access.

### Secret-Safe Default

Default exclusions ensure sensitive files are never accidentally uploaded. This builds trust for team use cases.

### Git Context Capture

Including Git context helps recipients understand the exact state of artifacts they receive. Redacting credentials from remote URLs prevents information leakage.

## What's Not Included

- Bidirectional sync (by design)
- Real-time agent communication
- Merge/reconcile on pull
- Agent-to-agent negotiation

These are out of scope for v0.5.0. The feature is intentionally focused on discrete handoff workflows.

## Conclusion

Agent artifact handoff is the right differentiation for Cheri at this stage. It leverages existing workspace infrastructure, fits naturally with the CLI-first model, and addresses a real pain point in AI-assisted development workflows.

**Verdict: ✅ Build it.**