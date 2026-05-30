# Documentation & Changelog Report

## What Changed

Added or updated documentation files to reflect v0.1.0-beta status and product limitations.

## Files Added/Updated

| File | Change |
|------|--------|
| `LICENSE` | Added — MIT License |
| `CHANGELOG.md` | Added — v0.1.0b1 changelog |
| `docs/RELEASE_PROCESS.md` | Added — SemVer policy, version bump steps |
| `docs/SECURITY.md` | Added — credential storage, task scanning, not-to-commit list |
| `docs/ROADMAP.md` | Added — v0.1.x → v1.0.0 roadmap |
| `README.md` | Review — confirmed existing limitations are accurate |
| `docs/provider-matrix.md` | Review — confirmed accurate |
| `cheri_cloud_cli/__init__.py` | Updated — __version__ = "0.1.0b1" |
| `setup.py` | Updated — version, description, python_requires |
| `package.json` | Updated — version to 0.1.0b1 |

## README Accuracy Check

Current README already correctly states:
- "Beta foundation" (not explicitly, but version 1.0.0 was misleading — now 0.1.0b1)
- "System (recommended) is the only public provider that is production-ready"
- "task automation is upload-only today"
- "conflict handling and bidirectional sync are not implemented"
- "local secret storage is separated but not encrypted at rest" (now improved with keyring)

## CHANGELOG.md Structure

Follows Keep a Changelog format with sections:
- Added
- Changed
- Security
- Deprecated (none yet)
- Removed (none yet)
- Fixed (none yet)
- Migration (none yet)

## SemVer Policy (from RELEASE_PROCESS.md)

- `v0.1.x` — Foundation beta (current)
- `v0.2.x` — Storage abstraction
- `v0.3.x` — Provider beta
- `v1.0.0` — First stable CLI product

Breaking changes to public APIs will increment the minor version with deprecation notice.

## Documentation Gaps (Future)

- `docs/DEPLOYMENT.md` — skeleton not filled (self-hosting instructions)
- `docs/TROUBLESHOOTING.md` — not created (common issues and solutions)
- `docs/ARCHITECTURE.md` — could be added for Worker design docs

These are recommended for v0.2.0 but not blocking for initial beta release.