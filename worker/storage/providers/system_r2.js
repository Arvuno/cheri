// System storage provider backed by Cloudflare R2.
// Uses HERMES_BUCKET binding for blob operations.
// Status: ready

import { BaseStorageProvider } from "./base.js";
import { CAPABILITIES_SYSTEM, buildValidationResult } from "../types.js";
import { StorageObjectNotFoundError } from "../errors.js";

export class SystemStorageProvider extends BaseStorageProvider {
  constructor(env, providerConfig, definition) {
    super(env, providerConfig, definition);
    this._capabilities = CAPABILITIES_SYSTEM;
  }

  get capabilities() {
    return this._capabilities;
  }

  async validateConfig() {
    if (!this.env?.HERMES_BUCKET) {
      return buildValidationResult({
        state: "misconfigured",
        available: false,
        errors: ["HERMES_BUCKET is not configured in this deployment."],
        warnings: [],
      });
    }
    return buildValidationResult({
      state: "ready",
      available: true,
      errors: [],
      warnings: ["System storage is temporary. Files are reset daily."],
    });
  }

  async putObject({ providerObjectKey, body, contentType, metadata = {} }) {
    await this.env.HERMES_BUCKET.put(providerObjectKey, body, {
      httpMetadata: { contentType },
      customMetadata: metadata,
    });
    return {
      provider_object_key: providerObjectKey,
      provider_object_id: providerObjectKey,
    };
  }

  async getObject({ providerObjectKey }) {
    const object = await this.env.HERMES_BUCKET.get(providerObjectKey);
    if (!object) {
      throw new StorageObjectNotFoundError(`Object not found: ${providerObjectKey}`);
    }
    return {
      body: object.body,
      size: object.size,
      content_type: httpMetadataToContentType(object.httpMetadata),
      etag: object.etag || "",
      uploaded_at: object.uploaded?.toISOString?.() || "",
      provider_object_key: providerObjectKey,
      provider_object_id: providerObjectKey,
    };
  }

  async deleteObject({ providerObjectKey }) {
    try {
      await this.env.HERMES_BUCKET.delete(providerObjectKey);
    } catch (err) {
      // R2 delete is idempotent — if the object is already gone, that's fine.
      // We treat NOT_FOUND as success.
      if (err?.message?.includes("NotFound") || err?.code === "NoSuchKey") {
        return;
      }
      throw err;
    }
  }

  async listObjects({ prefix = "" } = {}) {
    const listed = await this.env.HERMES_BUCKET.list({ prefix });
    return {
      objects: (listed.objects || []).map((object) => ({
        provider_object_key: object.key,
        provider_object_id: object.key,
        size: object.size || 0,
        uploaded_at: object.uploaded?.toISOString?.() || "",
        etag: object.etag || "",
      })),
      has_more: !!listed.truncated,
      next_cursor: listed.truncated ? listed.cursor : undefined,
    };
  }

  async headObject({ providerObjectKey }) {
    const head = await this.env.HERMES_BUCKET.head(providerObjectKey);
    if (!head) {
      return null;
    }
    return {
      provider_object_key: providerObjectKey,
      provider_object_id: providerObjectKey,
      size: head.size || 0,
      content_type: httpMetadataToContentType(head.httpMetadata),
      etag: head.etag || "",
      uploaded_at: head.uploaded?.toISOString?.() || "",
    };
  }

  async copyObject({ sourceKey, destKey }) {
    // R2 does not support server-side copy in the same way as S3.
    // We re-upload by streaming from the source object.
    const source = await this.env.HERMES_BUCKET.get(sourceKey);
    if (!source) {
      throw new StorageObjectNotFoundError(`Source object not found: ${sourceKey}`);
    }
    const contentType = httpMetadataToContentType(source.httpMetadata);
    await this.env.HERMES_BUCKET.put(destKey, source.body, {
      httpMetadata: { contentType },
    });
  }
}

function httpMetadataToContentType(metadata = {}) {
  return metadata.contentType || metadata.content_type || "application/octet-stream";
}