# Security & Credential Storage Report

## What Changed

Added `KeyringCredentialStore` to `cheri_cloud_cli/sessions/store.py`:
- Uses OS keyring (keyring library) when available on desktop environments
- Falls back to protected JSON file storage in headless/container/server environments
- One-time migration reads existing `~/.cheri/credentials.json`, stores secrets in keyring, sanitizes plaintext file
- Clear warning printed when fallback is used

## Implementation

**Key Classes**:
- `KeyringCredentialStore` — primary secure store, tries keyring first
- `JsonCredentialStore` — preserved for backwards compatibility, unchanged

**Keyring keys**:
- `cheri.session_token` — stores session token
- `cheri.bootstrap_secret` — stores bootstrap secret when persist flag set

**Headless detection** (`_is_headless()`):
- Returns True on Linux with no DISPLAY/WAYLAND and no CHERI_FORCE_KEYRING
- Returns False on Windows/macOS (desktop environments have keyring access)

**Migration** (`_migrate_from_json_if_needed()`):
- Reads `~/.cheri/credentials.json`
- Stores session token and bootstrap secret in OS keyring
- Writes new `state.json` with identity and workspace_access (public fields)
- Sanitizes `credentials.json` with migration note, no secrets remain

## Files Changed

- `cheri_cloud_cli/sessions/store.py` — KeyringCredentialStore added (270+ lines)
- `cheri_cloud_cli/sessions/__init__.py` — KeyringCredentialStore exported
- `tests/python/test_store.py` — 10 new tests for keyring store

## Tests Added

| Test | Coverage |
|------|----------|
| `test_keyring_store_saves_and_loads_session_token` | save/load session via keyring |
| `test_keyring_store_saves_bootstrap_secret_when_requested` | bootstrap persist flag |
| `test_keyring_store_loads_from_keyring` | keyring read on load |
| `test_keyring_store_fallback_warns_when_keyring_unavailable` | headless fallback warning |
| `test_keyring_store_migrates_legacy_json_to_keyring` | full migration flow |
| `test_no_plaintext_bootstrap_secret_after_keyring_migration` | sanitization verified |
| `test_fallback_when_keyring_not_installed` | keyring unavailable path |
| `test_clear_removes_keyring_entries_and_files` | clear removes keyring entries |

## Security Properties

1. **No plaintext secrets** when keyring available — session token and bootstrap secret stored only in OS keychain
2. **Migration sanitizes legacy files** — `credentials.json` is replaced with a migration note, no secrets remain
3. **Fallback warning** — headless environments print a clear warning that credentials are in a protected file, not encrypted keychain
4. **Protected file permissions** — fallback JSON files use `0o600` permissions on Unix

## Risks

- **Headless fallback**: Credentials stored in file-based JSON, not encrypted. Acceptable for single-user containers; not for shared systems.
- **Migration overwrites legacy state**: The migration creates a new `state.json` and sanitizes `credentials.json`. This is a one-time operation — subsequent runs use keyring directly.
- **Keyring not available**: If keyring import fails for any reason, `_get_keyring()` returns None and fallback is used silently. The `keyring_available` property can be checked.

## Next for v0.2.0

- Per-workspace provider credential storage using keyring-backed vault per provider
- Encrypted at-rest for non-keyring environments using a derived key from bootstrap secret
- Secret rotation support