# Phase 9: Known Limitations Report

## Honest Limitations

| Limitation | Severity | Notes |
|---|---|---|
| No PyPI publish | Blocking | Requires owner approval |
| S3-compatible upload/download not tested | Beta | Config validation works; transfer not e2e |
| MinIO/B2 file transfer not implemented | Beta | Docs only |
| Bidirectional sync not available | Feature gap | Upload-only is accurate |
| System provider is temporary | Limitation | Daily reset — not for production data |
| Keyring not available | Warning | Falls back to file storage |
| mypy type errors (35+) | Tech debt | Pre-existing, not introduced this release |
| ruff style errors (54) | Tech debt | 36 auto-fixable with --fix |

## Beta Claims (Verified Accurate)

- System provider: ready (default)
- S3-compatible: beta (config works, transfer scaffolded)
- Experimental providers: properly gated
- Secret-safe scanning: default on
- No bidirectional sync: confirmed (upload-only)

## Verdict

Limitations are documented and honest. No hidden blockers.
