# Provider Capability Truth Report

**Date:** 2026-05-30
**Branch:** `v0.9-s3-e2e-and-type-cleanup`

---

## Summary

Provider capability declarations were audited against actual implementation. Several false claims were found and corrected.

---

## Truth Matrix (After Fixes)

| Capability | System (R2) | S3-compatible | Local Dev |
|------------|-------------|---------------|-----------|
| upload | ✅ true | ✅ true | ✅ true |
| download | ✅ true | ✅ true | ✅ true |
| delete | ✅ true | ✅ true | ✅ true |
| list | ✅ true | ✅ true | ✅ true |
| signedUploadUrl | ❌ false | ⚠️ internal | ❌ false |
| signedDownloadUrl | ❌ false | ⚠️ internal | ❌ false |
| multipart | ❌ false | ❌ false | ❌ false |
| checksum | ❌ false | ✅ true | ❌ false |
| serverSideCopy | ❌ false | ❌ false | ❌ false |

---

## Changes Made

### 1. `worker/storage/types.js` — `CAPABILITIES_S3_COMPATIBLE`

**Before:**
```javascript
export const CAPABILITIES_S3_COMPATIBLE = {
  signedUploadUrl: true,
  signedDownloadUrl: true,
  multipart: true,
  checksum: true,
  serverSideCopy: true,
};
```

**After:**
```javascript
// NOTE: signedUploadUrl/signedDownloadUrl are generated internally by the provider
// but CLI does NOT use direct-to-S3 presigned URL mode — all transfers go through worker proxy.
// multipart upload is NOT implemented.
// serverSideCopy is NOT implemented.
export const CAPABILITIES_S3_COMPATIBLE = {
  signedUploadUrl: "internal", // CLI uses worker-proxy; presigned URLs exist internally
  signedDownloadUrl: "internal", // CLI uses worker-proxy; presigned URLs exist internally
  multipart: false, // Not implemented
  checksum: true, // Verified via SHA256 in MinIO e2e
  serverSideCopy: false, // Not implemented
};
```

###2. `worker/storage/registry.js` — `getProviderCapabilities()`

**Before:**
```javascript
signedUploadUrl: kind === "s3-compatible",
signedDownloadUrl: kind === "s3-compatible",
multipart: kind === "s3-compatible",
```

**After:**
```javascript
signedUploadUrl: kind === "s3-compatible" ? "internal" : false,
signedDownloadUrl: kind === "s3-compatible" ? "internal" : false,
multipart: false, // Not implemented for any provider
```

### 3. `docs/storage/PROVIDER_MATRIX.md`

- Changed multipart from ✅ to ❌ for S3-compatible
- Changed signed URL columns to ⚠️ internal for S3-compatible
- Added note about not implemented: Multipart upload, server-side copy, CLI direct-to-S3 presigned URL mode

---

## Files Changed

| File | Change |
|------|--------|
| `worker/storage/types.js` | Fixed `CAPABILITIES_S3_COMPATIBLE` capability declarations |
| `worker/storage/registry.js` | Fixed `getProviderCapabilities()` return values |
| `docs/storage/PROVIDER_MATRIX.md` | Updated capability matrix to reflect truth |

---

## Provider Status After Fixes

| Provider | Status | Notes |
|----------|--------|-------|
| System (R2) | ✅ Ready | Default provider, production-ready |
| S3-compatible | ⚠️ Beta (MinIO verified) | Worker-proxy flow tested, presigned URLs internal only |
| Local Dev | 🔧 Experimental | Test-only, not selectable |
| Backblaze B2 | 📄 Docs-only | No implementation class |
| Google Drive | 📄 Not Ready | Not implemented |

---

## Verdict

**PASS** — All provider capability claims now match implementation reality.
- Multipart: correctly marked as false
- Signed URLs: correctly marked as "internal" (not CLI-direct)
- serverSideCopy: correctly marked as false
- checksum: true for S3-compatible (verified via MinIO e2e)
