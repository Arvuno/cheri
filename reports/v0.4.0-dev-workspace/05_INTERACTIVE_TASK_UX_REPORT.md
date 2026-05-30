# Interactive Task UX Report

## Implementation: Complete

### New Commands
- `cheri task dry-run <task-id>` - Shows files that would upload without uploading
- `cheri task scan <task-id>` - Shows current snapshot/diff state without upload
- `cheri task create --interactive` - Guided task creation wizard

### Task Create Interactive Wizard
1. Choose file or directory
2. Select target path with picker
3. Choose workspace
4. Choose sync mode (on-change, interval, instant, hybrid)
5. Configure interval (if applicable)
6. Set recursive option
7. Configure include/exclude patterns
8. Show secret-safe exclusions warning
9. Preview task
10. Confirm and create
11. Ask to start watcher

### Dry Run Output
- Files that would be uploaded (green)
- Files skipped due to secret-safe patterns (yellow)
- Deleted paths ignored by upload-only mode (dim)

### Verification
```bash
cheri task --help  # Shows dry-run and scan commands
cheri task create --help  # Shows --interactive flag
```
