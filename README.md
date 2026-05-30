# Cheri

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white&style=flat-square)
![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Workers-F38020?logo=cloudflare&logoColor=white&style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Beta-orange?style=flat-square)

**CLI-first collaborative workspace sync tool**

*Shared workspaces · File transfer · Team invites · Activity history · Task-based local sync*

[Quick Start](#quick-start) · [Installation](#installation) · [Features](#features) · [Documentation](#documentation)

</div>

---

## What is Cheri?

Cheri is a CLI-first collaborative workspace sync tool for small teams. It provides a command-line workflow for:

| Feature | Description |
|---------|-------------|
| **Workspaces** | Create, join, and switch between workspaces |
| **File Sync** | Upload, download, and share files with team members |
| **Team Invites** | Generate short invite codes (e.g. `CHR-TEAM-8X2K91QZ`) |
| **Activity Feed** | Review recent team activity in real-time |
| **Task Automation** | Watch files/folders and auto-upload changes |

Built on **Cloudflare Workers** (API) + **KV** (metadata) + **R2** (blob storage).

## Current Status

| Ready | Limited |
|-------|---------|
| ✅ register / login / logout | ⚠️ Only `System (recommended)` is production-ready |
| ✅ workspace create / list / use / join | ⚠️ S3, Google Drive, B2 are scaffolded |
| ✅ file upload / download / list | ⚠️ Upload-only sync (no bidirectional yet) |
| ✅ team invite / list / invite-reset | ⚠️ No conflict resolution |
| ✅ activity feed | ⚠️ No bidirectional sync |
| ✅ task create / list / start / stop / run / logs / watch | |

## Quick Start

```bash
# 1. Install
git clone https://github.com/Arvuno/cheri.git
cd cheri
python -m pip install .

# 2. Configure
cheri config get
cheri config check

# 3. Register and create workspace
cheri register
cheri workspace create --name my-team
cheri workspace use my-team

# 4. Start syncing
cheri file upload ./notes.md
cheri file list
cheri activity
```

## Installation

### Requirements

- **Python** 3.9+
- **pip** package manager
- **Node.js** 18+ (for Worker test suite)
- **Wrangler** (for self-hosting the backend)

### Install from Repo

```bash
git clone https://github.com/Arvuno/cheri.git
cd cheri
python -m pip install .
cheri --help
```

Windows:
```powershell
py -3 -m pip install .
cheri --help
```

> **Note:** If `cheri` is not found after install, open a new shell or ensure your Python scripts directory is on `PATH`.

## Features

### Core Commands

| Command | Description |
|---------|-------------|
| `cheri register` / `login` / `logout` | Authentication |
| `cheri workspace create` / `list` / `use` / `join` | Workspace management |
| `cheri file upload` / `download` / `list` | File operations |
| `cheri teams invite` / `list` / `invite-reset` | Team collaboration |
| `cheri activity` | View team activity feed |
| `cheri task create` / `list` / `start` / `stop` / `run` / `logs` / `watch` | Task automation |

### Invite / Collaboration Flow

**User A:**
```bash
cheri register
cheri workspace create --name docs
cheri workspace use docs
cheri teams invite
# Output: CHR-TEAM-8X2K91QZ
```

**User B:**
```bash
cheri register
cheri workspace join CHR-TEAM-8X2K91QZ
cheri workspace list
cheri teams list
```

### Task / Folder Sync

```bash
# Create a sync task that watches for changes
cheri task create --directory cheri_test_files --mode on-change

# Or with an interval
cheri task create --file notes.md --mode interval --every 10m

# Manage tasks
cheri task list
cheri task stop <task-id>
cheri task start <task-id>
cheri task logs <task-id>
```

## Architecture

```
┌─────────────────────────────────────────────┐
│                 CLI Client                   │
│         Python (cheri_cloud_cli/)            │
│  • Auth · File transfer · Task automation   │
└────────────────────┬────────────────────────┘
                     │  HTTPS
┌────────────────────▼────────────────────────┐
│              Worker API Backend              │
│            Cloudflare Workers               │
│  • Auth · Workspaces · Files · Activity     │
└──────┬───────────────────────────┬───────────┘
       │ KV                       │ R2
       ▼                           ▼
  ┌─────────┐                ┌──────────┐
  │ Metadata│                │  Blobs   │
  └─────────┘                └──────────┘
```

## Backend Configuration

The CLI resolves the backend URL in this order:

1. `CHERI_API_URL` environment variable
2. `CHERI_WORKER_URL` environment variable
3. Saved local CLI config
4. Embedded public defaults

```bash
# Check current config
cheri config get

# Set custom backend
cheri config set api-url https://your-worker.workers.dev

# Reset to defaults
cheri config reset
cheri config check
```

## Documentation

### Development

```bash
# Repo structure
cheri_cloud_cli/   # Python CLI implementation
worker/            # Cloudflare Worker API
docs/              # Product documentation
guide/             # Static guide UI
tests/             # Python & Worker tests
scripts/           # Helper scripts

# Run tests
node tests/node/worker.test.mjs
python -m unittest discover -s tests/python -p "test_*.py"
npm test

# Deploy backend
wrangler deploy
```

### Self-Hosting

1. Create a Cloudflare KV namespace
2. Create an R2 bucket
3. Update `wrangler.toml`:
   - Set KV namespace ID
   - Set bucket name
   - Update route pattern
4. Deploy:
   ```bash
   wrangler deploy
   ```

Required bindings: `HERMES_KV`, `HERMES_BUCKET`

## Known Limitations

| Limitation | Impact |
|------------|--------|
| Only `System (recommended)` is production-ready | Limited storage provider options |
| Upload-only sync | No bidirectional/remote delete reconciliation |
| No conflict resolution | Manual conflict handling required |
| Local secret storage not encrypted at rest | Security consideration for shared machines |
| Bootstrap secret not an invite code | Different purposes in the auth flow |

## Security Notes

Cheri stores local state in a user-level config directory, **not** in the repo.

**Never commit:**
- `credentials.json`
- `.env` local overrides
- Bootstrap secrets
- Session tokens
- `.wrangler/` local state

## License

This project is distributed under the MIT License.