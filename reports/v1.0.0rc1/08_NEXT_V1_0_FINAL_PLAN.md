# Next v1.0 Final Plan
**Date:** 2026-05-30

---

## Status

**v1.0.0rc1 RC** — PREPARED AND READY

The release candidate has been prepared. All gates pass. The commit and tag are created locally.

---

## What Was Done

1. ✅ Audited current state (branch `v0.9-s3-e2e-and-type-cleanup`, version `0.9.1`)
2. ✅ Bumped version to `1.0.0rc1` across all 5 files
3. ✅ Updated CHANGELOG with new `[1.0.0rc1]` section
4. ✅ Updated README with RC status, honest provider table, limitations
5. ✅ Fixed `v1-readiness-gate.sh` bug in `run_check` function
6. ✅ Ran full v1 readiness gate — 10/10 PASS
7. ✅ Built package (`cheri-1.0.0rc1.tar.gz` + wheel)
8. ✅ twine check passed on both artifacts
9. ✅ Security/staging gate passed — no dangerous files staged
10. ✅ Created all 8 RC reports
11. ✅ Committed as `chore(release): prepare Cheri v1.0.0rc1`
12. ✅ Created local tag `v1.0.0rc1`

---

## To Release v1.0.0 Final

When ready to finalize:

1. **Review the RC reports** in `reports/v1.0.0rc1/`
2. **Test the built package:**
   ```bash
   pip install dist/cheri-1.0.0rc1-py3-none-any.whl
   cheri --help
   ```
3. **If all good, bump to final:**
   - Change `1.0.0rc1` → `1.0.0` in all version files
   - Update CHANGELOG `[1.0.0rc1]` → `[1.0.0]` with final date
   - Update README status from "Release Candidate" to "v1.0.0"
   - Amend the commit: `git commit --amend` (or new commit)
   - Create final tag: `git tag -a v1.0.0 -m "Cheri v1.0.0"`
4. **PyPI publish** (requires owner approval):
   ```bash
   twine upload dist/cheri-1.0.0.tar.gz dist/cheri-1.0.0-py3-none-any.whl
   ```

---

## Remaining Post-RC Items

| Item | Priority | Notes |
|------|---------|-------|
| PyPI owner approval | High | Cannot publish without owner |
| Mypy debt cleanup | Medium | 26 non-blocking errors remain |
| Bidirectional sync | Future | Not started |
| Direct-to-S3 CLI mode | Future | Not started |
| Multipart upload | Future | Not started |
| Google Drive provider | Future | Docs-only |

---

## Hard Rules Compliance

| Rule | Status |
|------|--------|
| No PyPI publish | ✅ Not executed |
| No force push | ✅ Not executed |
| No secrets committed | ✅ Clean |
| No dangerous files staged | ✅ Clean |
| No false feature claims | ✅ Honest docs |
| S3-compatible beta not claimed stable | ✅ Correct |
| System provider default | ✅ Correct |

---

## Final Recommendation

**PROCEED TO v1.0.0 FINAL** — All gates pass, documentation is honest, no blocking issues remain.
