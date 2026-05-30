# v0.3.1-provider-beta-rescue — Index

## Reports

- [01_PROVIDER_BETA_RESCUE_VERDICT.md](./01_PROVIDER_BETA_RESCUE_VERDICT.md)
- [02_STORAGE_CONFIGURE_COMMAND_REPORT.md](./02_STORAGE_CONFIGURE_COMMAND_REPORT.md)
- [03_WORKER_PROVIDER_CONFIG_API_REPORT.md](./03_WORKER_PROVIDER_CONFIG_API_REPORT.md)
- [04_PROVIDER_SECRET_ENCRYPTION_REPORT.md](./04_PROVIDER_SECRET_ENCRYPTION_REPORT.md)
- [05_S3_COMPATIBLE_BETA_STATUS_REPORT.md](./05_S3_COMPATIBLE_BETA_STATUS_REPORT.md)
- [06_MINIO_B2_COMPATIBILITY_REPORT.md](./06_MINIO_B2_COMPATIBILITY_REPORT.md)
- [07_STORAGE_MIGRATION_DRY_RUN_REPORT.md](./07_STORAGE_MIGRATION_DRY_RUN_REPORT.md)
- [08_TEST_RESULTS_REPORT.md](./08_TEST_RESULTS_REPORT.md)
- [09_IMPACT_ON_V0_4_AND_V0_5_REPORT.md](./09_IMPACT_ON_V0_4_AND_V0_5_REPORT.md)

## Summary

v0.3.1 closes the missing provider-beta layer from v0.3.0. The implementation
was verified against the hard rules and all constraints. See verdict for details.

## Decision

**READY_WITH_LIMITATIONS**

- v0.3 is no longer NOT STARTED
- Provider configure/use flow exists end-to-end
- Provider secrets are AES-GCM encrypted when `CHERI_PROVIDER_SECRET_KEY` is set
- System provider remains working
- Experimental providers are gated behind `--include-experimental`
- MinIO/B2/S3 status is honest (beta/config-only)