# Getting Started with Cheri

Cheri is a CLI-first workspace sync tool for developer teams. This guide will help you get up and running in under 5 minutes.

## Prerequisites

- Python 3.11 or higher
- pip package manager
- A backend API URL (defaults to `https://cheri.parapanteri.com`)

## Installation

Install Cheri globally from the repository:

```bash
pip install .
cheri --help
```

## First 5 Minutes

### 1. Initialize Cheri

Run the initialization wizard to set up your workspace:

```bash
cheri init
```

This will:
- Welcome you and check the backend API
- Ask you to register or log in
- Help you create or join a workspace
- Show your storage provider
- Offer to upload your first file or create a watch task

### 2. Check Your Configuration

Run the diagnostic command to verify everything is set up correctly:

```bash
cheri doctor
```

Expected output:
- All checks should pass (green checkmarks)
- Any warnings will be highlighted in yellow
- Critical failures will be shown in red

### 3. View Workspace Status

Check your current workspace and its state:

```bash
cheri workspace status
```

This shows:
- Active workspace name and ID
- Current user and role
- Storage provider and validation state
- Member and file counts
- Active tasks

### 4. Upload a File

Upload a file to your workspace:

```bash
cheri file upload README.md
```

Or upload an entire directory:

```bash
cheri file upload ./src
```

### 5. Create a Watch Task

Automate file syncing with a watch task:

```bash
cheri task create --interactive
```

The interactive wizard will guide you through:
- Choosing a file or directory to watch
- Selecting your workspace
- Choosing a sync mode (on-change, interval, instant, or hybrid)
- Configuring include/exclude patterns
- Previewing and creating the task

Or use direct command-line arguments:

```bash
cheri task create --directory ./notes --mode on-change
```

### 6. View Activity

Check recent uploads and changes:

```bash
cheri activity
```

## Common Commands

### Authentication

```bash
cheri register           # Create a new account
cheri login             # Log in with existing credentials
cheri logout            # Clear your session
```

### Workspace Management

```bash
cheri workspace list     # List accessible workspaces
cheri workspace status   # Show detailed workspace status
cheri workspace create --name myteam   # Create a workspace
cheri workspace join CHR-TEAM-8X2K91QZ  # Join via invite code
```

### File Operations

```bash
cheri file upload ./notes.md      # Upload a file
cheri file list                   # List workspace files
cheri file download notes.md      # Download a file
```

### Task Management

```bash
cheri task list                   # List all tasks
cheri task create --directory ./src --mode on-change  # Create a task
cheri task stop task_abc123       # Stop a task
cheri task start task_abc123      # Start a task
cheri task dry-run task_abc123    # Preview what would upload
cheri task scan task_abc123       # Show current file state
```

### Configuration

```bash
cheri config get           # Show current config
cheri config set api-url https://cheri.example.com  # Set API URL
cheri config check         # Verify backend connectivity
cheri config reset        # Reset to defaults
```

### Diagnostics

```bash
cheri doctor               # Run health checks
cheri doctor --json        # JSON output
cheri doctor --release-check  # Exit non-zero on issues
```

## Next Steps

- Read the [CLI Reference](CLI_REFERENCE.md) for complete command documentation
- See [Developer Team Workflows](DEVELOPER_TEAM_WORKFLOWS.md) for collaboration patterns
- Learn about [Task Automation](TASK_AUTOMATION_GUIDE.md) for advanced usage
- Run `cheri doctor` if you encounter any issues

## First-Time Setup Complete

You're now ready to use Cheri! Key points to remember:

- Cheri is **upload-only** in this version (no bidirectional sync)
- Your data is encrypted before upload
- Secret-safe patterns are automatically excluded (`.env`, `credentials.json`, etc.)
- Use `cheri doctor` to diagnose any issues
