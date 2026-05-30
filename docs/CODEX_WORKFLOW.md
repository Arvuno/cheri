# Codex Workflow

This document describes how to use Cheri's handoff feature with Codex (OpenAI's coding agent) development sessions.

## Overview

Codex is OpenAI's AI coding agent that runs in various IDE integrations. After a Codex session, you can use `cheri handoff` to share session artifacts and outputs with your team.

## When to Use Handoff

Use `cheri handoff` when:

- A Codex session produced artifacts you want to preserve
- You want to share generated code, session summaries, or test results
- You need to hand off Codex work to a human developer or another agent

## Workflow

### 1. Codex Session Produces Output

Codex sessions typically produce artifacts in the project directory:

- Modified source files
- Session logs
- Generated test files
- Implementation summaries

### 2. Identify Output Directory

Common Codex output locations:

```bash
# VS Code extension: often in project root
ls -la

# Or in a dedicated output directory
ls -la ./codex-output/
ls -la ./session-logs/
```

### 3. Inspect and Push

```bash
# Inspect what will be included
cheri handoff inspect ./codex-output

# Push to workspace
cheri handoff push ./codex-output \
  --name "codex session 2026-05-30" \
  --agent codex \
  --version-label "session-2026-05-30" \
  --workspace team
```

### 4. Share with Team

```bash
# Confirm upload
cheri handoff latest

# Team members can pull
cheri handoff pull hnd_xyz789 --dest ~/codex-sessions/session-2026-05-30
```

## Session Artifacts

Codex sessions commonly produce:

| Artifact Type | Description | Example Files |
|---------------|-------------|---------------|
| Modified source | Changed code files | `src/*.py`, `src/*.ts` |
| Session logs | Console output, errors | `codex.log`, `session.txt` |
| Test files | Generated tests | `tests/test_*.py` |
| Summaries | Implementation notes | `SUMMARY.md`, `NOTES.md` |

## Example

```bash
$ cheri handoff push ./codex-output \
    --name "feature implementation session" \
    --agent codex \
    --tag implementation \
    --version-label "2026-05-30"

[cyan]Creating handoff for[/] /home/user/projects/myapp/codex-output...
[green]Manifest written:[/] /home/user/projects/myapp/codex-output/cheri-handoff.json
[cyan]Uploading handoff metadata...[/]
[green]Handoff metadata created:[/] hnd_abc123def456

Git: feature/auth @ def789abc012 (dirty)
```

## Filtering by Agent

To list only Codex handoffs:

```bash
cheri handoff list --workspace team | grep codex
```

## Safety Notes

- Default secret-safe scanning is applied
- Credentials and keys are never uploaded
- `--include-sensitive` requires explicit confirmation
- Manifest is visible to all workspace members