# Agent Handoff Workflows

Cheri's agent artifact handoff feature enables developer teams — and AI coding agents like Claude Code and Codex — to share reports, logs, build outputs, screenshots, generated docs, and AI deliverables through workspace-based CLI flows.

## Why Agent Handoff?

When working in a collaborative development environment, especially with AI coding agents:

1. **Context Transfer**: A human or agent can hand off a working context to another human or agent without repeating all prior work.
2. **Evidence Trails**: Build outputs, test results, and generated artifacts are preserved for audit and review.
3. **Team Visibility**: Shared handoffs appear in workspace feed, making artifacts visible to the whole team.

## Core Commands

```bash
# Inspect a path (dry-run) — see what would be included/skipped
cheri handoff inspect ./reports

# Create a local handoff manifest (no upload)
cheri handoff create ./reports --name "v0.4 implementation"

# Push to workspace (creates manifest + uploads safe files)
cheri handoff push ./reports --name "v0.4 implementation" --workspace myteam

# List workspace handoffs
cheri handoff list

# Show a specific handoff
cheri handoff show hnd_abc123def456

# Download handoff to local folder
cheri handoff pull hnd_abc123def456

# Get the latest handoff
cheri handoff latest

# Create a compressed bundle
cheri handoff bundle ./output --name "build artifacts"
```

## Agent-Specific Options

All `create` and `push` commands support:

```bash
--agent claude-code        # Tag the agent type
--agent codex              # Tag the agent type
--tool <name>             # Tag the specific tool that generated artifacts
--version-label <label>    # Tag a version (e.g., v0.4.0, release-candidate)
--tag <tag>               # Add custom tags (can be repeated)
```

## Safety Model

### Secret-Safe Scanning

By default, Cheri excludes sensitive files from handoffs:

- `.env`, `.env.*`, `*.env`
- `credentials.json`, `secrets.json`, `secret.json`
- `*.key`, `*.pem` (private keys and certificates)
- `id_rsa`, `id_ed25519` (SSH keys)
- `.npmrc`, `.pypirc`, `.netrc` (auth config files)

This behavior matches the task scanning exclusion patterns.

### Including Sensitive Files

If you need to include sensitive files (not recommended for shared workspaces):

```bash
cheri handoff push ./config --name "config bundle" --include-sensitive
```

You will be prompted for explicit confirmation. The action is logged.

### What Gets Uploaded

The handoff manifest (`cheri-handoff.json`) is always uploaded alongside file metadata. File content upload uses the existing storage provider abstraction.

### Upload Storage Namespace

Files are stored under the `handoffs/{handoff_id}/` namespace in workspace storage. The manifest itself is uploaded as a handoff file and referenced by `manifest_file_id` in the handoff record.

### Partial Failure Behavior

During `cheri handoff push`, if a file fails to upload:
- The push operation continues processing remaining files
- The failed file is marked with `"upload_status": "partial_failed"` in the manifest
- Overall handoff status is set to `"partial_failed"` if any file failed
- Files that succeeded retain their `file_id` and `storage_key`

### Pull and Checksum Verification

During `cheri handoff pull`:
- Actual file content is downloaded from workspace storage to the destination folder
- Original directory structure is reconstructed under the destination path
- If a manifest checksum is available for a file, the downloaded content is verified against it
- Files with missing checksums or failed verification are flagged but do not block other files
- Pull continues on partial failure, marking individual file failures in output

### Secret-Safe Exclusions During Push

The secret-safe exclusion patterns continue to apply during push. Files matching these patterns are listed in `skipped_sensitive` but their content is never read or uploaded.

## Git Context Detection

When the source path is inside a Git repository, Cheri automatically captures:

- Branch name
- Commit hash (short form)
- Dirty status (uncommitted changes)
- Remote URL (redacted if credentials are embedded)

This helps recipients understand the exact state of the artifacts they receive.

## Workflow Examples

### Claude Code Handoff

```bash
# After completing a feature implementation
cd ~/projects/myapp

# Run your agent (Claude Code completes work)
# Then package the results for the team

cheri handoff push ./report_md \
  --name "feature implementation report" \
  --agent claude-code \
  --tool implementation \
  --tag feature-complete \
  --workspace team
```

### Codex Handoff

```bash
cheri handoff push ./codex-output \
  --name "codex session artifacts" \
  --agent codex \
  --version-label "session-2026-05-30" \
  --workspace team
```

### Release Evidence

```bash
cheri handoff push ./release-artifacts \
  --name "v0.5.0 release" \
  --agent claude-code \
  --tag release \
  --version-label "v0.5.0"
```

### Receiving a Handoff

```bash
# List recent handoffs
cheri handoff list

# Download and inspect
cheri handoff pull hnd_abc123def456 --dest ./incoming

# Inspect locally
cd ./incoming
cat cheri-handoff.json | jq .
```

## Manifest Schema

The `cheri-handoff.json` manifest contains:

- `schema_version` — manifest format version
- `handoff_id` — unique identifier
- `name` / `description` / `tags`
- `generated_at` — ISO timestamp
- `source_path` — original path
- `git_context` — branch, commit, dirty, remote (if applicable)
- `files` — array of included files with path, size, checksum, content type
- `skipped_sensitive` — list of excluded file names (no content)
- `agent_name` / `tool_name` / `version_label` — agent metadata

See [HANDOFF_MANIFEST.md](./HANDOFF_MANIFEST.md) for the full schema specification.

## Limitations

- **No merge or conflict resolution**: If you pull a handoff to a directory with existing files, no merge or conflict resolution is performed.
- **No real-time sync**: Handoffs are discrete artifacts, not continuous sync sessions. Use `cheri task` for continuous sync.

## See Also

- [HANDOFF_MANIFEST.md](./HANDOFF_MANIFEST.md) — manifest schema
- [CLAUDE_CODE_WORKFLOW.md](./CLAUDE_CODE_WORKFLOW.md)
- [CODEX_WORKFLOW.md](./CODEX_WORKFLOW.md)
- [RELEASE_EVIDENCE_WORKFLOW.md](./RELEASE_EVIDENCE_WORKFLOW.md)