# v0.3.0-provider-beta — Index

## Status

**NOT STARTED** — pending v0.2.0 exit criteria confirmation.

## Planned Reports

| # | Report | Scope |
|---|---|---|
| 01 | [Provider Beta Verdict](01_PROVIDER_BETA_VERDICT.md) | Overall assessment after v0.3 |
| 02 | [Storage Config UX Report](02_STORAGE_CONFIG_UX_REPORT.md) | configure command design |
| 03 | [S3-Compatible Status Report](03_S3_COMPATIBLE_STATUS_REPORT.md) | S3 provider completion status |
| 04 | [MinIO Support Report](04_MINIO_SUPPORT_REPORT.md) | MinIO self-hosted setup |
| 05 | [B2 Compatibility Report](05_B2_COMPATIBILITY_REPORT.md) | Backblaze B2 path |
| 06 | [Storage Migration Dry-Run Report](06_STORAGE_MIGRATION_DRY_RUN_REPORT.md) | Migration CLI design |
| 07 | [Security and Secret Redaction Report](07_SECURITY_AND_SECRET_REDACTION_REPORT.md) | Secrets never leaked |
| 08 | [Test Results Report](08_TEST_RESULTS_REPORT.md) | v0.3 test results |
| 09 | [Next v0.4 Dev Workspace Plan](09_NEXT_V0_4_DEV_WORKSPACE_PLAN.md) | Future roadmap |

## Exit Criteria (from spec)

- Users can see provider options via `cheri storage providers`
- System provider remains safe default
- Experimental providers are gated behind flag/confirmation
- S3-compatible path is either beta-working or honestly marked `not_ready`
- MinIO and B2 paths documented
- No provider secrets leak in CLI/API/test output