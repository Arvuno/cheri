# Cheri CLI Reference

Complete reference for all Cheri CLI commands.

## Global Options

```
--help    Show help for any command
--version Show Cheri version
```

## init

Initialize Cheri and walk through first-time setup.

```bash
cheri init [OPTIONS]
```

**Options:**
- `--non-interactive` - Run without interactive prompts
- `--skip-upload` - Skip the upload offer
- `--skip-task` - Skip the task creation offer
- `--workspace <name>` - Workspace name to create or use
- `--api-url <url>` - Backend API URL to use
- `--register` - Force registration flow

**Examples:**
```bash
cheri init
cheri init --workspace myteam
cheri init --non-interactive --skip-upload --skip-task
```

---

## register

Create a new account and workspace.

```bash
cheri register
```

**Examples:**
```bash
cheri register
```

---

## login

Sign in with your bootstrap secret.

```bash
cheri login [OPTIONS]
```

**Options:**
- `--invite <code>` - Optional team invite code to accept after login
- `--force` - Ignore saved local session and sign in again

**Examples:**
```bash
cheri login
cheri login --invite CHR-TEAM-8X2K91QZ
cheri login --force
```

---

## logout

Clear the local session.

```bash
cheri logout
```

---

## doctor

Run diagnostic checks to verify your Cheri installation.

```bash
cheri doctor [OPTIONS]
```

**Options:**
- `--json` - Output results as JSON
- `--release-check` - Exit non-zero on critical issues

**Examples:**
```bash
cheri doctor
cheri doctor --json
cheri doctor --release-check
```

**Checks performed:**
- CLI version
- Python version
- Config directory permissions
- Keyring availability
- Backend API URL
- Backend health
- Auth session state
- Active workspace
- Storage provider status
- Task registry state
- Secret-safe exclude patterns
- Local write permissions
- Environment variables

---

## config

Show and change local CLI settings.

```bash
cheri config [COMMAND]
```

**Commands:**
- `cheri config get` - Show current backend settings
- `cheri config set api-url <url>` - Set the backend API URL
- `cheri config reset` - Clear the saved API URL
- `cheri config check` - Verify backend connectivity

**Examples:**
```bash
cheri config get
cheri config set api-url https://cheri.parapanteri.com
cheri config check
```

---

## workspace

Manage workspaces.

```bash
cheri workspace [COMMAND]
```

**Commands:**
- `cheri workspace status` - Show detailed workspace status
- `cheri workspace list` - List accessible workspaces
- `cheri workspace create --name <name>` - Create a workspace
- `cheri workspace use <id-or-name>` - Switch active workspace
- `cheri workspace join <invite-code>` - Join via invite code

**Options for status command:**
- `--json` - Output results as JSON

**Examples:**
```bash
cheri workspace status
cheri workspace status --json
cheri workspace list
cheri workspace create --name docs
cheri workspace use docs
cheri workspace join CHR-TEAM-8X2K91QZ
```

---

## file

Upload, download, and list files.

```bash
cheri file [COMMAND]
```

**Commands:**
- `cheri file upload <path>` - Upload a file or directory
- `cheri file download <file-or-id>` - Download a file
- `cheri file list` - List workspace files

**Options:**
- `--workspace <id-or-name>` - Target workspace (optional)

**Examples:**
```bash
cheri file upload ./notes.md
cheri file upload ./src
cheri file download notes.md
cheri file list
```

---

## teams

Manage team invites and members.

```bash
cheri teams [COMMAND]
```

**Commands:**
- `cheri teams invite` - Create an invite code
- `cheri teams list` - Show members and invite state
- `cheri teams invite-reset` - Revoke and rotate invite codes

**Options:**
- `--workspace <id-or-name>` - Target workspace (optional)

**Examples:**
```bash
cheri teams invite
cheri teams invite --label contractor
cheri teams list
cheri teams invite-reset --new --label new-access
```

---

## activity

Show recent workspace changes.

```bash
cheri activity [OPTIONS]
```

**Options:**
- `--workspace <id-or-name>` - Target workspace (optional)

**Examples:**
```bash
cheri activity
cheri activity --workspace docs
```

---

## task

Create and manage sync tasks.

```bash
cheri task [COMMAND]
```

**Commands:**
- `cheri task create` - Create a sync task
- `cheri task find <query>` - Find a file or directory target
- `cheri task list` - List saved sync tasks
- `cheri task start <task-id>` - Start background watching
- `cheri task stop <task-id>` - Stop background watching
- `cheri task remove <task-id>` - Remove a task
- `cheri task run <task-id>` - Run a task immediately
- `cheri task logs <task-id>` - Show task logs
- `cheri task watch [task-id]` - Watch tasks in foreground
- `cheri task dry-run <task-id>` - Preview what would upload
- `cheri task scan <task-id>` - Show current file state

### task create

```bash
cheri task create [OPTIONS]
```

**Options:**
- `--file <path>` - Watch a single file
- `--directory <path>` - Watch a directory
- `--workspace <id-or-name>` - Target workspace
- `--mode [interval|on-change|instant|hybrid]` - Sync mode
- `--every <interval>` - Interval (e.g., 10m, 30s, 1h)
- `--no-start` - Create task without starting watcher
- `--pick` - Show selection list for matching targets
- `--interactive` - Guided interactive task creation
- `--recursive/--no-recursive` - Watch subdirectories (default: true)
- `--include <pattern>` - Include pattern (can be repeated)
- `--exclude <pattern>` - Exclude pattern (can be repeated)

**Examples:**
```bash
cheri task create --directory ./notes --mode on-change
cheri task create --file notes.md --mode interval --every 10m
cheri task create --interactive
```

### task find

```bash
cheri task find <query> [OPTIONS]
```

**Options:**
- `--file` - Search for a file target
- `--directory` - Search for a directory target (default)

**Examples:**
```bash
cheri task find notes.md --file
cheri task find myfolder --directory
```

### task run

```bash
cheri task run <task-id> [OPTIONS]
```

**Options:**
- `--dry-run` - Show sync decisions without uploading

**Examples:**
```bash
cheri task run task_abc123
cheri task run task_abc123 --dry-run
```

### task dry-run

Show files that would be uploaded without uploading.

```bash
cheri task dry-run <task-id>
```

**Examples:**
```bash
cheri task dry-run task_abc123
```

### task scan

Show current snapshot/diff state without uploading.

```bash
cheri task scan <task-id>
```

**Examples:**
```bash
cheri task scan task_abc123
```

### task watch

```bash
cheri task watch [task-id] [OPTIONS]
```

**Options:**
- `--all` - Watch all enabled tasks
- `--dry-run` - Show sync decisions without uploading

**Examples:**
```bash
cheri task watch task_abc123
cheri task watch --all
cheri task watch --all --dry-run
```

---

## storage

Manage storage providers.

```bash
cheri storage [COMMAND]
```

**Commands:**
- `cheri storage providers` - List available storage providers
- `cheri storage status` - Show active storage provider
- `cheri storage check` - Verify storage connectivity
- `cheri storage configure` - Set storage provider
- `cheri storage migrate plan` - Plan storage migration
- `cheri storage migrate dry-run` - Dry-run storage migration

**Options:**
- `--workspace <id-or-name>` - Target workspace (optional)
- `--include-experimental` - Show experimental providers

**Examples:**
```bash
cheri storage providers
cheri storage status
cheri storage configure --provider system
cheri storage migrate plan --to s3-compatible
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CHERI_API_URL` | Backend API URL override |
| `CHERI_WORKER_URL` | Worker URL override |
| `CHERI_CONFIG_DIR` | Config directory override |
| `CHERI_PROVIDER_SECRET_KEY` | Secret encryption key (do not export!) |
