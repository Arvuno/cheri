# Cheri Doctor Command

Diagnostic tool for verifying your Cheri installation and configuration.

## Overview

`cheri doctor` runs a series of health checks to verify that Cheri is properly configured and can connect to required services.

## Usage

```bash
cheri doctor           # Human-readable output
cheri doctor --json    # JSON output for scripting
cheri doctor --release-check  # Exit non-zero on critical issues
```

## Health Checks

### 1. CLI Version

Verifies Cheri CLI is installed and shows the version.

**Pass criteria:** Cheri CLI version is displayed.

### 2. Python Version

Checks Python interpreter version.

**Pass criteria:** Python 3.11 or higher.

### 3. Config Directory

Verifies Cheri's configuration directory exists and has correct permissions.

**Pass criteria:**
- Directory exists at expected location
- Directory is writable
- Permissions are secure (mode 700 or appropriate)

**Locations:**
- Linux: `~/.config/cheri/`
- macOS: `~/Library/Application Support/Cheri/`
- Windows: `%APPDATA%\Cheri\`

### 4. Keyring

Checks for OS keychain availability for secure credential storage.

**Pass criteria:** Keyring is available with a non-null backend.

**Warning criteria:** Keyring available but using null/fallback backend.

### 5. Backend API URL

Verifies the backend API URL is configured.

**Pass criteria:** API URL is set (from settings or defaults).

### 6. Backend Health

Checks if the backend API is reachable.

**Pass criteria:** Backend responds to health check.

**Fails if:** Backend is unreachable or returns an error.

### 7. Auth Session

Checks if there is a valid saved session.

**Pass criteria:** Session token exists and is valid.

**Fails if:** No saved session or token missing.

### 8. Active Workspace

Checks if there is an active workspace selected.

**Pass criteria:** Active workspace is set.

**Warning criteria:** No active workspace (use `cheri workspace create` or `cheri workspace join`).

### 9. Storage Provider

Checks the configured storage provider for the active workspace.

**Pass criteria:** Provider is configured and validated.

**Warning criteria:** Provider validation is not ready.

### 10. Task Registry

Checks the local task registry state.

**Pass criteria:** Registry is readable and shows task counts.

### 11. Secret-Safe Patterns

Verifies secret-safe exclude patterns are enabled.

**Pass criteria:** Standard exclusions are in place.

### 12. Local Write Permissions

Checks if the current directory is writable.

**Pass criteria:** Can write to current working directory.

### 13. Environment Variables

Shows Cheri-related environment variables that are set.

**Informational:** Lists any Cheri environment variables found.

## Output Format

### Human-Readable

```
✓ CLI Version       Cheri CLI v0.4.0b1
✓ Python Version    Python 3.11.0
✓ Config Directory  Config directory OK: ~/.config/cheri
⚠ Keyring          keyring package not installed - using fallback
✓ Backend API URL   API URL: https://cheri.parapanteri.com
✓ Backend Health   Backend OK: Cheri CLI API (api_only)
✓ Auth Session     Logged in as: alice
✓ Active Workspace Active workspace: myworkspace (admin)
✓ Storage Provider Provider: system (ready)
✓ Task Registry   2 task(s) configured, 1 running
✓ Secret-Safe     Secret-safe exclusions active (14 patterns)
✓ Local Write      Current directory is writable
✓ Environment      No Cheri environment variables set

Summary: 11 passed, 1 warning, 0 failures
```

### JSON Output

```bash
cheri doctor --json
```

Returns:
```json
{
  "version": "1.0",
  "summary": {
    "total": 13,
    "passed": 11,
    "warnings": 1,
    "failures": 0,
    "skipped": 1,
    "has_critical_failures": false
  },
  "checks": [...]
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed (or `--release-check` with no critical failures) |
| 1 | Critical failure found (with `--release-check`) |

## Using in CI/CD

For automated testing and deployment:

```bash
# Exit non-zero on critical issues
cheri doctor --release-check
if [ $? -eq 0 ]; then
  echo "Cheri is healthy"
else
  echo "Cheri has issues"
  exit 1
fi
```

For scripting with JSON:

```bash
cheri doctor --json | jq '.summary'
```

## Common Issues

### Backend Unreachable

**Symptom:** Backend Health check fails

**Causes:**
- No internet connection
- Backend URL is incorrect
- Backend server is down

**Solutions:**
1. Check your internet connection
2. Run `cheri config get` to verify API URL
3. Run `cheri config check` for detailed connectivity test
4. Contact your administrator

### No Auth Session

**Symptom:** Auth Session check fails

**Causes:**
- Never logged in
- Session expired
- Credentials cleared

**Solutions:**
1. Run `cheri login`
2. If session expired, login again with `cheri login --force`

### No Active Workspace

**Symptom:** Active Workspace check shows warning

**Solutions:**
1. `cheri workspace list` to see available workspaces
2. `cheri workspace create --name <name>` to create one
3. `cheri workspace join <invite-code>` to join existing

### Keyring Warning

**Symptom:** Keyring check shows warning

**Causes:**
- keyring package not installed
- OS keychain not available (headless environment)

**Impact:** Falls back to encrypted file storage

**Solutions:**
1. Install keyring: `pip install keyring`
2. For headless environments, this warning can be safely ignored

### Storage Provider Not Ready

**Symptom:** Storage Provider check shows warning

**Solutions:**
1. Run `cheri storage status` for details
2. Run `cheri storage configure --provider system`
3. Check `cheri doctor` for other issues

## Running Specific Checks

Currently, `cheri doctor` runs all checks. To check specific items:

```bash
# Check only config
cheri config get

# Check only backend
cheri config check

# Check only storage
cheri storage status

# Check only tasks
cheri task list
```

## Reporting Issues

When reporting issues, include the output of:

```bash
cheri doctor --json > doctor-output.json
```

This provides detailed diagnostic information for troubleshooting.
