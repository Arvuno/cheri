// Local development storage provider.
// ** TEST-ONLY ** — not for production use.
// Uses an in-memory Map to simulate blob storage.
// Useful for local testing and development without Cloudflare credentials.

import { buildValidationResult } from "../types.js";

/**
 * LocalDevStorageProvider — test adapter for local development.
 *
 * WARNING: This provider stores all blobs in process memory.
 * Blobs are lost on worker restart. Files are not persisted.
 * DO NOT use in production.
 *
 * Status: experimental (test-only)
 */
export class LocalDevStorageProvider {
  constructor(env, providerConfig, definition) {
    this.env = env;
    this.providerConfig = providerConfig;
    this.definition = definition;
    this._store = new Map();
  }

  get id() {
    return "local-dev";
  }

  get label() {
    return "Local Dev (test-only)";
  }

  get status() {
    return "experimental";
  }

  get capabilities() {
    return {
      upload: true,
      download: true,
      delete: true,
      list: true,
      signedUploadUrl: false,
      signedDownloadUrl: false,
      multipart: false,
      checksum: false,
      serverSideCopy: false,
    };
  }

  async validateConfig() {
    return buildValidationResult({
      state: "ready",
      available: true,
      errors: [],
      warnings: [
        "Local Dev provider is for testing only. Blobs are not persisted.",
      ],
    });
  }

  async putObject({ providerObjectKey, body, contentType, metadata = {} }) {
    // Store the body as a Uint8Array in memory
    let data;
    if (body instanceof Uint8Array) {
      data = body;
    } else if (body instanceof ArrayBuffer) {
      data = new Uint8Array(body);
    } else if (typeof body === "string") {
      data = new TextEncoder().encode(body);
    } else {
      // Assume it's a ReadableStream or something with arrayBuffer()
      const arrayBuffer = await body.arrayBuffer();
      data = new Uint8Array(arrayBuffer);
    }

    this._store.set(providerObjectKey, {
      data,
      contentType: contentType || "application/octet-stream",
      metadata,
      storedAt: new Date().toISOString(),
    });

    return {
      provider_object_key: providerObjectKey,
      provider_object_id: providerObjectKey,
    };
  }

  async getObject({ providerObjectKey }) {
    const entry = this._store.get(providerObjectKey);
    if (!entry) {
      return null;
    }
    return {
      body: entry.data,
      size: entry.data.byteLength,
      content_type: entry.contentType,
      etag: `local-${providerObjectKey}`,
      uploaded_at: entry.storedAt,
      provider_object_key: providerObjectKey,
      provider_object_id: providerObjectKey,
    };
  }

  async deleteObject({ providerObjectKey }) {
    this._store.delete(providerObjectKey);
  }

  async listObjects({ prefix = "" } = {}) {
    const objects = [];
    for (const [key, entry] of this._store.entries()) {
      if (prefix && !key.startsWith(prefix)) {
        continue;
      }
      objects.push({
        provider_object_key: key,
        provider_object_id: key,
        size: entry.data.byteLength,
        content_type: entry.contentType,
        etag: `local-${key}`,
        uploaded_at: entry.storedAt,
      });
    }
    return { objects, has_more: false };
  }

  async headObject({ providerObjectKey }) {
    const entry = this._store.get(providerObjectKey);
    if (!entry) {
      return null;
    }
    return {
      provider_object_key: providerObjectKey,
      provider_object_id: providerObjectKey,
      size: entry.data.byteLength,
      content_type: entry.contentType,
      etag: `local-${providerObjectKey}`,
      uploaded_at: entry.storedAt,
    };
  }

  async createUploadTarget({ workspace, file, expires_at }) {
    return {
      mode: "worker_proxy",
      provider_object_key: file.provider_object_key,
      provider_object_id: file.provider_object_id,
      headers: {},
      expires_at,
    };
  }

  async createDownloadTarget({ workspace, file, expires_at }) {
    return {
      mode: "worker_proxy",
      provider_object_key: file.provider_object_key,
      provider_object_id: file.provider_object_id,
      headers: {},
      expires_at,
    };
  }

  // Test-only helpers
  _clearAll() {
    this._store.clear();
  }

  _getSize() {
    return this._store.size;
  }
}