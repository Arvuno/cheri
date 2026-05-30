# Handoff Commands Report

## Implementation Summary

Eight CLI commands were implemented for the `cheri handoff` group.

## Command Details

### `cheri handoff create`

**Purpose**: Create a local handoff manifest without uploading.

**Signature**:
```bash
cheri handoff create <path> --name <name>
  [--description <text>]
  [--tag <tag>]...
  [--agent <agent-name>]
  [--tool <tool-name>]
  [--version-label <label>]
  [--include-sensitive]
```

**Behavior**:
1. Validates the path exists
2. Prompts for confirmation if `--include-sensitive` not set (secret-safe scanning enabled)
3. Scans the directory/file using `scan_directory()`
4. Generates `cheri-handoff.json` manifest
5. Writes manifest to the source directory
6. Displays summary with handoff ID, file count, skipped count, git context

**Exit codes**: 0 on success, 1 on error (path not found, permission denied)

---

### `cheri handoff push`

**Purpose**: Create manifest and upload safe files to a workspace.

**Signature**:
```bash
cheri handoff push <path> --name <name>
  [--workspace <workspace-id-or-name>]
  [--description <text>]
  [--tag <tag>]...
  [--agent <agent-name>]
  [--tool <tool-name>]
  [--version-label <label>]
  [--include-sensitive]
```

**Behavior**:
1. Validates the path exists
2. Confirms secret-safe scanning (unless `--include-sensitive`)
3. Creates manifest (same as `create`)
4. Writes manifest locally
5. Calls `POST /v1/handoffs` to create backend metadata
6. Shows confirmation with handoff ID

**Exit codes**: 0 on success, 1 on error (no active workspace, backend unreachable)

---

### `cheri handoff list`

**Purpose**: List recent handoffs in the active workspace.

**Signature**:
```bash
cheri handoff list [--workspace <workspace-id-or-name>]
```

**Behavior**:
1. Resolves workspace (active or specified)
2. Calls `GET /v1/handoffs`
3. Displays table with: ID, Name, Files, Size, Agent, Created

**Output**: Rich table or JSON (if `--json` added)

---

### `cheri handoff show`

**Purpose**: Show metadata and file list for a specific handoff.

**Signature**:
```bash
cheri handoff show <handoff-id>
```

**Behavior**:
1. Calls `GET /v1/handoffs/<handoff-id>`
2. Displays full metadata in a Panel
3. Shows file list table (up to 50 files)
4. Shows git context if available

---

### `cheri handoff pull`

**Purpose**: Download handoff files to a local folder.

**Signature**:
```bash
cheri handoff pull <handoff-id> [--dest <directory>]
```

**Behavior**:
1. Calls `GET /v1/handoffs/<handoff-id>`
2. Creates destination directory (default: `./handoff-<id[:8]>`
3. Confirms if directory exists and not empty
4. Writes manifest JSON
5. Shows note that file content download requires storage provider integration

**Note**: Full file content download via storage provider is planned for future versions.

---

### `cheri handoff latest`

**Purpose**: Show the most recent handoff for the workspace.

**Signature**:
```bash
cheri handoff latest [--workspace <workspace-id-or-name>]
```

**Behavior**:
1. Calls `GET /v1/handoffs/latest`
2. Delegates to `show_handoff()` for display

---

### `cheri handoff bundle`

**Purpose**: Create a compressed tar.gz archive of a path.

**Signature**:
```bash
cheri handoff bundle <path> --name <name> [--include-sensitive]
```

**Behavior**:
1. Scans path with secret-safe scanning
2. Creates `tar.gz` archive
3. Embeds manifest in archive as `cheri-handoff.json`
4. Adds files from scan results

**Output file**: `{name}-{handoff-id[:8]}.tar.gz`

---

### `cheri handoff inspect`

**Purpose**: Dry-run scan showing included/skipped files.

**Signature**:
```bash
cheri handoff inspect <path>
```

**Behavior**:
1. Scans path without uploading
2. Shows count of included files and skipped sensitive files
3. Lists skipped file names (no content)
4. Shows git context if available

**Use case**: Preview what a handoff would include without creating anything.

---

## Error Handling

All commands use standardized error messages with:
- What failed
- Likely cause
- Suggested fix
- Recovery command (when applicable)

Example:
```
Error: Path not found: ./reports
Cheri could not find the path you specified.

Likely cause: The directory does not exist or you don't have read permissions.

Suggested fix: Verify the path exists and you have access.

Recovery command: ls -la ./reports
```

## Option Consistency

| Option | create | push | list | show | pull | latest | bundle | inspect |
|--------|--------|------|------|------|------|--------|--------|---------|
| `--name` | ✅ | ✅ | | | | | ✅ | |
| `--workspace` | | ✅ | ✅ | | | ✅ | | |
| `--description` | ✅ | ✅ | | | | | | |
| `--tag` | ✅ | ✅ | | | | | | |
| `--agent` | ✅ | ✅ | | | | | | |
| `--tool` | ✅ | ✅ | | | | | | |
| `--version-label` | ✅ | ✅ | | | | | | |
| `--include-sensitive` | ✅ | ✅ | | | | | ✅ | |
| `--dest` | | | | | ✅ | | | |

## Verification

Commands can be verified with:
```bash
python -m cheri_cloud_cli.cli handoff inspect reports
python -m cheri_cloud_cli.cli handoff create reports --name test-handoff
```