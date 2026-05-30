# Security

## Reporting Vulnerabilities

If you discover a security vulnerability in Cheri, please do not open a public issue. Contact the maintainers directly with details.

## Credential Storage

### Keyring (Desktop Environments)

When `keyring` is available and a desktop environment is detected, Cheri stores session tokens and bootstrap secrets in the OS-level keychain:

- **macOS**: Keychain Access
- **Linux**: libsecret (GNOME Keyring / KDE Wallet)
- **Windows**: Credential Manager

### Fallback (Headless / Server)

In container, server, or headless environments where keyring is unavailable, Cheri falls back to file-based storage with `0o600` permissions. A warning is printed:

> OS keyring is not available. Credentials are stored in a protected local file that may not be encrypted. Do not use this in untrusted multi-user environments.

### Migration

On first load with keyring available, any existing plaintext `~/.cheri/credentials.json` is migrated:
1. Secrets are read from the file
2. Stored in the OS keyring
3. The legacy file is sanitized (secrets replaced with a migration note)

## Task Scanning

Cheri excludes sensitive files by default from task scanning:
- `.env`, `.env.*`, `*.env` — environment variable files
- `credentials.json` — credential files
- `*.key`, `*.pem` — private keys and certificates
- `id_rsa`, `id_ed25519` — SSH private keys
- `.npmrc`, `.pypirc`, `.netrc` — package manager credentials
- `secrets.json`, `secret.json` — secret configuration

These exclusions prevent accidental upload of sensitive local files to the workspace.

## Session Tokens

Session tokens are short-lived and stored only in memory or the OS keyring. They are never logged or printed in full.

## Bootstrap Secrets

Bootstrap secrets are shown once during registration and cannot be recovered. Users should store them securely (password manager, keyring, etc.).

## What Not to Commit

- `.env` files and local overrides
- `credentials.json` with real secrets
- Provider credential files
- SSH private keys
- Session tokens or bootstrap secrets in logs or screenshots