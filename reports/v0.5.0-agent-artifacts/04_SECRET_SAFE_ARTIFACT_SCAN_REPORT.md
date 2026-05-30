# Secret-Safe Artifact Scan Report

## Overview

Cheri's handoff feature includes secret-safe artifact scanning by default. Sensitive files are identified by name pattern and excluded from the handoff without their contents ever being read.

## Default Exclusion Patterns

These patterns are applied to all handoff scans:

```
.env, .env.*, *.env,
credentials.json, *.key, *.pem,
id_rsa, id_ed25519, id_rsa.pub, id_ed25519.pub,
.npmrc, .pypirc, .netrc,
secrets.json, secret.json,
.git, .gitignore, .DS_Store, Thumbs.db,
*.swp, *.swo
```

These patterns are reused from the existing task scanning exclusion system.

## Implementation

### `is_sensitive_path()` Function

Located in: `cheri_cloud_cli/handoff/__init__.py`

```python
def is_sensitive_path(path: str, exclude_patterns: Optional[list[str]] = None) -> bool:
    patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
    path_lower = path.lower()

    # Check glob patterns
    for pattern in patterns:
        if "*" in pattern:
            if fnmatch.fnmatch(path_lower, pattern.lower()):
                return True
        else:
            if pattern.lower() in path_lower:
                return True

    # Check secret file names
    secret_names = {
        ".env", ".env.local", ".env.production",
        "credentials.json", "secrets.json", "secret.json",
        "id_rsa", "id_ed25519", "id_rsa.pub", "id_ed25519.pub",
        ".npmrc", ".pypirc", ".netrc",
    }

    basename = os.path.basename(path)
    return basename in secret_names
```

### `scan_directory()` Integration

```python
def scan_directory(
    directory: Path,
    recursive: bool = True,
    exclude_patterns: Optional[list[str]] = None,
    include_sensitive: bool = False,
) -> tuple[list[HandoffFile], list[str]]:
```

- When `include_sensitive=False` (default): applies exclusion patterns
- Skipped files are recorded in the second element of the return tuple
- **File contents are never read for skipped files** — only the path is recorded

## Skipped Files Listing

The manifest includes a `skipped_sensitive` array that lists excluded files by name:

```json
{
  "skipped_sensitive": [
    ".env",
    "credentials.json",
    "id_rsa"
  ]
}
```

**Important**: Only file names are stored, not file contents or paths.

## `--include-sensitive` Flag

When `--include-sensitive` is passed:

1. The CLI prompts for explicit confirmation:
   ```
   [yellow]Warning:[/] Secret-safe scanning is enabled by default.
   Sensitive files (.env, credentials, keys, etc.) will be skipped.
   Use --include-sensitive to include them (requires explicit confirmation).

   Continue?
   ```
2. If confirmed, the scan includes all files regardless of pattern
3. The action is logged (future: audit trail)

**Use cases**:
- Personal handoffs on an air-gapped machine
- Explicit acknowledgment that the workspace is trusted

## What Gets Scanned

### Included (Default)
- Source code files (`.py`, `.js`, `.ts`, etc.)
- Documentation (`.md`, `.txt`, `.pdf`)
- Data files (`.json`, `.yaml`, `.csv`)
- Images (`.png`, `.jpg`, `.gif`)
- Build outputs and reports

### Excluded (Default)
- Environment files (`.env`, `.env.production`)
- Credentials and keys (`credentials.json`, `*.key`, `*.pem`)
- SSH keys (`id_rsa`, `id_ed25519`)
- Auth config (`.npmrc`, `.pypirc`, `.netrc`)
- Git metadata (`.git/` contents)
- OS files (`.DS_Store`, `Thumbs.db`)
- Editor temp files (`*.swp`, `*.swo`)

## Secret Content Never in Output

The manifest generation ensures secret file contents never appear in output:

```python
def test_env_file_content_not_in_manifest(self) -> None:
    (self.scan_dir / ".env").write_text("SUPER_SECRET_API_KEY=don't_log_me")
    manifest = create_manifest(source_path=str(self.scan_dir), name="test")
    manifest_str = json.dumps(manifest)
    self.assertNotIn("don't_log_me", manifest_str)
    self.assertNotIn("SUPER_SECRET_API_KEY", manifest_str)
```

## Git Context Redaction

Git remote URLs with embedded credentials are redacted:

```python
# Remove user:pass@ if present
remote_url = re.sub(r"://[^@]+@", "://", remote_url)
```

Example: `https://user:token@github.com/user/repo.git` → `https://github.com/user/repo.git`

## Verification

```bash
# Inspect shows what would be included/skipped
cheri handoff inspect ./reports

# Example output:
# INCLUDED: 15 files
# SKIPPED (secret-safe): 3 files
#
# Skipped files (names only):
#   .env
#   credentials.json
#   id_rsa
```

## Test Coverage

See `tests/python/test_handoff.py` for:
- `IsSensitivePathTests` — pattern matching tests
- `ScanDirectoryTests` — directory scanning with exclusions
- `NoSecretContentInOutputTests` — verification that secret content never appears
- `IncludeSensitiveConfirmationTests` — flag behavior tests