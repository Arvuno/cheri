# v1.0.0 Final — GitHub Release Notes

**Date:** 2026-05-30

---

## Suggested GitHub Release Body

```markdown
# Cheri v1.0.0 — First Stable Release

**Status:** Stable v1.0 — First stable release. Promoted from `1.0.0rc1`.

## What's New

Cheri is now officially stable! This is the first production-ready release of the CLI-first collaborative workspace sync tool.

### Core CLI Verified
- Python tests pass: **149/149**
- Worker tests pass: **8/8**
- Storage tests pass: **14/14**
- Ruff: **0 issues**
- Mypy: **0 errors**

### Agent Handoff
Push/pull artifacts between agents and local workspace:
```bash
cheri handoff push --name "sprint-23-results" --tag analysis --agent claude
cheri handoff pull <handoff-id>
cheri handoff list --agent claude --since 2026-05-01
cheri handoff diff <handoff-1> <handoff-2>
```

### Secret-Safe Scanning
Secrets are scanned by default and masked in output.

### Storage Provider Abstraction
Provider catalog with honest capability status:
- **System (R2)**: Production-ready (default)
- **S3-compatible**: Beta (Worker-proxy + MinIO verified)
- **MinIO**: Beta verified path
- **Google Drive**: Docs-only / Planned
- **Backblaze B2**: Docs-only / Planned

## Known Limitations

- Upload-only sync (no bidirectional sync)
- No conflict resolution
- Direct-to-S3 CLI mode not implemented (all transfers go through worker proxy)
- Multipart upload not implemented
- Backblaze B2: docs-only/planned
- Google Drive: not implemented
- PyPI publish requires owner approval

## Install

```bash
git clone https://github.com/Arvuno/cheri.git
cd cheri
python -m pip install .
cheri --help
```

## Upgrade from RC1

```bash
git pull origin main
python -m pip install --force-reinstall dist/cheri-1.0.0-py3-none-any.whl
```
```

---

## Tag

- **Tag name:** `v1.0.0`
- **Annotation:** `Cheri v1.0.0`
- **Type:** Annotated tag (`git tag -a v1.0.0 -m "Cheri v1.0.0"`)

---

## Branches

- **Current branch:** `v0.9-s3-e2e-and-type-cleanup`
- **Release branch strategy:** Push to `main`; current feature branch will be the target
- **Remote:** `https://github.com/Arvuno/cheri.git`

---

## Pre-built Artifacts

Artifacts are available in `dist/` after building:
- `cheri-1.0.0.tar.gz` (source distribution)
- `cheri-1.0.0-py3-none-any.whl` (wheel)

---

## PyPI Publish

**NOT PUBLISHED TO PYPI** — requires explicit owner approval (`OWNER_APPROVES_PYPI_PUBLISH=YES` not present).

---

## Result

GitHub release notes prepared. Tag and commit ready for push.
