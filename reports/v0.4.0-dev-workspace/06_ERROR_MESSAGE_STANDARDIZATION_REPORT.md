# Error Message Standardization Report

## Implementation: Complete

### cheri_cloud_cli/errors.py

Standardized error messages with:
- What failed
- Likely cause
- Suggested fix
- Recovery command

### Error Types
- BACKEND_UNREACHABLE
- NOT_LOGGED_IN
- NO_ACTIVE_WORKSPACE
- PROVIDER_INVALID
- UPLOAD_GRANT_FAILURE
- DOWNLOAD_GRANT_FAILURE
- TASK_TARGET_MISSING
- KEYRING_UNAVAILABLE
- AUTH_SESSION_EXPIRED
- WORKSPACE_NOT_FOUND

### Usage
```python
from cheri_cloud_cli.errors import print_error, print_error_simple, CheriError

# Print full error panel
print_error(console, CheriError(...))

# Print simple error with hint
print_error_simple(console, "message", CheriError(...))
```
