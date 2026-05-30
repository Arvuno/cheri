# Task Automation Guide

Learn how to create and manage automated sync tasks with Cheri.

## What Are Tasks?

Tasks are persistent configurations that watch files or directories and automatically upload changes to your workspace. They run in the background and can monitor for changes or run on a schedule.

## Creating Tasks

### Interactive Mode

The easiest way to create a task:

```bash
cheri task create --interactive
```

This launches a guided wizard that helps you:
1. Choose a file or directory to watch
2. Select a workspace
3. Choose a sync mode
4. Configure patterns
5. Preview and create the task

### Command-Line Mode

For faster creation, use command-line arguments:

```bash
# Watch a directory for changes
cheri task create --directory ./notes --mode on-change

# Watch a file
cheri task create --file important.md --mode instant

# Watch with interval
cheri task create --directory ./backups --mode interval --every 1h
```

## Sync Modes

### on-change

Monitors files and uploads when they change.

```bash
cheri task create --directory ./docs --mode on-change
```

**Best for:**
- Source code directories
- Active documentation
- Project files under active development

### interval

Uploads on a fixed schedule regardless of changes.

```bash
cheri task create --directory ./backups --mode interval --every 30m
```

**Best for:**
- Periodic backups
- Status reports
- Scheduled snapshots

### instant

Uploads immediately when any change is detected.

```bash
cheri task create --file notes.md --mode instant
```

**Best for:**
- Single critical files
- Configuration files
- Quick feedback scenarios

### hybrid

Combines on-change detection with interval uploads as a safety net.

```bash
cheri task create --directory ./src --mode hybrid --every 15m
```

**Best for:**
- Important directories
- Balancing responsiveness with efficiency
- Missed change detection protection

## Task Options

### Target Selection

```bash
# Watch a specific directory
--directory ./path/to/dir

# Watch a specific file
--file ./path/to/file.txt

# Let Cheri find matching directories
cheri task create --directory myproject --pick
```

### Workspace

```bash
# Create in specific workspace
--workspace backend-api

# Create in active workspace (default)
```

### Patterns

```bash
# Include only certain files
--include "*.py"
--include "*.js"

# Exclude patterns
--exclude "*.log"
--exclude "__pycache__"
--exclude "*.pyc"
```

### Recursive Watching

```bash
# Watch subdirectories (default for directories)
--recursive

# Only watch top-level files
--no-recursive
```

### Debounce

Control how quickly Cheri reacts to changes:

```bash
# Default 3 seconds
--debounce 5
```

Lower values = faster response but more uploads.

### Starting Behavior

```bash
# Don't start watching immediately
--no-start

# Start watching immediately (default)
```

## Managing Tasks

### List Tasks

```bash
cheri task list
```

### Start/Stop Tasks

```bash
# Stop watching
cheri task stop task_abc123

# Resume watching
cheri task start task_abc123
```

### Run Immediately

```bash
# Run task now
cheri task run task_abc123

# Preview what would happen
cheri task run task_abc123 --dry-run
```

### Dry Run

See what would be uploaded without actually uploading:

```bash
cheri task dry-run task_abc123
```

This shows:
- Files that would be uploaded
- Files skipped due to secret-safe patterns
- Deleted paths ignored by upload-only mode

### Scan

View current file state without uploads:

```bash
cheri task scan task_abc123
```

This shows:
- Current snapshot status
- Changed files
- Deleted files
- Skipped sensitive files

### Task Logs

View history of task executions:

```bash
cheri task logs task_abc123
```

### Remove Tasks

```bash
cheri task remove task_abc123
```

## Background vs Foreground

### Background Watching

Runs continuously in the background:

```bash
cheri task create --directory ./src --mode on-change
# Automatically starts in background
```

### Foreground Watching

Run in terminal for debugging:

```bash
cheri task watch task_abc123
# Shows real-time output

# Watch all tasks
cheri task watch --all
```

## Secret-Safe Patterns

Cheri automatically excludes sensitive files:

```
.env, .env.*, *.env
credentials.json
*.key, *.pem
id_rsa, id_ed25519
.npmrc, .pypirc, .netrc
secrets.json, secret.json
```

These files are **never uploaded** even if they match your include patterns.

## Task Lifecycle

1. **Created** - Task is saved with configuration
2. **Idle** - Task is saved but not running
3. **Running** - Task is executing an upload
4. **Watching** - Task is monitoring for changes
5. **Stopped** - Task is paused
6. **Error** - Task encountered an error

## Best Practices

### Development Workflows

```bash
# Quick sync for active development
cheri task create --directory ./src --mode on-change

# Regular sync with filtering
cheri task create \
  --directory ./src \
  --mode hybrid \
  --every 30m \
  --include "*.py" \
  --include "*.js" \
  --exclude "*.pyc"
```

### Backup Workflows

```bash
# Hourly backup of important files
cheri task create \
  --directory ./important \
  --mode interval \
  --every 1h
```

### Documentation

```bash
# Watch docs folder
cheri task create \
  --directory ./docs \
  --mode on-change \
  --recursive
```

## Troubleshooting

### Task Not Starting

```bash
# Check task status
cheri task list

# Check for errors
cheri task logs task_abc123

# Verify workspace access
cheri workspace status
```

### No Uploads Happening

```bash
# Run manually to see output
cheri task run task_abc123 --dry-run

# Check if files actually changed
cheri task scan task_abc123
```

### Too Many Uploads

```bash
# Increase debounce
cheri task create ... --debounce 10

# Switch to interval mode
# (delete old task and create new)
```

## Examples

### Watch Source Code

```bash
cheri task create \
  --directory ~/projects/myapp \
  --mode on-change \
  --include "*.py" \
  --include "*.js" \
  --include "*.html" \
  --exclude "node_modules" \
  --exclude "__pycache__"
```

### Periodic Backup

```bash
cheri task create \
  --directory ./backups \
  --mode interval \
  --every 4h \
  --recursive
```

### Single File Monitoring

```bash
cheri task create \
  --file ./config/app.yaml \
  --mode instant
```

## Limitations

- Tasks are **upload-only** (no download from workspace)
- System provider resets daily
- Tasks require an active workspace
- Files must exist when task is created
