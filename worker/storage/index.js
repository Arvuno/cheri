// Storage abstraction layer.
// Re-exports from individual modules for convenient access.

export {
  StorageError,
  ProviderNotReadyError,
  ProviderConfigInvalidError,
  ProviderSecretMissingError,
  StorageUploadFailedError,
  StorageDownloadFailedError,
  StorageObjectNotFoundError,
  InvalidObjectKeyError,
} from "./errors.js";

export {
  CAPABILITIES_SYSTEM,
  CAPABILITIES_S3_COMPATIBLE,
  buildValidationResult,
  buildProviderCapabilities,
} from "./types.js";

export {
  buildObjectKey,
  buildProviderObjectReference,
  validateObjectKey,
  extractWorkspaceId,
  extractFileId,
  extractVersion,
  buildWorkspacePrefix,
  buildFilePrefix,
} from "./object_keys.js";

export {
  getProviderStatus,
  isProviderReady,
  isProviderExperimental,
  isProviderSelectable,
  getProviderClass,
  getProviderCapabilities,
  getProviderCatalog,
  getProviderCatalogEntry,
  assertProviderKind,
  getRegisteredProviderKinds,
  buildProviderCatalogEntry,
} from "./registry.js";

export { BaseStorageProvider } from "./providers/base.js";
export { SystemStorageProvider } from "./providers/system_r2.js";
export { LocalDevStorageProvider } from "./providers/local_dev.js";
export { S3CompatibleStorageProvider } from "./providers/s3_compatible.js";