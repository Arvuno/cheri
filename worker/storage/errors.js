// Storage provider errors

export class StorageError extends Error {
  constructor(code, message, httpStatus = 500) {
    super(message);
    this.name = "StorageError";
    this.code = code;
    this.httpStatus = httpStatus;
  }
}

export class ProviderNotReadyError extends StorageError {
  constructor(message = "Provider is not available in this deployment.") {
    super("PROVIDER_NOT_READY", message, 503);
    this.name = "ProviderNotReadyError";
  }
}

export class ProviderConfigInvalidError extends StorageError {
  constructor(message = "Provider configuration is invalid.") {
    super("PROVIDER_CONFIG_INVALID", message, 400);
    this.name = "ProviderConfigInvalidError";
  }
}

export class ProviderSecretMissingError extends StorageError {
  constructor(message = "Required provider secret is missing.") {
    super("PROVIDER_SECRET_MISSING", message, 500);
    this.name = "ProviderSecretMissingError";
  }
}

export class StorageUploadFailedError extends StorageError {
  constructor(message = "Upload failed.") {
    super("STORAGE_UPLOAD_FAILED", message, 500);
    this.name = "StorageUploadFailedError";
  }
}

export class StorageDownloadFailedError extends StorageError {
  constructor(message = "Download failed.") {
    super("STORAGE_DOWNLOAD_FAILED", message, 500);
    this.name = "StorageDownloadFailedError";
  }
}

export class StorageObjectNotFoundError extends StorageError {
  constructor(message = "Object not found in storage.") {
    super("STORAGE_OBJECT_NOT_FOUND", message, 404);
    this.name = "StorageObjectNotFoundError";
  }
}

export class InvalidObjectKeyError extends StorageError {
  constructor(message = "Object key format is invalid.") {
    super("INVALID_OBJECT_KEY", message, 400);
    this.name = "InvalidObjectKeyError";
  }
}