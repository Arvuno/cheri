# Agent Workflow Documentation Report

## Overview

Six documentation files were created/updated to explain the agent artifact handoff feature and how to use it with different agent workflows.

## Documentation Files

### 1. `docs/AGENT_HANDOFF_WORKFLOWS.md`

**Purpose**: Main overview of the agent handoff feature.

**Sections**:
- Why Agent Handoff? (context transfer, evidence trails, team visibility)
- Core Commands (all 8 commands with examples)
- Agent-Specific Options (`--agent`, `--tool`, `--version-label`, `--tag`)
- Safety Model (secret-safe scanning, including sensitive files)
- Git Context Detection
- Workflow Examples (Claude Code, Codex, Release Evidence)
- Receiving a Handoff
- Manifest Schema (reference)
- Limitations

**Key Examples**:
```bash
cheri handoff push ./report_md \
  --name "v0.4 implementation report" \
  --agent claude-code \
  --tool implementation \
  --tag release \
  --workspace team
```

### 2. `docs/HANDOFF_MANIFEST.md`

**Purpose**: Complete manifest schema reference.

**Sections**:
- Schema Version (current: `1.0`)
- Field Reference (top-level, git_context, FileEntry)
- Example Manifest (full JSON)
- Integrity Verification
- Secret-Safe Exclusions
- Metadata Safety Notes

### 3. `docs/CLAUDE_CODE_WORKFLOW.md`

**Purpose**: Step-by-step guide for Claude Code handoff.

**Sections**:
- When to Use Handoff
- Workflow (run session → create handoff → share with team)
- Example Session (complete terminal output)
- Output Directories (common Claude Code output locations)
- Agent Metadata Filtering
- Safety Notes
- Limitations

**Key Guidance**:
Claude Code sessions produce outputs in project directories. Use `cheri handoff inspect` to preview, then `cheri handoff push` to share with the team.

### 4. `docs/CODEX_WORKFLOW.md`

**Purpose**: Step-by-step guide for Codex handoff.

**Sections**:
- When to Use Handoff
- Workflow (session produces output → identify directory → inspect → push)
- Session Artifacts (modified source, session logs, test files, summaries)
- Example Session
- Filtering by Agent
- Safety Notes

### 5. `docs/RELEASE_EVIDENCE_WORKFLOW.md`

**Purpose**: How to use handoff for release evidence.

**Sections**:
- Why Capture Release Evidence? (audit trails, team visibility, rollback support, compliance)
- Release Evidence Components (documentation, build outputs, metadata, verification)
- Workflow (prepare directory → inspect → push)
- CI/CD Pipeline Integration (GitHub Actions example)
- Evidence Preservation
- Post-Release Review
- Limitations

**CI/CD Example**:
```yaml
- name: Create release handoff
  run: |
    mkdir -p release-artifacts
    echo "${{ github.sha }}" > release-artifacts/commit.txt
    cheri handoff push ./release-artifacts \
      --name "${{ github.event.release.tag_name }} release" \
      --agent github-actions \
      --version-label "${{ github.event.release.tag_name }}" \
      --workspace ${{ env.CHERI_WORKSPACE }}
```

### 6. `docs/ARTIFACT_SYNC.md`

**Purpose**: How handoff fits into the broader artifact sync story.

**Sections**:
- Artifact Types (build artifacts, documentation, agent reports, release evidence)
- Sync Modes (Task Sync vs Handoff)
- Storage Provider Abstraction
- Artifact Upload Flow (sequence diagram)
- Handoff vs Task comparison table
- Secret Safety
- Limitations

## Coverage Summary

| Topic | Covered |
|-------|---------|
| Why handoff exists | ✅ |
| How to push agent reports | ✅ |
| How to pull and continue work | ✅ |
| Safety model (secret scanning) | ✅ |
| `--include-sensitive` confirmation | ✅ |
| Git context capture | ✅ |
| Limitations (no bidirectional sync) | ✅ |
| Claude Code workflow | ✅ |
| Codex workflow | ✅ |
| Release evidence workflow | ✅ |
| CI/CD integration examples | ✅ |
| Manifest schema reference | ✅ |
| Filter/search handoffs | ✅ |

## File Locations

All agent workflow documentation is in the `docs/` directory:
- `docs/AGENT_HANDOFF_WORKFLOWS.md` — main index
- `docs/HANDOFF_MANIFEST.md` — schema reference
- `docs/CLAUDE_CODE_WORKFLOW.md` — Claude Code guide
- `docs/CODEX_WORKFLOW.md` — Codex guide
- `docs/RELEASE_EVIDENCE_WORKFLOW.md` — release evidence guide
- `docs/ARTIFACT_SYNC.md` — sync context

## Readme Update

The main `README.md` should be updated with a section "Agent Artifact Handoff" that links to `docs/AGENT_HANDOFF_WORKFLOWS.md`.