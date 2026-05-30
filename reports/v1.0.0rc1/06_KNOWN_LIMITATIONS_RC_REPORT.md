# Known Limitations RC Report
**Date:** 2026-05-30

---

## Truthful Feature Status

The following table documents what is actually implemented vs. what is claimed as future/planned:

| Feature | Claimed Status | Actual Status | Honesty |
|---------|---------------|---------------|---------|
| System (R2) provider | ✅ Default/Production | ✅ Working | ✅ Honest |
| S3-compatible provider | 🟡 Beta (Worker-proxy + MinIO) | 🟡 Beta via Worker-proxy, MinIO verified | ✅ Honest |
| MinIO | 🟡 Beta verified path | 🟡 Beta verified path | ✅ Honest |
| Backblaze B2 | 📄 Docs-only/Planned | 📄 Docs-only/Planned | ✅ Honest |
| Google Drive | 📄 Docs-only/Planned | 📄 Not implemented | ✅ Honest |
| Agent handoff push/pull | ✅ Implemented | ✅ Implemented | ✅ Honest |
| Secret-safe scanning | ✅ Default | ✅ Default | ✅ Honest |
| Upload-only sync | ⚠️ Limitation | ⚠️ Limitation | ✅ Honest |
| Bidirectional sync | ⚠️ Not implemented | ⚠️ Not implemented | ✅ Honest |
| Conflict resolution | ⚠️ Not implemented | ⚠️ Not implemented | ✅ Honest |
| Direct-to-S3 CLI mode | ⚠️ Not implemented | ⚠️ Not implemented | ✅ Honest |
| Multipart upload | ⚠️ Not implemented | ⚠️ Not implemented | ✅ Honest |
| PyPI publish | ⚠️ Requires approval | ⚠️ Not published | ✅ Honest |

---

## What NOT to Claim

The following must NOT be marketed as implemented:
- ❌ S3-compatible as "stable" — it is beta
- ❌ Backblaze B2 as "supported" — it is docs-only
- ❌ Google Drive as "supported" — it is not implemented
- ❌ Direct-to-S3 CLI mode — not implemented (all transfers go through worker proxy)
- ❌ Multipart upload — declared in capabilities but not implemented
- ❌ Bidirectional sync — not started
- ❌ PyPI publish — requires owner approval, not yet done

---

## Provider Capabilities

**System (R2):** Full upload/download/list via Cloudflare R2
**S3-compatible:** Beta — upload/download via Worker-proxy flow, verified with MinIO. Direct-to-S3 CLI mode NOT implemented.
**Backblaze B2:** S3-compatible mode is theoretically possible but not tested/implemented.
**Google Drive:** Not implemented.

---

## Verdicts

| Check | Status |
|-------|--------|
| No false feature claims | ✅ PASS |
| S3-compatible marked beta | ✅ PASS |
| B2 marked docs-only | ✅ PASS |
| GDrive marked not implemented | ✅ PASS |
| Direct-to-S3 marked not implemented | ✅ PASS |
| Multipart marked not implemented | ✅ PASS |
| Bidirectional sync marked not started | ✅ PASS |
| PyPI marked not published | ✅ PASS |

**Next:** Step 9 (v1.0 RC Verdict)
