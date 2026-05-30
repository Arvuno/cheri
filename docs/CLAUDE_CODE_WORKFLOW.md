# Claude Code Workflow

This document describes how to use Cheri's handoff feature with Claude Code development sessions.

## Overview

Claude Code is Anthropic's CLI coding agent. After a Claude Code session, you can use `cheri handoff` to share the results with your team through a shared workspace.

## When to Use Handoff

Use `cheri handoff` when:

- Claude Code completed a feature or bug fix and you want to share the results
- You want to preserve implementation reports and artifacts for team review
- You need to hand off work to another developer or agent
- You want to build an evidence trail for audit or release purposes

## Workflow

### 1. Run Claude Code Session

```bash
cd ~/projects/myapp
claude
```

Claude Code works in the project directory. When done, it produces outputs like:

- Modified source files
- Implementation notes
- Generated documentation
- Test results

### 2. Create Handoff

After the Claude Code session, navigate to the output directory and create a handoff:

```bash
# Inspect what will be included
cheri handoff inspect ./output

# Create handoff and push to workspace
cheri handoff push ./output \
  --name "feature: user authentication" \
  --agent claude-code \
  --tool implementation \
  --tag feature-complete \
  --workspace team
```

### 3. Share with Team

```bash
# List the handoff to confirm
cheri handoff list

# Show details
cheri handoff latest
```

### 4. Team Member Reviews

```bash
# List recent handoffs
cheri handoff list

# Pull the latest to inspect
cheri handoff pull hnd_abc123def456 --dest ~/reviews/auth-feature

# Review the manifest
cat ~/reviews/auth-feature/cheri-handoff.json | jq .
```

## Example Session

```
$ cd ~/projects/myapp
$ claude
[Claude Code session running...]

$ cheri handoff push ./report_md \
    --name "v0.5 implementation report" \
    --agent claude-code \
    --tag release \
    --version-label "v0.5.0" \
    --workspace engineering

[cyan]Creating handoff for[/] /home/user/projects/myapp/report_md...
[green]Manifest written:[/] /home/user/projects/myapp/report_md/cheri-handoff.json
[cyan]Uploading handoff metadata...[/]
[green]Handoff metadata created:[/] hnd_7f3a9bc2d081

Git: main @ abc123def456 (dirty)
```

## Output Directories

Claude Code commonly produces output in these directories:

| Directory | Contents |
|-----------|----------|
| `report_md/` | Markdown implementation reports |
| `./` (root) | Modified source files |
| `docs/` | Generated documentation |
| `test-results/` | Test output and coverage |
| `build/` | Build artifacts (if applicable) |

Use `cheri handoff inspect <path>` to preview before pushing.

## Agent Metadata

The `--agent claude-code` flag sets the `agent_name` field in the manifest, making it easy to filter and identify Claude Code handoffs:

```bash
# List only Claude Code handoffs
cheri handoff list | grep claude-code

# Or use workspace filtering if supported
cheri handoff list --workspace engineering
```

## Safety Notes

- **Default secret-safe scanning**: `.env` files, credentials, and keys are never uploaded
- **Explicit confirmation for sensitive files**: If you use `--include-sensitive`, you'll be prompted before any sensitive files are included
- **Manifest is workspace-visible**: The manifest and metadata are stored in the shared workspace and visible to all workspace members

## Limitations

- Handoffs are upload-only; team members cannot push changes back through the same handoff
- For continuous sync of source code, use `cheri task` instead
- Large binary artifacts may take time to upload depending on storage provider