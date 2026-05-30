# Troubleshooting Guide

Solutions to common Cheri issues.

## Quick Diagnostics

Start here for any issue:

```bash
cheri doctor
```

This runs a comprehensive health check and identifies most configuration problems.

## Common Issues

### 1. Backend Unreachable

**Symptom:**
```
Error: Backend API is not reachable
```

**Solutions:**

1. Check your internet connection:
   ```bash
   ping cheri.parapanteri.com
   ```

2. Verify API URL configuration:
   ```bash
   cheri config get
   ```

3. Test connectivity:
   ```bash
   cheri config check
   ```

4. If using custom backend:
   ```bash
   cheri config set api-url https://your-backend.example.com
   ```

### 2. Not Logged In

**Symptom:**
```
Error: Not logged in
```

**Solutions:**

1. Login with credentials:
   ```bash
   cheri login
   ```

2. If you don't have an account:
   ```bash
   cheri register
   ```

3. If session expired:
   ```bash
   cheri login --force
   ```

### 3. No Active Workspace

**Symptom:**
```
Error: No active workspace
```

**Solutions:**

1. List available workspaces:
   ```bash
   cheri workspace list
   ```

2. Create a new workspace:
   ```bash
   cheri workspace create --name myworkspace
   ```

3. Join an existing workspace:
   ```bash
   cheri workspace join CHR-TEAM-8X2K91QZ
   ```

4. Use a specific workspace:
   ```bash
   cheri workspace use workspace-name
   ```

### 4. Upload Fails

**Symptom:**
```
Error: Could not obtain upload authorization
```

**Solutions:**

1. Verify workspace access:
   ```bash
   cheri workspace status
   ```

2. Check storage provider:
   ```bash
   cheri storage status
   ```

3. Verify authentication:
   ```bash
   cheri doctor | grep Auth
   ```

4. Try logging in again:
   ```bash
   cheri logout
   cheri login
   ```

### 5. Download Fails

**Symptom:**
```
Error: Could not obtain download authorization
```

**Solutions:**

1. Verify file exists:
   ```bash
   cheri file list
   ```

2. Check file name/ID:
   ```bash
   cheri file list | grep filename
   ```

3. Verify workspace access:
   ```bash
   cheri workspace status
   ```

### 6. Task Won't Start

**Symptom:**
```
Error: Task task_xxx is already running
```

**Wait for task to complete or stop it:**
```bash
cheri task stop task_xxx
```

**Symptom:**
```
Error: Task not found: task_xxx
```

**Check task ID:**
```bash
cheri task list
```

**Symptom:**
```
Error: Workspace provider is not available
```

**Check provider:**
```bash
cheri storage status
cheri storage configure --provider system
```

### 7. Keyring Warning

**Symptom:**
```
Warning: keyring package not installed - using fallback
```

**Impact:** Credentials stored in encrypted file instead of OS keychain.

**Solutions:**

1. Install keyring:
   ```bash
   pip install keyring
   ```

2. For headless environments, this is expected and safe.

### 8. Task Scans But Doesn't Upload

**Symptom:** `task dry-run` shows changes but uploads don't happen.

**Explanation:** This is expected for `dry-run`. Use `task run` to actually upload.

```bash
cheri task run task_xxx
```

### 9. Files Not Detected as Changed

**Symptom:** Task doesn't upload when files change.

**Solutions:**

1. Verify task is running:
   ```bash
   cheri task list
   ```

2. Check task mode:
   ```bash
   cheri task list | grep on-change
   ```

3. Try manual run:
   ```bash
   cheri task run task_xxx
   ```

4. Check debounce setting (default 3s):
   ```bash
   # Wait longer between changes
   ```

### 10. Too Many Uploads

**Symptom:** Task uploads too frequently.

**Solutions:**

1. Increase debounce:
   ```bash
   # Delete and recreate with higher debounce
   cheri task remove task_xxx
   cheri task create --directory ./src --mode on-change --debounce 10
   ```

2. Switch to interval mode:
   ```bash
   cheri task create --directory ./src --mode interval --every 30m
   ```

### 11. Sensitive Files Uploaded

**Symptom:** Concern that sensitive files were uploaded.

**Explanation:** Cheri has built-in secret-safe patterns that exclude:
- `.env`, `.env.*`, `*.env`
- `credentials.json`
- `*.key`, `*.pem`
- `id_rsa`, `id_ed25519`
- And more...

These files are **never uploaded**.

**Verification:**
```bash
cheri task dry-run task_xxx
```
Shows files that would be uploaded.

### 12. Permission Denied

**Symptom:**
```
Error: Permission denied
```

**Solutions:**

1. Check file permissions:
   ```bash
   ls -la filename
   ```

2. Check directory permissions:
   ```bash
   ls -ld directory
   ```

3. Run with appropriate permissions

### 13. Config Directory Issues

**Symptom:**
```
Error: Config directory is not writable
```

**Solutions:**

1. Check config directory:
   ```bash
   ls -la ~/.config/cheri  # Linux
   ls -la ~/Library/Application\ Support/Cheri  # macOS
   ```

2. Fix permissions:
   ```bash
   chmod 700 ~/.config/cheri
   ```

### 14. Storage Provider Not Ready

**Symptom:**
```
Warning: Storage provider not ready
```

**Solutions:**

1. Check provider status:
   ```bash
   cheri storage status
   ```

2. Reconfigure provider:
   ```bash
   cheri storage configure --provider system
   ```

3. Run diagnostics:
   ```bash
   cheri doctor | grep Storage
   ```

### 15. Session Expired

**Symptom:** Commands work but new actions fail.

**Solutions:**

1. Refresh session:
   ```bash
   cheri logout
   cheri login
   ```

2. Use bootstrap secret to relogin

## Getting Help

### Run Full Diagnostics

```bash
cheri doctor --json > diagnostics.json
```

### Check Version

```bash
cheri --version
```

### Verify Python Version

```bash
python --version  # Need 3.11+
```

### View Logs

For task-related issues:
```bash
cheri task logs task_xxx
```

### Check Configuration

```bash
cheri config get
cheri workspace status
cheri storage status
```

## Reporting Issues

When reporting issues, include:

1. Output of `cheri doctor`
2. Output of `cheri doctor --json` (for scripting issues)
3. Cheri version (`cheri --version`)
4. Python version
5. Operating system
6. Steps to reproduce

## Resetting Cheri

If all else fails, you can reset:

```bash
# Clear session (keeps config)
cheri logout

# Reset config to defaults
cheri config reset

# Remove all local data (nuclear option)
rm -rf ~/.config/cheri  # Linux
rm -rf ~/Library/Application\ Support/Cheri  # macOS
```

After reset, run `cheri init` again.

## Known Limitations

These are expected behaviors, not bugs:

1. **Upload-only**: Cheri doesn't download from workspace
2. **System provider resets**: Daily reset for System provider
3. **No bidirectional sync**: Changes only go from local to workspace
4. **Experimental providers**: Some providers marked experimental

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (see error message) |

For `cheri doctor --release-check`:
| Code | Meaning |
|------|---------|
| 0 | No critical issues |
| 1 | Critical issues found |
