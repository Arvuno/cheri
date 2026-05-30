# Cheri Init Flow

Documentation of the `cheri init` initialization wizard.

## Overview

`cheri init` walks new users through setting up Cheri for the first time. It provides a guided, interactive experience that can also run non-interactively.

## Interactive Flow

### Step 1: Welcome Panel

```
╔══════════════════════════════════════════════════════════════════╗
║                    Welcome to Cheri                              ║
║                                                                  ║
║  Cheri — CLI-first workspace sync for developer teams            ║
║                                                                  ║
║  Sync files and automate uploads across your team.               ║
║  All uploads are encrypted and stored securely.                ║
╚══════════════════════════════════════════════════════════════════╝
```

### Step 2: API URL Check

The wizard checks the backend API URL:
- Default: `https://cheri.parapanteri.com`
- User can accept default or provide custom URL

```
✓ Backend API: https://cheri.parapanteri.com
```

If unreachable:
```
! Backend API: https://cheri.parapanteri.com (not reachable)
  This may affect some features. Run 'cheri doctor' to diagnose.
```

### Step 3: Authentication

The wizard checks if you're already logged in.

**If logged in:**
```
✓ Logged in as: alice
Continue with this account? [Y/n]
```

**If not logged in:**

Choose an action:
1. Register new account
2. Login with bootstrap secret
3. Skip (some features unavailable)

#### Register Flow

1. Enter username
2. Enter workspace name (default: `{username} workspace`)
3. Select storage provider
4. Account created
5. **Bootstrap secret displayed** (save securely!)
6. Save credentials locally? [Y/n]
7. Also save bootstrap secret for future logins? [y/N]

```
╔══════════════════════════════════════════════════════════════════╗
║                    Bootstrap Secret                              ║
║                                                                  ║
║  amber anchor apple atlas bamboo beacon berry birch              ║
║  candle cedar cloud cobalt                                       ║
║                                                                  ║
║  Save this securely. You will need it to log in on other        ║
║  devices.                                                        ║
╚══════════════════════════════════════════════════════════════════╝
```

#### Login Flow

1. Enter username
2. Have bootstrap secret? [Y/n]
3. Enter bootstrap secret
4. Login attempted
5. Save credentials? [Y/n]

### Step 4: Workspace Selection

After authentication:

**If no workspace exists:**
```
Choose an action:
1. Create a new workspace
2. Join via invite code
3. Skip (can do later)
```

**If workspace exists:**
```
✓ Active workspace: myworkspace
Create or join another workspace? [y/N]
```

#### Create Workspace

1. Enter workspace name
2. Select storage provider
3. Workspace created and set as active

```
✓ Created workspace: myworkspace
```

#### Join Workspace

1. Enter invite code (e.g., CHR-TEAM-8X2K91QZ)
2. Join attempted
3. Workspace joined and set as active

```
✓ Joined workspace via invite code
```

### Step 5: Storage Provider Info

Shows the configured storage provider:

```
✓ Storage provider: System (recommended) (ready)
```

### Step 6: Upload Offer

```
Upload a file now? [y/N]
```

If yes:
1. Enter file path
2. File uploaded
3. Confirmation shown

### Step 7: Task Creation Offer

```
Create a watch task for automatic uploads? [y/N]
```

If yes:
```
Run 'cheri task create --interactive' to create a task.
```

### Step 8: Success Screen

```
╔══════════════════════════════════════════════════════════════════╗
║                   Cheri Initialized                             ║
║                                                                  ║
║  Logged in as    : alice                                        ║
║  Active workspace: myworkspace                                  ║
║                                                                  ║
║  Next steps:                                                    ║
║                                                                  ║
║    cheri workspace status    View workspace information          ║
║    cheri file upload <path>   Upload a file                     ║
║    cheri task create --interactive  Create a watch task        ║
║    cheri activity           View recent activity                ║
║    cheri doctor              Diagnose configuration              ║
╚══════════════════════════════════════════════════════════════════╝
```

## Non-Interactive Mode

For scripting and automation:

```bash
cheri init --non-interactive
cheri init --non-interactive --workspace myteam
cheri init --non-interactive --skip-upload --skip-task
cheri init --non-interactive --api-url https://cheri.example.com
cheri init --non-interactive --register
```

### Flags

| Flag | Description |
|------|-------------|
| `--non-interactive` | Run without prompts |
| `--skip-upload` | Skip upload offer |
| `--skip-task` | Skip task creation offer |
| `--workspace <name>` | Workspace name to create or use |
| `--api-url <url>` | API URL to use |
| `--register` | Force registration flow |

### Behavior in Non-Interactive Mode

| Step | Interactive | Non-Interactive |
|------|-------------|-----------------|
| Welcome | Shown | Shown |
| API URL | Prompted if no config | Uses default or `--api-url` |
| Auth | Prompted | Skipped if already logged in |
| Workspace | Prompted | Uses `--workspace` or skips |
| Upload | Prompted | Skipped |
| Task | Prompted | Skipped |

## Safety Checks

### Existing Config Protection

If config already exists:
- Does not overwrite without confirmation
- Offers to use existing session

### Error Handling

If any step fails:
1. Error is displayed clearly
2. Recovery command is shown
3. Init can be re-run safely

Example error recovery:
```
! Registration failed: Invalid username

Recovery: Run 'cheri doctor' to diagnose the issue.
```

## Skip Flags Explained

### `--skip-upload`

Skips the "Upload a file now?" prompt.

Useful for:
- Batch setup scripts
- When you know what you'll upload later

### `--skip-task`

Skips the "Create a watch task?" prompt.

Useful for:
- Initial setup without immediate automation
- Planning to configure tasks manually later

### Combining Flags

```bash
# Minimal setup
cheri init --non-interactive --skip-upload --skip-task

# With workspace pre-selected
cheri init --non-interactive --workspace myteam

# Full automated setup
cheri init --non-interactive --workspace myteam --api-url https://cheri.example.com
```

## Re-Running Init

`cheri init` can be run multiple times safely:
- Does not reset existing configuration
- Offers to continue with existing session
- Can be used to add workspace or configure more settings

## Manual Alternative

If you prefer manual setup:

```bash
# 1. Check config
cheri config get
cheri config check

# 2. Register or login
cheri register
# or
cheri login

# 3. Create or join workspace
cheri workspace create --name myteam
# or
cheri workspace join INVITE-CODE

# 4. Start using Cheri
cheri workspace status
cheri file upload ./notes.md
```
