# RC Current State Audit
**Date:** 2026-05-30
**Branch:** `v0.9-s3-e2e-and-type-cleanup`

---

## Version Declarations

| File | Current Value | Target Value |
|------|-------------|--------------|
| `cheri_cloud_cli/__init__.py` | `0.9.1` | `1.0.0rc1` |
| `setup.py` | `0.9.1` | `1.0.0rc1` |
| `package.json` | `0.9.1` | `1.0.0rc1` |
| README.md badge | `0.9.1` | `1.0.0rc1` |
| CHANGELOG.md latest section | `[0.9.1] - 2026-05-30` | `[1.0.0rc1] - 2026-05-30` |

**Version mismatch status:** The version is internally consistent at `0.9.1` across all files. No mismatch exists between `cheri_cloud_cli.__version__` and `setup.py --version` — both report `0.9.1`. The mission description ("`cheri_cloud_cli.__version__` and `setup.py --version` still show `0.8.0b1`") is stale — version has already been bumped to `0.9.1`.

---

## Git State

```
$ git status --short
?? requirements-dev.txt        (untracked, not staged)
?? system_audit_report/       (untracked, not staged)

$ git branch --show-current
v0.9-s3-e2e-and-type-cleanup

$ git log --oneline -n 10
0942707 chore(release): harden Cheri before v1.0 RC
f16e481 docs: update CHANGELOG for v0.9.0 S3-e2e and type cleanup
13c4e5c feat(storage): verify S3-compatible provider with MinIO e2e
2c61275 docs: add GitHub push report for v0.8.0b1
b8c2ee6 chore(release): prepare Cheri v0.8 public beta
473a267 chore(release): polish Cheri v0.8 public beta
f2e8883 docs: beautify README with badges and improved structure
9a13535 docs: add v0.5.1-handoff-content reports
1c164a3 docs: update handoff docs for v0.5.1 upload/download feature
9fa026f test(handoff): add tests for upload/download and backward compat
```

---

## CHANGELOG Latest Section

```markdown
## [0.9.1] - 2026-05-30 - Final Hardening Before v1.0 RC

### Added
- `scripts/dev/minio-e2e.py` — Python MinIO e2e test harness
- `.gitignore` additions: `*.key`, `*.pem`, `*.env`, `id_rsa*`, etc.

### Changed
- S3-compatible provider status upgraded from "Experimental" to "Beta (MinIO verified)"
- MinIO infrastructure verified

### Fixed
- `HandoffManifest.to_dict()` mypy fix
- `workspace/service.py` TaskDefinition attribute access fix
- `CheriHelpMixin` stub methods for click compatibility

### Known Limitations
- Mypy: 26 errors remain (down from 49). Target of <20 not met.
- Backblaze B2: no implementation class — docs-only
- Direct-to-S3 CLI mode: not implemented
- Multipart upload: declared but not implemented
```

---

## Dirty/Untracked Files

| File | Status | Risk |
|------|--------|------|
| `requirements-dev.txt` | Untracked | Low — dev dependency file, not in gitignore |
| `system_audit_report/` | Untracked | Low — report directory, not in gitignore |

---

## CLI --version

```
$ python -m cheri_cloud_cli.cli --version
Error: No such option: --version
```

The CLI does not have a `--version` flag. The version is only accessible via `python -c "import cheri_cloud_cli; print(cheri_cloud_cli.__version__)"` or `python setup.py --version`.

---

## .gitignore Status

`.gitignore` is well-configured and excludes:
- `dist/`, `build/`, `*.egg-info/`
- `.env`, `*.env`, `credentials.json`, `*.key`, `*.pem`, `id_rsa*`, `id_ed25519*`
- `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `*.log`, `.DS_Store`

**Status:** ✅ PASS

---

## Version Bump Required

All version declarations must change from `0.9.1` to `1.0.0rc1`:
- [ ] `cheri_cloud_cli/__init__.py` line 3
- [ ] `setup.py` line 8
- [ ] `package.json` line 3
- [ ] `README.md` line 9 (version badge)
- [ ] `CHANGELOG.md` top section heading

---

## Audit Verdict

| Check | Status |
|-------|--------|
| Branch | `v0.9-s3-e2e-and-type-cleanup` |
| Version consistency | ✅ Consistent at `0.9.1` |
| Version mismatch | ❌ None — already resolved |
| Dirty files | ⚠️2 untracked files (low risk) |
| .gitignore | ✅ Well-configured |
| CLI --version | ℹ️ Not available |
| Version bump needed | YES — to `1.0.0rc1` |

**Next:** Proceed to Step 2 — Version Bump
