# Version Sync Report

> Date: 2026-05-30

## Commands Run

```bash
python -c "import cheri_cloud_cli; print(cheri_cloud_cli.__version__)"
python setup.py --version
python -m build
```

## Before (Inconsistent)

| Location | Before | After |
|----------|--------|-------|
| `cheri_cloud_cli/__init__.py` | 0.6.0-reliability | 0.8.0b1 |
| `setup.py` | 0.4.0b1 | 0.8.0b1 |
| `package.json` | 0.5.0b1 | 0.8.0b1 |

## After (Consistent)

| Location | Version |
|----------|---------|
| `cheri_cloud_cli/__init__.py` | 0.8.0b1 |
| `setup.py` | 0.8.0b1 |
| `package.json` | 0.8.0b1 |

## Package Build Verification

```
python -m build → cheri-0.8.0b1.tar.gz, cheri-0.8.0b1-py3-none-any.whl
```

Both wheel and sdist now report version 0.8.0b1.

## PEP 440 Compliance

`0.8.0b1` is PEP 440 compliant:
- `0` — major version
- `.8` — minor version
- `.0` — patch version
- `b1` — pre-release (beta 1)

## Result

**PASS** — Version declarations synchronized across all files.