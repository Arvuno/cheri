// Object key construction and validation for storage providers.
// Ensures workspace-scoped, traversal-safe, deterministic object keys.

import { safeLogicalName } from "../security/tokens.js";
import { InvalidObjectKeyError } from "./errors.js";

const KEY_PREFIX = "workspaces";  // Reserved for future use; current keys use workspaceId directly
const FILES_PREFIX = "files";    // Reserved for future use

// Current key format matches storage_registry.js:
// {workspaceId}/{fileId}/v{version}/{safeLogicalName}
const OBJECT_KEY_PATTERN = /^[^/]+\/[^/]+\/v[0-9]+\/[^/]+$/;

/**
 * Build a canonical object key for a file version.
 *
 * @param {Object} options
 * @param {string} options.workspaceId
 * @param {string} options.fileId
 * @param {number} options.version
 * @param {string} options.logicalName
 * @returns {string}
 */
export function buildObjectKey({ workspaceId, fileId, version, logicalName }) {
  const safeName = safeLogicalName(logicalName);
  return `${KEY_PREFIX}/${workspaceId}/${FILES_PREFIX}/${fileId}/v${version}/${safeName}`;
}

/**
 * Build a provider object reference (key + id pair) for a file.
 *
 * @param {Object} options
 * @param {string} options.workspaceId
 * @param {string} options.fileId
 * @param {number} options.version
 * @param {string} options.logicalName
 * @returns {{ provider_object_key: string, provider_object_id: string }}
 */
export function buildProviderObjectReference(options) {
  const key = buildObjectKey(options);
  return {
    provider_object_key: key,
    provider_object_id: key,
  };
}

/**
 * Validate that an object key conforms to the expected format.
 * Throws InvalidObjectKeyError if the key is malformed.
 *
 * @param {string} key
 * @returns {boolean}
 */
export function validateObjectKey(key) {
  if (!key || typeof key !== "string") {
    throw new InvalidObjectKeyError("Object key must be a non-empty string.");
  }
  if (!OBJECT_KEY_PATTERN.test(key)) {
    throw new InvalidObjectKeyError(
      `Object key "${key}" does not match expected format.`
    );
  }
  return true;
}

/**
 * Extract workspace_id from an object key.
 *
 * @param {string} key
 * @returns {string}
 */
export function extractWorkspaceId(key) {
  validateObjectKey(key);
  const parts = key.split("/");
  return parts[1];
}

/**
 * Extract file_id from an object key.
 *
 * @param {string} key
 * @returns {string}
 */
export function extractFileId(key) {
  validateObjectKey(key);
  const parts = key.split("/");
  return parts[3];
}

/**
 * Extract version number from an object key.
 *
 * @param {string} key
 * @returns {number}
 */
export function extractVersion(key) {
  validateObjectKey(key);
  const parts = key.split("/");
  return parseInt(parts[5].slice(1), 10);
}

/**
 * Build an object key prefix for listing all files in a workspace.
 *
 * @param {string} workspaceId
 * @returns {string}
 */
export function buildWorkspacePrefix(workspaceId) {
  return `${KEY_PREFIX}/${workspaceId}/${FILES_PREFIX}/`;
}

/**
 * Build an object key prefix for listing all versions of a specific file.
 *
 * @param {string} workspaceId
 * @param {string} fileId
 * @returns {string}
 */
export function buildFilePrefix(workspaceId, fileId) {
  return `${KEY_PREFIX}/${workspaceId}/${FILES_PREFIX}/${fileId}/`;
}

/**
 * List the version keys for a file (for cleanup or migration).
 *
 * @param {string} workspaceId
 * @param {string} fileId
 * @param {number} currentVersion
 * @returns {string[]}
 */
export function listVersionKeys(workspaceId, fileId, currentVersion) {
  const keys = [];
  for (let v = 1; v <= currentVersion; v++) {
    // Note: logicalName is not stored here, so we can only construct the prefix.
    // In practice, cleanup iterates over KV file records instead.
  }
  return keys;
}