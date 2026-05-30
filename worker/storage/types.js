// Storage types and contracts for the provider abstraction layer.
// These types document the expected shapes for the BlobStorageProvider interface.

/**
 * @typedef {"ready" | "experimental" | "not_ready" | "deprecated"} ProviderStatus
 */

/**
 * @typedef {"pending" | "configured" | "ready" | "misconfigured" | "validated-config"} ValidationState
 */

/**
 * @typedef {import("./errors.js").StorageError} StorageError
 */

/**
 * @typedef {Object} ProviderCapabilities
 * @property {boolean} upload
 * @property {boolean} download
 * @property {boolean} delete
 * @property {boolean} list
 * @property {boolean} signedUploadUrl
 * @property {boolean} signedDownloadUrl
 * @property {boolean} multipart
 * @property {boolean} checksum
 * @property {boolean} serverSideCopy
 */

/**
 * @typedef {Object} ValidationResult
 * @property {ValidationState} state
 * @property {boolean} available
 * @property {string[]} errors
 * @property {string[]} warnings
 */

/**
 * @typedef {Object} UploadContext
 * @property {Object} workspace
 * @property {Object} file
 * @property {string} expires_at
 */

/**
 * @typedef {Object} DownloadContext
 * @property {Object} workspace
 * @property {Object} file
 * @property {string} expires_at
 */

/**
 * @typedef {Object} DeleteObjectContext
 * @property {string} providerObjectKey
 * @property {string} providerObjectId
 */

/**
 * @typedef {Object} HeadObjectContext
 * @property {string} providerObjectKey
 * @property {string} providerObjectId
 */

/**
 * @typedef {Object} ListObjectsContext
 * @property {string} [prefix]
 * @property {string} [cursor]
 * @property {number} [limit]
 */

/**
 * @typedef {Object} ObjectStat
 * @property {string} provider_object_key
 * @property {string} provider_object_id
 * @property {number} size
 * @property {string} content_type
 * @property {string} etag
 * @property {string} uploaded_at
 */

/**
 * @typedef {Object} ObjectListing
 * @property {ObjectStat[]} objects
 * @property {string} [next_cursor]
 * @property {boolean} has_more
 */

/**
 * @typedef {Object} UploadTarget
 * @property {"worker_proxy" | "direct"} mode
 * @property {string} [upload_url]
 * @property {string} provider_object_key
 * @property {string} provider_object_id
 * @property {Record<string, string>} [headers]
 * @property {string} expires_at
 */

/**
 * @typedef {Object} DownloadTarget
 * @property {"worker_proxy" | "direct"} mode
 * @property {string} [download_url]
 * @property {string} provider_object_key
 * @property {string} provider_object_id
 * @property {Record<string, string>} [headers]
 * @property {string} expires_at
 */

/**
 * @typedef {Object} CopyObjectContext
 * @property {string} source_key
 * @property {string} source_id
 * @property {string} dest_key
 * @property {string} dest_id
 * @property {Record<string, string>} [metadata]
 */

/**
 * @typedef {Object} CompleteUploadContext
 * @property {Object} workspace
 * @property {Object} file
 * @property {string} provider_object_key
 * @property {string} provider_object_id
 */

// Standard capability sets
export const CAPABILITIES_SYSTEM = {
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

// S3-compatible capabilities
// NOTE: signedUploadUrl/signedDownloadUrl are generated internally by the provider
// but CLI does NOT use direct-to-S3 presigned URL mode — all transfers go through worker proxy.
// multipart upload is NOT implemented.
// serverSideCopy is NOT implemented.
export const CAPABILITIES_S3_COMPATIBLE = {
  upload: true,
  download: true,
  delete: true,
  list: true,
  signedUploadUrl: "internal", // CLI uses worker-proxy; presigned URLs exist internally
  signedDownloadUrl: "internal", // CLI uses worker-proxy; presigned URLs exist internally
  multipart: false, // Not implemented
  checksum: true, // Verified via SHA256 in MinIO e2e
  serverSideCopy: false, // Not implemented
};

// Validation state helpers
export function buildValidationResult(overrides = {}) {
  return {
    state: "pending",
    available: false,
    errors: [],
    warnings: [],
    ...overrides,
  };
}

export function buildProviderCapabilities(capabilities = {}) {
  return {
    upload: false,
    download: false,
    delete: false,
    list: false,
    signedUploadUrl: false,
    signedDownloadUrl: false,
    multipart: false,
    checksum: false,
    serverSideCopy: false,
    ...capabilities,
  };
}