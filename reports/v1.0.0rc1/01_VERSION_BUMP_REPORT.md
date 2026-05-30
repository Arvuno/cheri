# Version Bump Report
**Date:** 2026-05-30
**Target:** `1.0.0rc1`

---

## Files Changed

| File | Change | Line |
|------|--------|------|
| `cheri_cloud_cli/__init__.py` | `0.9.1` → `1.0.0rc1` | 3 |
| `setup.py` | `0.9.1` → `1.0.0rc1` | 8 |
| `package.json` | `0.9.1` → `1.0.0rc1` | 3 |
| `README.md` | Version badge `0.9.1` → `1.0.0rc1` | 9 |
| `README.md` | Status badge "Public Beta" → "Release Candidate" | 8 |
| `README.md` | Status text updated to v1.0.0 RC1 | 37 |
| `README.md` | Provider table updated |48–56 |
| `README.md` | Known limitations updated | 251–261 |
| `README.md` | Roadmap updated | 262–270 |
| `CHANGELOG.md` | New `[1.0.0rc1]` section prepended | 8 |

---

## Verification

```bash
$ python -c "import cheri_cloud_cli; print(cheri_cloud_cli.__version__)"
1.0.0rc1

$ python setup.py --version
1.0.0rc1
```

**Status:** ✅ PASS — All version declarations now report `1.0.0rc1`

---

## PEP 440 Compliance

`1.0.0rc1` is a valid PEP 440 pre-release identifier:
- `1.0.0` — release version
- `rc1` — release candidate 1

Not used: `1.0.0-rc1` (hyphen form), `1.0.0rc.1` (dot form)

---

## Version Bump Verdict

| Check | Status |
|-------|--------|
| `cheri_cloud_cli.__version__` | ✅ `1.0.0rc1` |
| `setup.py --version` | ✅ `1.0.0rc1` |
| `package.json` version | ✅ `1.0.0rc1` |
| README badge | ✅ `1.0.0rc1` |
| CHANGELOG top section | ✅ `[1.0.0rc1]` |
| PEP 440 compliance | ✅ PASS |
| All declarations consistent | ✅ PASS |

**Next:** Step 3 (CHANGELOG & README RC polish — complete) → Step 5 (v1 readiness gate)
