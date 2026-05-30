# Backblaze B2 via S3-Compatible API

> Date: 2026-05-30
> Status: experimental — requires S3-compatible provider

## Overview

Backblaze B2 cloud storage can be used through its S3-compatible API. Since B2's S3 compatibility is just another S3 endpoint, the `s3-compatible` provider handles it with appropriate configuration.

## Setup

### 1. Create a B2 bucket

1. Sign up at https://www.backblaze.com/b2/cloud-storage.html
2. Create a bucket (e.g., `cheri-workspace`)
3. Enable S3-compatible API in bucket settings

### 2. Get API credentials

1. Go to App Keys page
2. Create a new application key with access to the bucket
3. Note the `keyID` and `applicationKey`

### 3. Configure Cheri

```bash
cheri storage configure --provider s3-compatible
# Endpoint: https://s3.us-west-002.backblazeb2.com  (use your region's endpoint)
# Bucket: cheri-workspace
# Region: us-west-002  (your bucket's region)
# Access key: <keyID>
# Secret: <applicationKey>
# Force path-style: false  (B2 supports virtual-hosted-style)
```

## B2 S3-Compatible Endpoint

| Region | Endpoint |
|---|---|
| us-west-002 | `https://s3.us-west-002.backblazeb2.com` |
| us-west-001 | `https://s3.us-west-001.backblazeb2.com` |
| eu-central-001 | `https://s3.eu-central-001.backblazeb2.com` |

Check B2 documentation for your bucket's actual endpoint.

## Differences from AWS S3

- B2 uses `keyID` as the access key (not an AWS-style access key ID)
- B2 uses `applicationKey` as the secret
- B2 requires `Content-Type` header for uploads
- B2's free tier includes 10 GB storage, 30 GB downloads/month

## Configuration Example

```json
{
  "kind": "s3-compatible",
  "settings": {
    "endpoint": "https://s3.us-west-002.backblazeb2.com",
    "bucket": "my-cheri-bucket",
    "region": "us-west-002",
    "access_key_id": "K002...XXX",
    "secret_access_key": "001...XXX",
    "force_path_style": false
  }
}
```

## Security Notes

- B2 application keys should be stored as secrets (KV, not workspace metadata)
- B2 bucket is private by default — Cheri's signed URL mechanism provides temporary access
- Do not use the master application key; create bucket-specific keys