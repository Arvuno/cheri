# v1.0.0 Final — Next Post-v1 Plan

**Date:** 2026-05-30

---

## After v1.0.0 Stable is Released

### Immediate Post-Release (v1.0.x)

| Item | Priority | Notes |
|------|----------|-------|
| PyPI publish | HIGH | Requires `OWNER_APPROVES_PYPI_PUBLISH=YES` |
| Documentation hosting | MEDIUM | GitHub Pages or readthedocs.org |
| CLI man page | LOW | For Linux distribution packaging |
| Changelog automation | LOW | `cz bump` or similar |

---

### v1.1 — Near Term

| Feature | Priority | Notes |
|---------|----------|-------|
| Bidirectional sync | HIGH | Upload-only is limiting for active teams |
| Conflict resolution UI | HIGH | Required for bidirectional sync |
| Multipart upload | MEDIUM | For large file support |
| PyPI package maintenance | MEDIUM | Set up automated release pipeline |

---

### v1.x — Mid Term

| Feature | Priority | Notes |
|---------|----------|-------|
| Google Drive provider | MEDIUM | Most requested integration |
| Direct-to-S3 CLI mode | MEDIUM | Bypass worker proxy for S3-compatible |
| Backblaze B2 native | LOW | Depends on S3-compatible maturity |
| Web dashboard | LOW | Beyond CLI-first scope |

---

### Security Hardening (Ongoing)

| Item | Priority | Notes |
|------|----------|-------|
| Encrypt secrets at rest | HIGH | Local credential store security |
| Audit logging | MEDIUM | Compliance for enterprise teams |
| 2FA / MFA support | MEDIUM | Team security |

---

## Current Branch / Repo Notes

- Branch: `v0.9-s3-e2e-and-type-cleanup` — consider renaming to `main` after release
- Remote: `https://github.com/Arvuno/cheri.git`
- Release artifacts: `dist/cheri-1.0.0.tar.gz`, `dist/cheri-1.0.0-py3-none-any.whl`

---

## Not in Scope for v1.x

- Dropbox replacement feature parity
- Mobile app
- Self-hosted backend without Cloudflare
- Enterprise SSO / SAML
- End-to-end encryption
