# v0.1.0 Foundation Index

**Product**: Cheri — CLI-first collaborative workspace sync for developer teams
**Version**: 0.1.0b1
**Release Date**: 2026-05-30
**Status**: Beta foundation — upload-only, System provider only

## Phase Summary

v0.1.0-foundation establishes the legal, security, testing, and CI/CD baseline necessary to publish Cheri as a release-trackable beta. No bidirectional sync, no non-System providers in the public flow.

## Reports

| Report | Status |
|--------|--------|
| 01_RELEASE_VERDICT.md | Final verdict and readiness assessment |
| 02_SECURITY_CREDENTIAL_STORAGE_REPORT.md | Keyring store, migration, fallback |
| 03_SECRET_SAFE_SCANNING_REPORT.md | Default exclusions, tests, warnings |
| 04_WORKER_TESTING_REPORT.md | Node worker tests and route coverage |
| 05_CI_CD_REPORT.md | GitHub Actions, ruff, mypy baseline |
| 06_PROVIDER_GATING_REPORT.md | System-only enforcement, experimental flags |
| 07_DOCUMENTATION_CHANGELOG_REPORT.md | README, CHANGELOG, docs updates |
| 08_REMAINING_RISKS_AND_NEXT_VERSION_PLAN.md | Open risks, v0.2.0 recommendations |

## Verification Commands Run

```bash
python -m unittest discover -s tests/python -p "test_*.py"  # 52 tests, all PASS
node tests/node/worker.test.mjs                               # 6 test cases, all PASS
```

## Files Changed Summary

- `LICENSE` — MIT License added
- `setup.py` — version 0.1.0b1, python_requires>=3.11, description updated
- `cheri_cloud_cli/__init__.py` — __version__ = "0.1.0b1"
- `package.json` — version 0.1.0b1
- `cheri_cloud_cli/cli.py` — --version flag working, KeyringCredentialStore imported
- `cheri_cloud_cli/sessions/store.py` — KeyringCredentialStore added with migration and fallback
- `cheri_cloud_cli/sessions/__init__.py` — KeyringCredentialStore exported
- `cheri_cloud_cli/task/runtime.py` — 13 secret-safe exclude patterns added, skipped_sensitive tracking
- `cheri_cloud_cli/services/task_service.py` — TaskExecutionResult.skipped_sensitive field
- `cheri_cloud_cli/task/service.py` — warning output when sensitive files are skipped
- `tests/python/test_store.py` — 10 new tests for keyring store
- `tests/python/test_task_runtime.py` — 19 new tests for path filtering and scanning
- `.github/workflows/ci.yml` — CI/CD workflow added
- `requirements-dev.txt` — dev dependencies
- `pyproject.toml` — ruff and mypy config
- `CHANGELOG.md` — v0.1.0b1 entry
- `docs/RELEASE_PROCESS.md` — release process
- `docs/SECURITY.md` — security documentation
- `docs/ROADMAP.md` — roadmap to v1.0.0

## Exit Criteria: All Met

- [x] License exists (MIT)
- [x] Credentials not stored as plaintext when keyring available
- [x] `.env` and common secret files excluded from task scanning by default
- [x] Worker tests run (6/6 passing)
- [x] Python tests pass (52/52 passing)
- [x] CI workflow exists (GitHub Actions)
- [x] Non-System providers not misleadingly exposed (System-only default, coming_soon labels)
- [x] README accurately describes product limitations (beta, upload-only, System-only)
- [x] v0.1.0-foundation reports exist (8/8)