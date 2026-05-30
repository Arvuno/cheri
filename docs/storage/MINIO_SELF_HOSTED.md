# MinIO Self-Hosted Setup

> Date: 2026-05-30
> Status: experimental — requires S3-compatible provider

## Overview

MinIO is an S3-compatible object storage server that teams can self-host for local development or private deployments. Cheri supports MinIO via the `s3-compatible` provider with `force_path_style: true`.

## Quick Start

### 1. Start MinIO

```bash
# Docker
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"

# Or docker-compose.yml
```

### 2. Create a bucket

Using MinIO Console (http://localhost:9001) or mc CLI:

```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/cheri-workspace
mc anonymous set download local/cheri-workspace  # Optional: public read
```

### 3. Configure Cheri

```bash
cheri storage configure --provider s3-compatible
# Endpoint: http://localhost:9000
# Bucket: cheri-workspace
# Region: us-east-1
# Access key: minioadmin
# Secret: minioadmin
# Force path-style: true
```

### 4. Verify

```bash
cheri storage check
cheri storage status
```

## MinIO Configuration Fields

| Field | Value for MinIO |
|---|---|
| `endpoint` | `http://localhost:9000` |
| `bucket` | Your bucket name |
| `region` | `us-east-1` (or any value) |
| `access_key_id` | `minioadmin` (default) |
| `secret_access_key` | `minioadmin` (default) |
| `force_path_style` | `true` — **required** for MinIO |

## Production Credentials Warning

> **Never use `minioadmin`/`minioadmin` in production.**

Create a dedicated user with least-privilege access:

```bash
mc alias set local http://localhost:9000 $(MINIO_ROOT_USER) $(MINIO_ROOT_PASSWORD)
mc user add local cheri-user --password "secure-password"
mc policy attach local/readwrite cheri-user
```

## Architecture Notes

- MinIO does not support presigned URLs in the same way as AWS S3 in all versions. Test your MinIO version.
- `force_path_style: true` is required because MinIO doesn't support virtual-hosted-style URLs by default.
- MinIO's S3 compatibility mode must be enabled: `minio server /data --compat`

## Health Check

```bash
mc ls local/cheri-workspace
```

## Limitations

- MinIO is experimental in v0.2.0/v0.3.0
- File reset/cleanup uses standard delete — MinIO lifecycle rules are not integrated
- Large file support depends on MinIO's maximum object size configuration