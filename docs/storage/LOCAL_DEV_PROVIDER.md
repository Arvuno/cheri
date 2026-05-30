# Local Dev Provider

> Date: 2026-05-30
> Status: **TEST-ONLY** — not for production use

## Overview

The Local Dev provider is a test adapter that stores all blobs in an in-memory `Map`. It exists solely to enable Worker tests without Cloudflare credentials or R2 binding configuration.

**WARNING:** Blobs are lost when the Worker instance restarts. This provider must never be used in production.

## Status

- **Status:** experimental (test-only)
- **Selectable:** No — not available via CLI in any deployment mode
- **Use cases:** Worker unit tests, integration tests, local development without cloud credentials

## Implementation

```javascript
// worker/storage/providers/local_dev.js

export class LocalDevStorageProvider {
  constructor(env, providerConfig, definition) {
    this._store = new Map();  // In-memory blob store
  }

  async putObject({ providerObjectKey, body, contentType, metadata }) {
    // Stores as Uint8Array in memory
    const data = await body.arrayBuffer();
    this._store.set(providerObjectKey, { data, contentType, metadata });
    return { provider_object_key: providerObjectKey, provider_object_id: providerObjectKey };
  }

  async getObject({ providerObjectKey }) {
    const entry = this._store.get(providerObjectKey);
    if (!entry) return null;
    return {
      body: entry.data,
      size: entry.data.byteLength,
      content_type: entry.contentType,
      provider_object_key: providerObjectKey,
      provider_object_id: providerObjectKey,
    };
  }
}
```

## Capabilities

| Capability | Supported |
|---|---|
| putObject | ✅ |
| getObject | ✅ |
| deleteObject | ✅ |
| listObjects | ✅ |
| headObject | ✅ |
| createUploadTarget | ✅ (worker_proxy mode) |
| createDownloadTarget | ✅ (worker_proxy mode) |
| signed URLs | ❌ |
| multipart | ❌ |

## Testing with LocalDevProvider

```javascript
import { LocalDevStorageProvider } from "./worker/storage/providers/local_dev.js";

const provider = new LocalDevStorageProvider(env, providerConfig, definition);
const validation = await provider.validateConfig();
// { state: "ready", available: true, errors: [], warnings: [...] }
```

## Limitations

- No persistence across worker restarts
- No actual cloud storage operations
- Not selectable via CLI
- No signed URL support
- No multipart upload
- No server-side copy