# Developer Team Workflows

Patterns for using Cheri effectively in developer teams.

## Overview

Cheri enables developer teams to:
- Share files across team members via a shared workspace
- Automate uploads with watch tasks
- Maintain a centralized file history
- Control access via invite codes

## Common Workflows

### 1. Team Setup

When a new team member joins:

```bash
# Receive invite code from team lead
cheri login
cheri workspace join CHR-TEAM-8X2K91QZ
cheri workspace status
```

### 2. Project Collaboration

For ongoing project collaboration:

```bash
# Create a project-specific workspace
cheri workspace create --name backend-api

# Upload project files
cheri file upload ./docs
cheri file upload ./specs

# Set up automated sync for documentation
cheri task create --directory ./docs --mode on-change --workspace backend-api

# Invite team members
cheri teams invite --label backend-docs
# Share the invite code with team
```

### 3. File Sharing

Sharing files with team members:

```bash
# Upload and share
cheri file upload ./release-notes.md

# Check what's available
cheri file list

# Download shared files
cheri file download release-notes.md --dest ./
```

### 4. Automated Backups

Setting up automated backups for important directories:

```bash
# Create interval-based backup task
cheri task create \
  --directory ./important-files \
  --mode interval \
  --every 1h \
  --recursive

# Monitor task status
cheri task list
cheri task logs task_abc123
```

### 5. Development Workflow

For development teams wanting to sync code:

```bash
# Create task for source directory
cheri task create \
  --directory ./src \
  --mode on-change \
  --include "*.py" \
  --include "*.js" \
  --exclude "*.pyc" \
  --exclude "__pycache__"

# Run immediate sync before meetings
cheri task run task_abc123

# Check what changed
cheri activity
```

## Workspace Strategies

### Single Workspace

Best for small teams or simple setups:

```bash
cheri workspace create --name team
# All files go here
```

### Multiple Workspaces

For larger organizations with separate concerns:

```bash
# Create separate workspaces
cheri workspace create --name docs
cheri workspace create --name backend
cheri workspace create --name frontend

# Switch between them as needed
cheri workspace use docs
cheri workspace use backend
```

## Invite and Access Management

### Creating Invites

```bash
# Basic invite
cheri teams invite

# With label for tracking
cheri teams invite --label q4-contractors

# List active invites
cheri teams list
```

### Rotating Invites

For security, rotate invite codes periodically:

```bash
# Reset and create new invite
cheri teams invite-reset --new --label new-access
```

## Task Modes Explained

### on-change

Uploads when files are modified. Best for:
- Active development directories
- Quick feedback loops

```bash
cheri task create --directory ./src --mode on-change
```

### interval

Uploads on a schedule. Best for:
- Periodic backups
- Reducing bandwidth

```bash
cheri task create --directory ./backups --mode interval --every 30m
```

### instant

Uploads immediately when files change. Best for:
- Critical files
- Small, important documents

```bash
cheri task create --file notes.md --mode instant
```

### hybrid

Combines interval and on-change. Best for:
- Balance between responsiveness and efficiency

```bash
cheri task create --directory ./docs --mode hybrid --every 15m
```

## Security Notes

### Secret-Safe Patterns

Cheri automatically excludes sensitive files:
- `.env`, `.env.*`, `*.env`
- `credentials.json`
- `*.key`, `*.pem`
- `id_rsa`, `id_ed25519`
- `.npmrc`, `.pypirc`, `.netrc`
- `secrets.json`, `secret.json`

These files are **never uploaded** regardless of task configuration.

### Best Practices

1. **Use workspace-specific invite codes** - Rotate periodically
2. **Monitor active tasks** - `cheri task list`
3. **Review activity** - `cheri activity`
4. **Run diagnostics** - `cheri doctor --release-check` in CI

## Team Collaboration Tips

1. **Establish naming conventions** for workspaces
2. **Use labels on invites** to track who has access
3. **Set up tasks with descriptive names** via comments
4. **Regular health checks** with `cheri doctor`
5. **Review activity feed** to stay aware of team changes

## Limitations

- Cheri is **upload-only** in this version
- No bidirectional sync (changes don't download from workspace)
- System provider resets daily
- Review `cheri doctor` warnings for configuration issues
