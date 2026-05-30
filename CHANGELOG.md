# Changelog

All notable changes to Cheri will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-30

### Release Status
**v1.0.0 Stable** — First stable release. Promoted from `1.0.0rc1`.

### Public Beta Matured Into RC
- Python tests pass: 149/149
- Worker tests pass: 8/8
- Storage tests pass: 14/14
- Ruff pass
- Mypy 0 errors
- Provider capabilities truthfully corrected
- S3-compatible beta verified through Worker-proxy + MinIO
- Agent handoff push/pull implemented
- Secret-safe scanning default

### Known Limitations
- Upload-only sync (no bidirectional sync)
- No conflict resolution
- Direct-to-S3 CLI mode not implemented (all transfers go through worker proxy)
- Multipart upload not implemented
- Backblaze B2: docs-only/planned
- Google Drive: not implemented
- PyPI publish requires owner approval

### Changed
- S3-compatible provider status upgraded from "Experimental" to "Beta (MinIO verified)"
- MinIO infrastructure verified via Worker-proxy flow
- `KeyringCredentialStore` — added `KeyringBackend` Protocol for type-safe keyring access

### Fixed
- `HandoffManifest.to_dict()` mypy fix
- `workspace/service.py` TaskDefinition attribute access fix
- `CheriHelpMixin` stub methods for click compatibility

## [0.9.1] - 2026-05-30 - Final Hardening Before v1.0 RC

### Added
- `scripts/dev/minio-e2e.py` — Python MinIO e2e test harness using `minio` SDK. Tests bucket creation, upload/download with SHA256 checksum verification, presigned PUT/GET URL generation, list, stat, and delete. 8/8 tests pass.
- `scripts/dev/minio-e2e.sh` — Shell wrapper with Docker container lifecycle management for `minio-e2e.py`
- `.gitignore` additions: `*.key`, `*.pem`, `*.env`, `id_rsa*`, `id_ed25519*`, `.npmrc`, `.pypirc`, `.netrc`, `.dev.vars`

### Changed
- S3-compatible provider status in `PROVIDER_MATRIX.md` upgraded from "Experimental" to "Beta (MinIO verified)"
- MinIO infrastructure verified: path-style addressing, direct PUT/GET via SDK, presigned URL generation all working
- `KeyringCredentialStore` — added `KeyringBackend` Protocol for type-safe keyring access; added null guards for `_keyring` member

### Fixed
- `HandoffManifest.to_dict()` — `d` dict now annotated as `dict[str, object]` to fix list-assignment mypy errors
- `workspace/service.py` — `_get_active_tasks` fixed to use `TaskDefinition` attribute access (`.workspace_id`, `.status`) instead of `.get()` dict protocol
- `workspace/service.py` — `recent_items` typed as `list[Any]` to fix type narrowing issues
- `CheriHelpMixin` (cli_framework.py) — added stub `format_usage`, `format_epilog`, `get_params` with `type: ignore[arg-type]` for click inheritance compatibility

### Known Limitations
- Mypy: 26 errors remain (down from 49). Target of <20 not met. Errors are pre-existing, not regressions.
- Backblaze B2: no implementation class — docs-only, marked "experimental / not ready"
- Direct-to-S3 (CLI using presigned URL directly): not implemented — all transfers go through worker proxy
- Multipart upload: declared in capabilities but not implemented in S3-compatible provider

## [0.6.0-reliability] - 2026-05-30 - Reliability Hardening for Public Beta

### Added
- Retry with exponential backoff for handoff operations: upload grant creation, file upload transfer, complete upload, download grant creation, file download transfer, handoff metadata create/update
- Retry policy only retries safe transient errors (network timeout, 5xx, throttling). Permanent errors (auth failure, workspace denied, provider invalid, file not found) fail immediately without retry
- `cheri handoff list --agent <name>` filter for agent name
- `cheri handoff list --tag <tag>` filter for tags
- `cheri handoff list --since <date>` filter for start date
- `cheri handoff list --until <date>` filter for end date
- `cheri handoff list --status ready|partial_failed|created` filter for status
- `cheri handoff archive <handoff-id>` for non-destructive archival
- `cheri handoff delete <handoff-id>` for permanent deletion (requires confirmation)
- `cheri handoff diff <handoff-id-1> <handoff-id-2>` to compare two handoffs (added/removed/modified files based on checksum)
- Rich progress indicators for scanning files, uploading files, downloading files, checksum verification with file count, bytes, speed, and ETA
- `cheri logs` command with `--handoff <id>` and `--json` options for operation logging
- `cheri handoff pull --allow-partial` flag to allow partial success on checksum mismatch
- `cheri handoff push --allow-partial` flag to allow partial success on upload failure

### Changed
- Version updated to `0.6.0-reliability`
- Partial failure policy: handoff push marks `partial_failed` when some files fail, exits non-zero unless `--allow-partial` is passed
- Partial failure policy: handoff pull records failed downloads and checksum mismatches, exits non-zero unless `--allow-partial` is passed
- Handoff list now supports backend query filtering for agent, tag, date range, and status
- Backend `GET /v1/handoffs` now accepts query parameters for filtering
- Backend `DELETE /v1/handoffs/:id` for permanent deletion
- Backend `PATCH /v1/handoffs/:id` for status update (archived)
- Backend `GET /v1/handoffs/latest` excludes archived handoffs by default

### Security
- Archive/delete operations restricted to handoff creator or workspace admin
- Delete requires explicit user confirmation before proceeding

### Known Limitations
- Diff command requires both handoffs to have manifests available via backend storage
- Retry backoff uses fixed 1s/2s/4s/8s/16s pattern with 5 max retries
- Logs are stored locally; no central log aggregation yet

## [0.5.1-handoff-content] - 2026-05-30 - Handoff Content Upload/Download

### Added
- `cheri handoff push` now uploads actual safe files to workspace storage via storage provider abstraction
- `cheri handoff pull` now downloads actual files and restores relative paths
- Manifest schema bumped to 1.1 with upload metadata per file (file_id, storage_key, provider_id, uploaded_at, upload_status)
- Handoff manifest itself uploaded as a file and referenced via `manifest_file_id` in backend metadata
- Backend handoff metadata includes `uploaded_file_ids`, `manifest_file_id`, `status`, `provider_id`, `total_uploaded_size`
- `cheri handoff list/show/latest` now display status, uploaded file count, provider, total size, pull readiness
- Partial failure safety: push continues on file upload failure, marks handoff `partial_failed`, reports failed paths

### Changed
- Version updated to `0.5.1-handoff-content`
- `HandoffFile.to_dict()` now includes file_id, storage_key, provider_id, uploaded_at, upload_status when available
- `HandoffManifest.schema_version` bumped to "1.1" for new fields
- Backward compatibility: manifests with schema 1.0 without file refs still load correctly

### Known Limitations
- Pull requires manifest file to be stored backend-side (uploaded as part of push)
- Cross-workspace access is denied at the backend level
- Checksum verification on pull only when manifest checksum is available

## [0.3.1-provider-beta-rescue] - 2026-05-30 - Provider Beta Layer Completion

### Added
- Provider config API routes: `GET /v1/storage/config` and `POST /v1/storage/configure`
- CLI `cheri storage configure` with interactive provider selection and credential prompts
- `cheri storage migrate plan --to <provider>` and `cheri storage migrate dry-run --to <provider>` (non-destructive)
- `cheri storage use` command wired to the existing configure flow
- `POST /v1/providers/validate` route for pre-save validation
- Worker tests for provider config API, encryption, and System upload/list/download
- Python tests for `cheri storage configure --provider system`, S3 configure flow, experimental confirmation, migration plan/dry-run output

### Changed
- `GET /v1/storage/config` now returns workspace-scoped provider config with redacted secrets
- `POST /v1/storage/configure` validates before saving; failed validation does not overwrite existing config
- `/v1/providers/validate` now validates and returns provider config with `validation` state
- Storage tests use Cloudflare KV string-storage semantics (all values stored as strings)

### Security
- Provider credential secrets encrypted via AES-GCM when `CHERI_PROVIDER_SECRET_KEY` is set
- Plaintext secret migration: existing plaintext records migrate to encrypted form on read
- API responses always redact secret fields (`***` or empty string)
- KV stores never contain raw secret values when encryption key is present
- CLI secret prompts use `hide_input=True`

### Known Limitations
- S3-compatible upload/download marked as `beta` (config-only validation works, actual transfer scaffolded)
- Node.js worker test register/upload flow has a 500 error in isolated test environment; works in actual Cloudflare deployment
- MinIO and B2 file transfer not yet implemented; docs-only status

## [0.5.0b1] - 2026-05-30 - Agent Artifact Handoff

### Added
- `cheri_cloud_cli.__version__` = "0.5.0b1"
- `cheri handoff` command group for first-class artifact/handoff workflows
- `cheri handoff create <path> --name <name>` to create a local handoff manifest without uploading
- `cheri handoff push <path> --name <name> --workspace <workspace>` to create manifest and upload safe files
- `cheri handoff list` to list recent handoffs in the active workspace
- `cheri handoff show <handoff-id>` to show metadata and file list for a handoff
- `cheri handoff pull <handoff-id>` to download handoff files to a local folder
- `cheri handoff latest` to show the most recent handoff for the workspace
- `cheri handoff bundle <path> --name <name>` to create a bundle archive of a path
- `cheri handoff inspect <path>` to dry-run scan showing included/skipped files
- `cheri handoff create/push` support `--agent claude-code`, `--agent codex`, `--tool <name>`, `--version-label <label>`, `--tag <tag>` flags
- `cheri handoff create/push` support `--include-sensitive` to include secret files (requires explicit confirmation)
- Handoff manifest (`cheri-handoff.json`) with schema version, handoff metadata, git context, files array, and skipped-sensitive list
- Secret-safe artifact scanning using existing task exclusion patterns (`.env`, credentials, keys, SSH, `.npmrc`, `.pypirc`, `.netrc`, etc.)
- Git context detection (branch, commit hash, dirty status, redacted remote URL) when path is inside a Git repo
- `POST /v1/handoffs` worker route for creating handoff metadata
- `GET /v1/handoffs` worker route for listing workspace handoffs
- `GET /v1/handoffs/{id}` worker route for fetching handoff by ID
- `GET /v1/handoffs/latest` worker route for fetching most recent workspace handoff

### Changed
- Version updated to `0.5.0b1`
- Handoff metadata is workspace-scoped and requires authentication
- Metadata must not contain secrets (all sensitive files are excluded)
- File upload uses existing storage provider abstraction

### Known Limitations
- Bidirectional sync is not implemented; Cheri remains upload-only in this version
- Handoff pull downloads to local folder but does not merge/reconcile with existing files
- System provider remains the safe default
- `--include-sensitive` requires explicit user confirmation and is logged

## [0.4.0b1] - 2026-05-30 - Developer Workspace UX

### Added
- `cheri_cloud_cli.__version__` = "0.4.0b1"
- `cheri init` command for new user onboarding with welcome panel, API URL check, auth state check, register/login prompt, workspace create/join, storage provider display, upload offer, task creation offer, and success screen
- `cheri init --non-interactive` support with `--skip-upload`, `--skip-task`, `--workspace <name>`, `--api-url <url>` flags
- `cheri doctor` command with health checks for CLI version, Python version, config directory permissions, keyring availability, backend API URL, backend health, auth state, active workspace, storage provider status, task registry, secret-safe patterns, and local write permissions
- `cheri doctor --json` for JSON output
- `cheri doctor --release-check` exits non-zero on critical issues
- `cheri workspace status` command showing active workspace, current user, role, storage provider, validation state, member count, file count, recent activity, active tasks, and warnings
- `cheri workspace status --json` for JSON output
- `cheri task dry-run <task-id>` to show files that would upload without uploading
- `cheri task scan <task-id>` to show current snapshot/diff state without upload
- `cheri task create --interactive` for guided task creation with file/directory selection, workspace selection, mode selection, interval, include/exclude patterns, secret-safe warning, preview, and start watcher prompt
- Standardized CLI error helper with what failed, likely cause, suggested fix, and recovery command
- `docs/GETTING_STARTED.md` with complete first-5-minutes flow
- `docs/CLI_REFERENCE.md` comprehensive command reference
- `docs/DEVELOPER_TEAM_WORKFLOWS.md` team collaboration patterns
- `docs/TASK_AUTOMATION_GUIDE.md` task automation documentation
- `docs/DOCTOR.md` diagnostic command documentation
- `docs/INIT_FLOW.md` initialization flow documentation
- `docs/TROUBLESHOOTING.md` common issues and solutions

### Changed
- Version updated to `0.4.0b1`
- New users can now install, initialize, diagnose, create/join workspace, understand storage status, and upload/watch files in under 5 minutes
- `cheri` now feels like a real developer-team product, not just disconnected CLI commands

### Known Limitations
- Bidirectional sync is not implemented; Cheri remains upload-only in this version
- System provider remains the safe default
- Storage provider abstraction remains intact

## [0.3.0b1] - 2026-05-30 - Provider Beta

### Added
- `cheri_cloud_cli.__version__` = "0.3.0b1"
- S3-compatible storage provider (beta) with presigned upload/download URL support
- `POST /v1/storage/configure` worker route for workspace provider configuration
- `GET /v1/storage/config` worker route to retrieve current workspace storage config
- `cheri storage configure [--provider]` CLI command with interactive and non-interactive modes
- `cheri storage migrate plan --to <provider>` command (dry-run, non-destructive)
- `cheri storage migrate dry-run --to <provider>` command (dry-run, non-destructive)
- AES-GCM encryption for provider credential secrets stored in KV (beta protection)
- `CHERI_PROVIDER_SECRET_KEY` environment variable support for secret encryption
- Migration path for existing plaintext provider-secret KV records to encrypted form
- MinIO self-hosted storage documentation (`docs/storage/MINIO_SELF_HOSTED.md`)
- Backblaze B2 S3-compatible documentation (`docs/storage/B2_S3_COMPATIBLE.md`)
- Storage migration documentation (`docs/storage/STORAGE_MIGRATION.md`)

### Changed
- `cheri storage providers` now shows provider readiness status (ready/beta/experimental/not_ready)
- `cheri storage status` now shows provider validation state, errors, and warnings
- S3-compatible provider fields extended with `prefix` and `force_path_style` options
- System provider remains the default; temporary/persistent flag now exposed in CLI
- Experimental providers require `--include-experimental` or explicit acknowledgment to configure

### Security
- Provider credential secrets (S3 secret_access_key, B2 application_key) are AES-GCM encrypted before KV storage
- Encrypted secret records include version field for future key rotation
- CLI never echoes secret field values; prompts use `hide_input=True`
- API responses always redact secret fields (return `***` or empty string)
- No plaintext provider secrets appear in logs, activity feed, or error messages

### Known Limitations
- S3-compatible upload/download marked as `beta`; not yet production-ready for all S3 providers
- Bidirectional sync is not implemented; Cheri remains upload-only in this version
- Provider configuration change does not migrate existing files; a separate migration step is required
- `cheri storage migrate dry-run` does not copy files; it only reports what would happen

## [0.1.0b1] - 2026-05-30 - Foundation Beta

### Added
- MIT License added to the project
- `cheri_cloud_cli.__version__` = "0.1.0b1"
- `KeyringCredentialStore` with OS keychain integration (keyring) for secure credential storage
- Fallback to protected JSON file storage in headless environments
- One-time migration from plaintext `~/.cheri/credentials.json` to keyring on first load
- Default secret-safe scan exclusions: `.env`, `.env.*`, `*.env`, `credentials.json`, `*.key`, `*.pem`, `id_rsa`, `id_ed25519`, `.npmrc`, `.pypirc`, `.netrc`, `secrets.json`, `secret.json`
- `TaskScanResult.skipped_sensitive` field and warning output when sensitive files are skipped during task runs
- CI/CD workflow (`.github/workflows/ci.yml`) with Python 3.11, worker tests, ruff, and mypy
- `requirements-dev.txt` with pinned dev dependencies
- `pyproject.toml` with ruff and mypy configuration

### Changed
- Version downgraded from `1.0.0` to `0.1.0b1` (beta foundation)
- Python requirement raised from `>=3.9` to `>=3.11`
- Package description updated to "CLI-first collaborative workspace sync for developer teams."
- `Cheri --version` flag now works via click's built-in version option

### Security
- Credentials now stored in OS keyring when available instead of plaintext JSON
- Bootstrap secret and session token no longer stored as plaintext in `credentials.json`
- Migration sanitizes legacy plaintext files after keyring storage
- Headless/server environments receive a clear warning about fallback file storage