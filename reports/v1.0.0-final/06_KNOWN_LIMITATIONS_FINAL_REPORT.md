# v1.0.0 Final — Known Limitations Report

**Date:** 2026-05-30

---

## Stable / Production-Ready

| Capability | Status | Notes |
|------------|--------|-------|
| System (R2) provider | ✅ Production-ready | Default provider |
| CLI core commands | ✅ Stable | register, login, workspace, file, team, activity, task |
| Agent handoff (push/pull) | ✅ Stable | Implemented |
| Secret-safe scanning | ✅ Stable | Default |
| Python tests | ✅ 149/149 | All passing |
| Worker tests | ✅ 8/8 | All passing |
| Storage tests | ✅ 14/14 | All passing |
| Ruff lint | ✅ 0 issues | |
| Mypy | ✅ 0 errors | |
| Package build | ✅ `cheri-1.0.0` | sdist + wheel |

---

## Beta / Verified (Not Production-Ready)

| Capability | Status | Notes |
|-----------|--------|-------|
| S3-compatible provider | 🟡 Beta | Worker-proxy + MinIO path verified; direct-to-S3 CLI mode NOT implemented |
| MinIO | 🟡 Beta path | For S3-compatible testing only |

---

## Not Implemented / Docs-Only / Planned

| Capability | Status | Notes |
|-----------|--------|-------|
| Bidirectional sync | ❌ Not implemented | Upload-only sync |
| Conflict resolution | ❌ Not implemented | Manual conflict handling required |
| Direct-to-S3 CLI mode | ❌ Not implemented | All S3 transfers go through worker proxy |
| Multipart upload | ❌ Not implemented | Large file uploads not yet supported |
| Google Drive provider | ❌ Not implemented | Docs-only / planned |
| Backblaze B2 provider | 📄 Docs-only | S3-compatible mode possible |
| Bidirectional sync CLI | ❌ Not implemented | Not started |
| PyPI publish | ⏳ Requires approval | `OWNER_APPROVES_PYPI_PUBLISH=YES` not present |

---

## Security Considerations

| Item | Status | Notes |
|------|--------|-------|
| Local secret storage | ⚠️ Not encrypted at rest | Security consideration for shared machines |
| Daily file reset | ⚠️ System provider | Files cleaned up daily |
| Bootstrap secrets | ⚠️ Must not be committed | Documented in README |

---

## What This Release Does NOT Claim

The following are explicitly NOT claimed by v1.0.0:

- ❌ Not a Dropbox replacement
- ❌ No bidirectional sync
- ❌ No conflict resolution UI
- ❌ No Google Drive integration
- ❌ No Backblaze B2 native support
- ❌ No direct-to-S3 CLI mode
- ❌ No multipart upload
- ❌ Not published to PyPI

---

## Result: PASS — Limitations Are Honest

All limitations are clearly documented in README.md and CHANGELOG.md. No false claims made.
