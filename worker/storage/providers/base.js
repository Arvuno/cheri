// Base class for blob storage providers.
// Provides default implementations that indicate the operation is not available.
// Providers extend this class and override only what they support.

import { ProviderNotReadyError } from "../errors.js";
import { buildValidationResult, buildProviderCapabilities } from "../types.js";

export class BaseStorageProvider {
  constructor(env, providerConfig, definition) {
    this.env = env;
    this.providerConfig = providerConfig;
    this.definition = definition;
    this._capabilities = buildProviderCapabilities();
  }

  get id() {
    return this.definition?.kind || this.providerConfig?.kind || "unknown";
  }

  get label() {
    return this.definition?.label || this.providerConfig?.label || "Unknown Provider";
  }

  get capabilities() {
    return this._capabilities;
  }

  /**
   * Validate that the provider is correctly configured.
   * Subclasses should override this to check their specific requirements.
   * @returns {Promise<import("../types.js").ValidationResult>}
   */
  async validateConfig() {
    return buildValidationResult({
      state: "configured",
      available: false,
      errors: [],
      warnings: [
        `${this.label} is scaffolded but not enabled in this deployment.`,
      ],
    });
  }

  /**
   * Throw an error indicating the operation is unavailable.
   * @param {string} action
   * @throws {ProviderNotReadyError}
   */
  unavailable(action) {
    throw new ProviderNotReadyError(`${this.label} cannot ${action} in this deployment.`);
  }

  /**
   * Store a blob.
   * @param {Object} context
   * @throws {ProviderNotReadyError}
   */
  async putObject({ providerObjectKey, body, contentType, metadata = {} }) {
    this.unavailable("store files");
  }

  /**
   * Retrieve a blob.
   * @param {Object} context
   * @throws {ProviderNotReadyError}
   */
  async getObject({ providerObjectKey }) {
    this.unavailable("read files");
  }

  /**
   * Delete a blob.
   * @param {Object} context
   * @throws {ProviderNotReadyError}
   */
  async deleteObject({ providerObjectKey }) {
    this.unavailable("delete files");
  }

  /**
   * List blobs with an optional prefix filter.
   * @param {Object} context
   * @throws {ProviderNotReadyError}
   */
  async listObjects({ prefix = "" } = {}) {
    this.unavailable("list objects");
  }

  /**
   * Get metadata for a single blob without returning the body.
   * @param {Object} context
   * @throws {ProviderNotReadyError}
   */
  async headObject({ providerObjectKey }) {
    this.unavailable("inspect objects");
  }

  /**
   * Create an upload target for a file.
   * Default implementation returns a worker_proxy target.
   * @param {Object} context
   * @returns {Promise<Object>}
   */
  async createUploadTarget({ workspace, file, expires_at }) {
    return {
      mode: "worker_proxy",
      provider_object_key: file.provider_object_key,
      provider_object_id: file.provider_object_id,
      headers: {},
      expires_at,
    };
  }

  /**
   * Create a download target for a file.
   * Default implementation returns a worker_proxy target.
   * @param {Object} context
   * @returns {Promise<Object>}
   */
  async createDownloadTarget({ workspace, file, expires_at }) {
    return {
      mode: "worker_proxy",
      provider_object_key: file.provider_object_key,
      provider_object_id: file.provider_object_id,
      headers: {},
      expires_at,
    };
  }

  /**
   * Complete an upload after the blob has been stored.
   * Can be overridden to perform post-upload verification.
   * @param {Object} context
   * @returns {Promise<void>}
   */
  async completeUpload({ workspace, file, providerObjectKey, providerObjectId }) {
    // Default: stat the object and return the stat
    const stat = await this.headObject({ providerObjectKey, providerObjectId });
    return stat;
  }
}