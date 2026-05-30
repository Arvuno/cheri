// S3-compatible storage provider.
// Status: experimental — not ready for production use.
// Requires: endpoint, bucket, region, access_key_id, secret_access_key.

import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand, HeadObjectCommand, ListObjectsV2Command } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

import { buildValidationResult, CAPABILITIES_S3_COMPATIBLE } from "../types.js";
import { ProviderConfigInvalidError, ProviderSecretMissingError, StorageObjectNotFoundError } from "../errors.js";

export class S3CompatibleStorageProvider {
  constructor(env, providerConfig, definition) {
    this.env = env;
    this.providerConfig = providerConfig;
    this.definition = definition;
    this._client = null;
    this._capabilities = CAPABILITIES_S3_COMPATIBLE;
  }

  get id() {
    return "s3-compatible";
  }

  get label() {
    return "S3-compatible";
  }

  get status() {
    return "experimental";
  }

  get capabilities() {
    return this._capabilities;
  }

  /**
   * Lazily create and configure the S3 client.
   * @returns {S3Client}
   */
  getClient() {
    if (this._client) {
      return this._client;
    }

    const settings = this.providerConfig?.settings || {};
    const endpoint = String(settings.endpoint || "").trim();
    const region = String(settings.region || "auto").trim();
    const accessKeyId = String(settings.access_key_id || "").trim();
    const secretAccessKey = String(settings.secret_access_key || "").trim();

    if (!endpoint) {
      throw new ProviderConfigInvalidError("S3 endpoint is required.");
    }
    if (!accessKeyId || !secretAccessKey) {
      throw new ProviderSecretMissingError("S3 access key or secret is missing.");
    }

    const clientConfig = {
      endpoint,
      region,
      credentials: {
        accessKeyId,
        secretAccessKey,
      },
      forcePathStyle: !!settings.force_path_style, // Required for MinIO
    };

    this._client = new S3Client(clientConfig);
    return this._client;
  }

  async validateConfig() {
    const settings = this.providerConfig?.settings || {};
    const endpoint = String(settings.endpoint || "").trim();
    const bucket = String(settings.bucket || "").trim();
    const region = String(settings.region || "auto").trim();
    const accessKeyId = String(settings.access_key_id || "").trim();
    const secretAccessKey = String(settings.secret_access_key || "").trim();

    const errors = [];
    const warnings = [];

    if (!endpoint) {
      errors.push("S3 endpoint is required.");
    } else if (!/^https?:\/\//i.test(endpoint)) {
      warnings.push("S3 endpoint should use https:// for security.");
    }

    if (!bucket) {
      errors.push("S3 bucket name is required.");
    }

    if (!accessKeyId || !secretAccessKey) {
      errors.push("S3 access key and secret are required.");
    }

    if (errors.length > 0) {
      return buildValidationResult({
        state: "misconfigured",
        available: false,
        errors,
        warnings,
      });
    }

    // Try to verify connectivity by listing the bucket
    try {
      const client = this.getClient();
      const command = new ListObjectsV2Command({ Bucket: bucket, MaxKeys: 1 });
      await client.send(command);
      return buildValidationResult({
        state: "ready",
        available: true,
        errors: [],
        warnings: ["S3-compatible provider is experimental. Use with caution."],
      });
    } catch (err) {
      return buildValidationResult({
        state: "misconfigured",
        available: false,
        errors: [`S3 bucket is not reachable: ${err?.message || String(err)}`],
        warnings,
      });
    }
  }

  async putObject({ providerObjectKey, body, contentType, metadata = {}) {
    try {
      const client = this.getClient();
      const bucket = this.providerConfig?.settings?.bucket;

      let bodyData;
      if (body instanceof Uint8Array) {
        bodyData = body;
      } else if (body instanceof ArrayBuffer) {
        bodyData = new Uint8Array(body);
      } else if (typeof body === "string") {
        bodyData = new TextEncoder().encode(body);
      } else {
        const arrayBuffer = await body.arrayBuffer();
        bodyData = new Uint8Array(arrayBuffer);
      }

      const command = new PutObjectCommand({
        Bucket: bucket,
        Key: providerObjectKey,
        Body: bodyData,
        ContentType: contentType,
        Metadata: metadata,
      });

      await client.send(command);

      return {
        provider_object_key: providerObjectKey,
        provider_object_id: providerObjectKey,
      };
    } catch (err) {
      throw new Error(`S3 put failed: ${err?.message || String(err)}`);
    }
  }

  async getObject({ providerObjectKey }) {
    try {
      const client = this.getClient();
      const bucket = this.providerConfig?.settings?.bucket;

      const command = new GetObjectCommand({
        Bucket: bucket,
        Key: providerObjectKey,
      });

      const response = await client.send(command);
      const body = await response.Body.transformToUint8Array();

      return {
        body,
        size: response.ContentLength || body.byteLength,
        content_type: response.ContentType || "application/octet-stream",
        etag: response.ETag || "",
        uploaded_at: response.LastModified?.toISOString() || "",
        provider_object_key: providerObjectKey,
        provider_object_id: providerObjectKey,
      };
    } catch (err) {
      if (err?.name === "NoSuchKey" || err?.$metadata?.httpStatusCode === 404) {
        throw new StorageObjectNotFoundError(`Object not found: ${providerObjectKey}`);
      }
      throw new Error(`S3 get failed: ${err?.message || String(err)}`);
    }
  }

  async deleteObject({ providerObjectKey }) {
    try {
      const client = this.getClient();
      const bucket = this.providerConfig?.settings?.bucket;

      const command = new DeleteObjectCommand({
        Bucket: bucket,
        Key: providerObjectKey,
      });

      await client.send(command);
    } catch (err) {
      if (err?.name === "NoSuchKey" || err?.$metadata?.httpStatusCode === 404) {
        // Idempotent — already gone is fine
        return;
      }
      throw new Error(`S3 delete failed: ${err?.message || String(err)}`);
    }
  }

  async headObject({ providerObjectKey }) {
    try {
      const client = this.getClient();
      const bucket = this.providerConfig?.settings?.bucket;

      const command = new HeadObjectCommand({
        Bucket: bucket,
        Key: providerObjectKey,
      });

      const response = await client.send(command);

      return {
        provider_object_key: providerObjectKey,
        provider_object_id: providerObjectKey,
        size: response.ContentLength || 0,
        content_type: response.ContentType || "application/octet-stream",
        etag: response.ETag || "",
        uploaded_at: response.LastModified?.toISOString() || "",
      };
    } catch (err) {
      if (err?.name === "NotFound" || err?.$metadata?.httpStatusCode === 404) {
        return null;
      }
      throw new Error(`S3 head failed: ${err?.message || String(err)}`);
    }
  }

  async listObjects({ prefix = "", cursor, limit = 100 } = {}) {
    try {
      const client = this.getClient();
      const bucket = this.providerConfig?.settings?.bucket;

      const command = new ListObjectsV2Command({
        Bucket: bucket,
        Prefix: prefix,
        ContinuationToken: cursor,
        MaxKeys: limit,
      });

      const response = await client.send(command);

      return {
        objects: (response.Contents || []).map((obj) => ({
          provider_object_key: obj.Key,
          provider_object_id: obj.Key,
          size: obj.Size || 0,
          content_type: obj.ContentType || "application/octet-stream",
          etag: obj.ETag || "",
          uploaded_at: obj.LastModified?.toISOString() || "",
        })),
        has_more: !!response.IsTruncated,
        next_cursor: response.NextContinuationToken,
      };
    } catch (err) {
      throw new Error(`S3 list failed: ${err?.message || String(err)}`);
    }
  }

  async createUploadTarget({ workspace, file, expires_at }) {
    try {
      const client = this.getClient();
      const bucket = this.providerConfig?.settings?.bucket;
      const expiresSeconds = Math.max(300, Math.floor((new Date(expires_at) - Date.now()) / 1000));

      const command = new PutObjectCommand({
        Bucket: bucket,
        Key: file.provider_object_key,
        ContentType: file.content_type,
      });

      const uploadUrl = await getSignedUrl(client, command, {
        expiresIn: expiresSeconds,
      });

      return {
        mode: "direct",
        upload_url: uploadUrl,
        provider_object_key: file.provider_object_key,
        provider_object_id: file.provider_object_id,
        headers: {},
        expires_at,
      };
    } catch (err) {
      throw new Error(`Failed to create S3 signed upload URL: ${err?.message || String(err)}`);
    }
  }

  async createDownloadTarget({ workspace, file, expires_at }) {
    try {
      const client = this.getClient();
      const bucket = this.providerConfig?.settings?.bucket;
      const expiresSeconds = Math.max(300, Math.floor((new Date(expires_at) - Date.now()) / 1000));

      const command = new GetObjectCommand({
        Bucket: bucket,
        Key: file.provider_object_key,
      });

      const downloadUrl = await getSignedUrl(client, command, {
        expiresIn: expiresSeconds,
      });

      return {
        mode: "direct",
        download_url: downloadUrl,
        provider_object_key: file.provider_object_key,
        provider_object_id: file.provider_object_id,
        headers: {},
        expires_at,
      };
    } catch (err) {
      throw new Error(`Failed to create S3 signed download URL: ${err?.message || String(err)}`);
    }
  }
}