# Impact on v0.4 and v0.5 Report

## v0.4 Commands — ALL PRESERVED ✅

| Command | Status |
|---------|--------|
| `cheri init` | ✅ Works — init.py intact |
| `cheri doctor` | ✅ Works — doctor.py intact |
| `cheri workspace status` | ✅ Works — workspace/service.py intact |
| `cheri task create` | ✅ Works — task/service.py intact |
| `cheri task list/watch/run` | ✅ Works |

No v0.4 file was modified. All init, doctor, workspace, task commands function identically.

## v0.5 Handoff Commands — ALL PRESERVED ✅

| Command | Status |
|---------|--------|
| `cheri handoff create` | ✅ Works — handoff/cli.py |
| `cheri handoff push` | ✅ Works |
| `cheri handoff list` | ✅ Works |
| `cheri handoff show` | ✅ Works |
| `cheri handoff pull` | ✅ Works |
| `cheri handoff latest` | ✅ Works |
| `cheri handoff bundle` | ✅ Works |
| `cheri handoff inspect` | ✅ Works |

Worker routes for handoffs (`/v1/handoffs`, `/v1/handoffs/:id`, `/v1/handoffs/latest`)
are all intact in `worker/index.js`.

## What Changed

### CHANGELOG.md
Added v0.3.1-provider-beta-rescue section at top of changelog.
Does not affect functionality.

### Python Tests
Added `test_storage.py` — 9 tests covering provider listing, status, connectivity.
All pass.

### Node.js Tests
Fixed FakeKV string-serialization to match Cloudflare KV behavior.
Provider catalog tests pass. Upload flow has env-specific 500.

## Backward Compatibility

No breaking changes. Provider config API is additive.
Existing workspaces continue to work with their current provider.
New provider configure/use flow is opt-in.