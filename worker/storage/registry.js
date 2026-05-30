// Storage provider registry.
// Maps provider kinds to their classes and definitions.
// Provides catalog operations and status computation.

import { getProviderDefinition, providerCatalog } from "../services/provider_config.js";
import { SystemStorageProvider } from "./providers/system_r2.js";
import { LocalDevStorageProvider } from "./providers/local_dev.js";
import { S3CompatibleStorageProvider } from "./providers/s3_compatible.js";

// All registered provider classes
const PROVIDER_CLASSES = {
  "system": SystemStorageProvider,
  "local-dev": LocalDevStorageProvider,
  "s3-compatible": S3CompatibleStorageProvider,
};

// Provider runtime status
const PROVIDER_STATUS = {
  "system": "ready",
  "local-dev": "experimental",
  "s3-compatible": "experimental",
};

/**
 * Get the status string for a provider kind.
 * @param {string} kind
 * @returns {string}
 */
export function getProviderStatus(kind) {
  return PROVIDER_STATUS[kind] || "not_ready";
}

/**
 * Check if a provider is production-ready (status === "ready").
 * @param {string} kind
 * @returns {boolean}
 */
export function isProviderReady(kind) {
  return getProviderStatus(kind) === "ready";
}

/**
 * Check if a provider is experimental (status === "experimental").
 * @param {string} kind
 * @returns {boolean}
 */
export function isProviderExperimental(kind) {
  return getProviderStatus(kind) === "experimental";
}

/**
 * Check if a provider can be selected by users in a given environment.
 * A provider is selectable if:
 *   - Its definition has selectable: true, OR
 *   - It is experimental AND CHERI_EXPERIMENTAL_PROVIDERS=1 in env
 *
 * @param {string} kind
 * @param {Object} env
 * @returns {boolean}
 */
export function isProviderSelectable(kind, env) {
  const definition = getProviderDefinition(kind);
  if (definition.selectable) {
    return true;
  }
  return !!(definition.experimental && experimentalProvidersEnabled(env));
}

/**
 * Check if experimental providers are enabled via environment.
 * @param {Object} env
 * @returns {boolean}
 */
function experimentalProvidersEnabled(env) {
  return String(env?.CHERI_EXPERIMENTAL_PROVIDERS || "").trim() === "1";
}

/**
 * Get the provider class for a given kind.
 * Throws if the kind is not registered.
 * @param {string} kind
 * @returns {typeof SystemStorageProvider}
 */
export function getProviderClass(kind) {
  const ProviderClass = PROVIDER_CLASSES[kind];
  if (!ProviderClass) {
    throw new Error(`Unsupported storage provider: ${kind}`);
  }
  return ProviderClass;
}

/**
 * Get provider capabilities as a structured object.
 * @param {string} kind
 * @returns {Object}
 */
export function getProviderCapabilities(kind) {
  const definition = getProviderDefinition(kind);
  return {
    upload: !!definition.fields.find((f) => f.key === "upload") || kind === "system",
    download: true,
    delete: true,
    list: kind === "system",
    signedUploadUrl: kind === "s3-compatible" ? "internal" : false,
    signedDownloadUrl: kind === "s3-compatible" ? "internal" : false,
    multipart: false, // Not implemented for any provider
    checksum: kind === "s3-compatible", // Verified via SHA256 in MinIO e2e
    serverSideCopy: false, // Not implemented
  };
}

/**
 * Get catalog entries for all registered providers.
 * Filters experimental providers unless includeExperimental is true.
 *
 * @param {Object} env
 * @param {{ includeExperimental?: boolean }} options
 * @returns {Object[]}
 */
export function getProviderCatalog(env, options = {}) {
  const includeExperimental = !!options.includeExperimental;
  return providerCatalog(env, { includeExperimental });
}

/**
 * Get a single provider's catalog entry by kind.
 * Returns null if the provider does not exist.
 *
 * @param {Object} env
 * @param {string} kind
 * @param {{ includeExperimental?: boolean }} options
 * @returns {Object|null}
 */
export function getProviderCatalogEntry(env, kind, options = {}) {
  const catalog = getProviderCatalog(env, options);
  return catalog.find((p) => p.kind === kind) || null;
}

/**
 * Validate that a provider kind exists in the registry.
 * Throws if not found.
 * @param {string} kind
 */
export function assertProviderKind(kind) {
  if (!PROVIDER_CLASSES[kind]) {
    throw new Error(`Unsupported storage provider: ${kind}`);
  }
}

/**
 * Get all registered provider kinds.
 * @returns {string[]}
 */
export function getRegisteredProviderKinds() {
  return Object.keys(PROVIDER_CLASSES);
}

/**
 * Build a catalog entry with status and capabilities for API responses.
 * Does not include secrets.
 *
 * @param {string} kind
 * @param {Object} env
 * @returns {Object}
 */
export function buildProviderCatalogEntry(kind, env) {
  const definition = getProviderDefinition(kind);
  const status = getProviderStatus(kind);
  return {
    kind,
    label: definition.label,
    status,
    description: definition.description,
    recommended: !!definition.recommended,
    temporary: !!definition.temporary,
    selectable: isProviderSelectable(kind, env),
    coming_soon: !!definition.comingSoon,
    experimental: status === "experimental",
    reset_policy: definition.resetPolicy || "",
    integration_status: definition.integrationStatus || "unknown",
    capabilities: getProviderCapabilities(kind),
    credential_fields: definition.fields.map((f) => ({
      key: f.key,
      label: f.label,
      required: !!f.required,
      secret: !!f.secret,
    })),
  };
}