# Unsupported Claims Cleanup Report

**Date:** 2026-05-30

---

## Summary

Removed or corrected false capability claims found in documentation and code.

---

## Claims Found and Fixed

### 1. S3-compatible `multipart: true` ❌ → Fixed to `false`

**Location:** `worker/storage/types.js`, `worker/storage/registry.js`, `docs/storage/PROVIDER_MATRIX.md`

**Issue:** The S3-compatible provider declared `multipart: true` in its capabilities, but the implementation does NOT implement multipart upload.

**Fix:** Changed to `multipart: false` with explanatory comment.

---

### 2. S3-compatible `signedUploadUrl/signedDownloadUrl: true` → Fixed to `"internal"`

**Location:** `worker/storage/types.js`, `worker/storage/registry.js`, `docs/storage/PROVIDER_MATRIX.md`

**Issue:** The S3-compatible provider generates presigned URLs internally via `createUploadTarget()`/`createDownloadTarget()`, but the CLI does NOT use direct-to-S3 presigned URL mode. All transfers go through the worker proxy.

**Fix:** Changed to `"internal"` with comment explaining that CLI uses worker-proxy flow, not direct-to-S3.

---

### 3. S3-compatible `serverSideCopy: true` ❌ → Fixed to `false`

**Location:** `worker/storage/types.js`

**Issue:** Declared but not implemented in the S3-compatible provider class.

**Fix:** Changed to `serverSideCopy: false`.

---

### 4. Direct-to-S3 CLI mode mentioned as available → Clarified

**Location:** `docs/storage/PROVIDER_MATRIX.md`, `CHANGELOG.md`

**Issue:** Documentation implied CLI could use presigned URLs directly for S3 transfers.

**Fix:** Updated docs to clarify that presigned URLs are generated internally by the provider but CLI uses worker-proxy transfer flow exclusively.

---

## README Status

The README.md correctly states:
- "S3-compatible upload/download e2e pending" (⚠️ Experimental)
- "Google Drive, Backblaze B2 are docs-only"
- "Upload-only sync (no bidirectional yet)"

No changes needed to README - it was already honest about limitations.

---

## CHANGELOG Status

The CHANGELOG correctly documents:
- "Direct-to-S3 (CLI using presigned URL directly): not implemented — all transfers go through worker proxy"
- "Multipart upload: declared in capabilities but not implemented in S3-compatible provider"

No changes needed to CHANGELOG - it was already honest.

---

## Verdict

**PASS** — All unsupported capability claims have been removed or corrected.
- multipart claim removed from S3-compatible
- Direct-to-S3 CLI mode clarified as not implemented
- serverSideCopy claim removed from S3-compatible
