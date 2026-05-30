# MinIO E2E Testing Guide

> Date: 2026-05-30
> Status: **MANUAL_ONLY** — S3-compatible upload/download not yet e2e verified

## Overview

This document describes how to test the S3-compatible provider with MinIO for local development. MinIO is an S3-compatible object storage server that can be run locally via Docker.

## Current S3-Compatible Provider Status

| Feature | Status | Notes |
|---------|--------|-------|
| Config validation | ✅ Implemented | Worker-side validateConfig() works |
| Upload (presigned URL) | ✅ Implemented | Worker returns presigned PUT URL |
| Download (presigned URL) | ✅ Implemented | Worker returns presigned GET URL |
| Full upload e2e | ⚠️ **PENDING** | Requires Cheri CLI → Worker → S3 flow |
| Full download e2e | ⚠️ **PENDING** | Requires Cheri CLI → Worker → S3 flow |
| MinIO infrastructure | ✅ Tested | `scripts/dev/minio-smoke.sh` works |

**Important:** The S3-compatible provider scaffold is in the Worker, but the full CLI → Worker → S3 upload/download flow has not been end-to-end tested.

## S3 Provider Implementation Status

### Worker-side (Complete)
- `worker/storage/providers/s3_compatible.js` — provider class
- `createUploadTarget()` — generates presigned PUT URL
- `createDownloadTarget()` — generates presigned GET URL
- `validateConfig()` — validates S3 credentials and endpoint

### CLI-side (Incomplete)
- Provider config display and selection in CLI
- `CHERI_EXPERIMENTAL_PROVIDERS=1` gate works
- **Upload/download via S3 presigned URLs NOT yet connected**

## Running the MinIO Infrastructure Test

```bash
# Start MinIO and verify basic operations
./scripts/dev/minio-smoke.sh

# Expected output:
# MinIO is ready after ~3s
# CHECKSUM VERIFY: PASSED
# MinIO Infrastructure Test: PASSED
```

This script:
1. Starts a MinIO container on port 9000
2. Creates a test bucket
3. Uploads a test file
4. Downloads and verifies checksum
5. Cleans up on exit

## Manual S3 E2E Test Procedure

Once the full CLI → Worker → S3 flow is implemented, test with:

### 1. Start MinIO
```bash
./scripts/dev/minio-smoke.sh  # In background
# Or manually:
docker run -d --name minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001" --compat
```

### 2. Configure S3-Compatible Provider
```bash
export CHERI_EXPERIMENTAL_PROVIDERS=1
cheri storage configure --provider s3-compatible
# Endpoint: http://localhost:9000
# Bucket: cheri-test (or your bucket name)
# Region: us-east-1
# Access Key: minioadmin
# Secret: minioadmin
# Force path-style: true
```

### 3. Verify Config
```bash
cheri storage check
cheri storage status
```

### 4. Test Upload
```bash
echo "test content" > /tmp/test.txt
cheri file upload /tmp/test.txt
cheri file list
```

### 5. Test Download
```bash
cheri file download test.txt --dest /tmp/downloaded.txt
diff /tmp/test.txt /tmp/downloaded.txt && echo "CHECKSUM OK"
```

## S3-Compatible Provider Configuration Schema

```yaml
kind: s3-compatible
label: S3-compatible
status: experimental
selectable: false  # Requires CHERI_EXPERIMENTAL_PROVIDERS=1
experimental: true

fields:
  - key: endpoint
    label: Endpoint URL
    required: true
    example: "https://s3.amazonaws.com or http://localhost:9000"
  - key: bucket
    label: Bucket name
    required: true
  - key: region
    label: Region
    required: true
    default: "auto"
  - key: access_key_id
    label: Access key id
    required: true
  - key: secret_access_key
    label: Secret access key
    required: true
    secret: true
  - key: force_path_style
    label: Force path-style URLs
    required: false
    description: "Required for MinIO (true) and some S3-compatible backends"
```

## Known Limitations

| Issue | Workaround |
|-------|------------|
| S3 upload/download e2e not tested | Manual verification only until CI setup |
| No MinIO in CI/CD | Requires Docker-in-Docker or external service |
| B2/B3 not end-to-end verified | Docs-only until explicit testing |
| Multipart upload not implemented | Single-part only, 5GB limit |

## Security Notes

- MinIO default credentials (`minioadmin`/`minioadmin`) are for testing only
- Never expose MinIO without authentication in production
- Presigned URLs expire after 10 minutes (grant TTL)
- Secrets stored in KV, not in workspace metadata

## Next Steps for v0.9

1. Implement full CLI → Worker → S3 upload flow
2. Implement full CLI → Worker → S3 download flow
3. Add MinIO to CI/CD for automated testing
4. Verify checksum verification end-to-end
5. Add multipart upload for large files