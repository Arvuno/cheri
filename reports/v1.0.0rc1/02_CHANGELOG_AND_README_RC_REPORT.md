# CHANGELOG and README RC Report
**Date:** 2026-05-30

---

## CHANGELOG Changes

### Added: `[1.0.0rc1]` section at top

```markdown
## [1.0.0rc1] - 2026-05-30 - Release Candidate

### Release Status
**v1.0.0 RC1** — Release candidate for v1.0. Public beta matured into RC.

### Public Beta Matured Into RC
- Python tests pass: 149/149
- Worker tests pass: 8/8
- Storage tests pass: 14/14
- Ruff pass
- Mypy0 errors (26 pre-existing non-blocking type errors)
- Provider capabilities truthfully corrected
- S3-compatible beta verified through Worker-proxy + MinIO
- Agent handoff push/pull implemented
- Secret-safe scanning default

### Known Limitations
- Upload-only sync (no bidirectional sync)
- No conflict resolution
- Direct-to-S3 CLI mode not implemented
- Multipart upload not implemented
- Backblaze B2: docs-only/planned
- Google Drive: not implemented
- PyPI publish requires owner approval
```

**Previous section (`[0.9.1]`) preserved intact.**

---

## README Changes

| Section | Change |
|---------|--------|
| Version badge | `0.9.1` → `1.0.0rc1` |
| Status badge | "Public Beta" → "Release Candidate" |
| Status text | Updated to "v1.0.0 RC1 — Release candidate for v1.0" |
| Ready/Limited table | Provider text updated |
| Provider table | System/R2: ✅ Default/Production; S3-compatible: 🟡 Beta (Worker-proxy + MinIO); MinIO: 🟡 Beta path; B2/GDrive: 📄 Docs-only/Planned |
| Known limitations | Added multipart upload, PyPI publish notes |
| Roadmap | Updated to v1.0+ with current status |

---

## Verdicts

| Check | Status |
|-------|--------|
| CHANGELOG new section | ✅ PASS |
| CHANGELOG old sections preserved | ✅ PASS |
| README version badge | ✅ PASS |
| README status updated | ✅ PASS |
| README provider table honest | ✅ PASS |
| README limitations honest | ✅ PASS |
| No hype for unsupported features | ✅ PASS |

**Next:** Step 5 reports → Step 6 package build report
