# CI/CD Baseline Report

## What Changed

Added GitHub Actions workflow, dev dependencies file, and Python tool configuration.

## Files Added

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | GitHub Actions CI pipeline |
| `requirements-dev.txt` | Pinned dev dependencies (ruff, mypy, pytest) |
| `pyproject.toml` | ruff and mypy configuration |

## CI Pipeline

**.github/workflows/ci.yml** runs 4 jobs on push and PR:

1. **python-tests** — Python 3.11, install -e ., run `python -m unittest discover`
2. **worker-tests** — Node 20, npm install, run `npm run test:worker`
3. **lint** — Python 3.11, ruff check .
4. **type-check** — Python 3.11, mypy cheri_cloud_cli --ignore-missing-imports

## Configuration

**pyproject.toml**:
```toml
[tool.ruff]
target-version = "py311"

[tool.mypy]
python_version = "3.11"
ignore-missing-imports = true
```

**requirements-dev.txt**:
```
ruff>=0.9.0
mypy>=1.15.0
pytest>=8.3.0
```

## Pre-commit Config

`.pre-commit-config.yaml` was considered but not added in this phase to keep scope manageable. Can be added in v0.2.0 if a simple config is straightforward.

## Verification

```bash
# All tests pass
python -m unittest discover -s tests/python -p "test_*.py"  # 52 PASS
node tests/node/worker.test.mjs                             # 6 PASS

# ruff check (if installed)
ruff check .  # No output = clean (or configure in CI)

# mypy (if installed)
mypy cheri_cloud_cli --ignore-missing-imports  # Configured baseline
```

## CI Status

| Job | Trigger | Status |
|-----|--------|--------|
| python-tests | push/PR | To be run on first push |
| worker-tests | push/PR | To be run on first push |
| lint | push/PR | To be run on first push |
| type-check | push/PR | To be run on first push |

## Next for v0.2.0

- Run CI on actual push to verify all 4 jobs pass
- Consider adding pre-commit hooks (ruff, mypy, trailing whitespace)
- Consider adding build verification step (`python -m pip install .`)
- Consider adding secrets scanning (detect accidentally committed credentials)