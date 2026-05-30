# v1 Readiness Gate Script Report

**Date:** 2026-05-30

---

## Summary

Created `scripts/dev/v1-readiness-gate.sh` as a one-stop verification script for v1.0 RC readiness.

---

## Script Location

```
scripts/dev/v1-readiness-gate.sh
```

---

## What It Checks

| Check | Command | Expected Exit |
|-------|---------|---------------|
| Python unit tests | `python -m unittest discover -s tests/python -p "test_*.py"` | 0 |
| Worker Node tests | `node tests/node/worker.test.mjs` | 0 |
| Storage Node tests | `node tests/node/storage.test.mjs` | 0 |
| npm test | `npm test` | 0 |
| ruff lint | `ruff check .` | 0 |
| mypy type check | `mypy cheri_cloud_cli --ignore-missing-imports` | 0 |
| CLI version | `python -m cheri_cloud_cli.cli --help` | 0 |
| setup.py version | `python setup.py --version` | 0 |
| Package build | `python -m build` | 0 |
| twine check | `twine check dist/*` | 0 |

---

## Mypy Debt Handling

The script respects `CHERI_ALLOW_MYPY_DEBT=1` environment variable:
- If set to `1`, mypy errors are allowed (warning instead of failure)
- If not set (default), mypy errors cause gate failure

This allows incremental mypy adoption while keeping the gate honest.

---

## Usage

```bash
# Run all checks
bash scripts/dev/v1-readiness-gate.sh

# Allow mypy debt (for development)
CHERI_ALLOW_MYPY_DEBT=1 bash scripts/dev/v1-readiness-gate.sh
```

---

## Output Format

```
==========================================
Cheri v1.0 Readiness Gate
==========================================

--- Python Tests ---
Checking: Python unit tests ... PASS

--- Node.js Tests ---
Checking: Worker Node tests ... PASS
Checking: Storage Node tests ... PASS

--- npm Tests ---
Checking: npm test ... PASS

--- Linting ---
Checking: ruff check ... PASS

--- Type Checking ---
Checking: mypy type check ... PASS (0 errors)

--- CLI Version ---
Checking: cheri CLI version ... PASS

--- Package Build ---
Checking: python setup.py --version ... PASS
Checking: python build ... PASS

--- Package Distribution Check ---
Checking: twine check dist/* ... PASS

==========================================
Results: 10 passed, 0 failed
==========================================

Gate PASSED - Ready for v1.0 RC
```

---

## Files Created

| File | Purpose |
|------|---------|
| `scripts/dev/v1-readiness-gate.sh` | v1.0 readiness gate script |

---

## Verdict

**PASS** — Gate script created and functional.
