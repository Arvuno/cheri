# Roadmap

## v0.1.0 — Foundation Beta (current)
**Goal**: Safe, testable, release-trackable beta foundation.

- [x] MIT License
- [x] Version discipline (0.1.0b1)
- [x] Secure credential storage (keyring)
- [x] Secret-safe task scanning
- [x] Worker test framework
- [x] CI/CD baseline (GitHub Actions)
- [x] Documentation updates
- [x] Provider gating (System-only default)

## v0.2.0 — Storage Abstraction Core
**Goal**: Complete the provider abstraction layer so S3/GDrive/B2 are first-class citizens.

- [ ] Unified `StorageProvider` interface with async I/O
- [ ] Provider-specific SDK adapters (boto3 for S3, google-api-python-client for GDrive, b2sdk for B2)
- [ ] Encrypted secret storage per workspace (keyring-backed vault per provider)
- [ ] Provider configuration CRUD in the Worker API
- [ ] Migration path for existing System-only workspaces
- [ ] Backend route: `GET /v1/providers`, `POST /v1/providers/validate`

## v0.3.0 — Provider Beta
**Goal**: Make S3, GDrive, and B2 selectable in the public CLI flow with working upload/download.

- [ ] S3-compatible provider (upload, download, list, delete via boto3)
- [ ] Google Drive provider (upload, download, list via Drive API)
- [ ] Backblaze B2 provider (upload, download, list via b2sdk)
- [ ] Provider-specific credential input prompts
- [ ] Backend validation for each provider type

## v1.0.0 — Stable CLI Product
**Goal**: First stable release with bidirectional sync and full team collaboration.

- [ ] Bidirectional sync (upload + download + delete reconciliation)
- [ ] Conflict resolution strategies (ask, overwrite, keep both, skip)
- [ ] Team workspace admin panel (invite management, permissions)
- [ ] `cheri sync` command for explicit two-way sync
- [ ] Full provider matrix ready for production use
- [ ] PyPI publication
- [ ] Formal support and security policy

## Non-Goals for v1.0

- Full Dropbox replacement (not positioned as such)
- Mobile companion app
- Browser-based file explorer
- Real-time collaborative editing
- AI agent artifact handoff (future phase)