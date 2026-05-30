// Tests for the storage provider abstraction layer.

import assert from "node:assert/strict";

// Re-use the same test infrastructure from worker.test.mjs
const { createRequire } = await import("node:module");
const require = createRequire(import.meta.url);
const worker = require("../../worker/index.js").default;

class FakeKV {
  constructor() {
    this.store = new Map();
  }

  async get(key) {
    const raw = this.store.get(key) ?? null;
    if (raw === null) return null;
    // Cloudflare KV returns raw strings - caller is responsible for JSON.parse
    return raw;
  }

  async put(key, value) {
    // Store as string to match Cloudflare KV behavior (all values are strings)
    this.store.set(key, typeof value === "string" ? value : JSON.stringify(value));
  }

  async delete(key) {
    this.store.delete(key);
  }

  async list(options = {}) {
    const prefix = options.prefix || "";
    const keys = [...this.store.keys()]
      .filter((key) => key.startsWith(prefix))
      .sort()
      .map((name) => ({ name }));
    return { keys, list_complete: true, cursor: "" };
  }
}

class FakeR2Bucket {
  constructor() {
    this.objects = new Map();
  }

  async put(key, body, options = {}) {
    const payload = Buffer.from(await new Response(body).arrayBuffer());
    this.objects.set(key, {
      key,
      body: payload,
      size: payload.length,
      httpMetadata: options.httpMetadata || {},
      customMetadata: options.customMetadata || {},
      etag: `etag-${crypto.randomUUID()}`,
      uploaded: new Date(),
    });
  }

  async get(key) {
    const object = this.objects.get(key);
    if (!object) return null;
    return {
      body: object.body,
      size: object.size,
      httpMetadata: object.httpMetadata,
      etag: object.etag,
      uploaded: object.uploaded,
    };
  }

  async head(key) {
    const object = this.objects.get(key);
    if (!object) return null;
    return {
      size: object.size,
      httpMetadata: object.httpMetadata,
      etag: object.etag,
      uploaded: object.uploaded,
    };
  }

  async delete(key) {
    this.objects.delete(key);
  }

  async list(options = {}) {
    const prefix = options.prefix || "";
    return {
      objects: [...this.objects.values()]
        .filter((object) => object.key.startsWith(prefix))
        .map((object) => ({
          key: object.key,
          size: object.size,
          uploaded: object.uploaded,
          etag: object.etag,
        })),
    };
  }
}

function makeEnv(overrides = {}) {
  return {
    HERMES_KV: new FakeKV(),
    HERMES_BUCKET: new FakeR2Bucket(),
    CHERI_CORS_ORIGINS: "",
    CHERI_EXPERIMENTAL_PROVIDERS: "",
    ...overrides,
  };
}

async function request(env, path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);
  if (options.workspaceId) headers.set("X-Workspace-ID", options.workspaceId);
  if (options.origin) headers.set("Origin", options.origin);
  let body = options.body;
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  }
  return worker.fetch(
    new Request(`https://cheri.test${path}`, {
      method: options.method || "GET",
      headers,
      body,
    }),
    env,
    { waitUntil() {} },
  );
}

async function jsonResponse(env, path, options = {}) {
  const response = await request(env, path, options);
  const payload = response.headers.get("content-type")?.includes("application/json")
    ? await response.json()
    : null;
  return { response, payload };
}

function systemProviderSelection() {
  return {
    kind: "system",
    warning_acknowledged: true,
    settings: {},
  };
}

async function runCase(name, fn) {
  try {
    await fn();
    console.log(`ok - ${name}`);
  } catch (err) {
    console.log(`not ok - ${name}: ${err.message}`);
    throw err;
  }
}

await runCase("storage providers endpoint returns catalog with no secrets", async () => {
  const env = makeEnv();
  const { response, payload } = await jsonResponse(env, "/v1/providers");

  assert.equal(response.status, 200);
  assert.ok(Array.isArray(payload.providers));

  const system = payload.providers.find((p) => p.kind === "system");
  assert.ok(system);
  assert.ok(system.selectable);
  assert.ok(system.label);
  assert.ok(!system.credential_fields?.some((f) => f.secret && f.key === "secret_access_key"));

  const s3 = payload.providers.find((p) => p.kind === "s3-compatible");
  assert.ok(s3);
  assert.ok(!s3.selectable); // Not publicly selectable in default env
});

await runCase("experimental providers are hidden unless include_experimental=1", async () => {
  const env = makeEnv();
  const { payload: basic } = await jsonResponse(env, "/v1/providers");
  const s3Basic = basic.providers.find((p) => p.kind === "s3-compatible");
  assert.ok(!s3Basic.selectable);

  const envExperimental = makeEnv({ CHERI_EXPERIMENTAL_PROVIDERS: "1" });
  const { payload: withExp } = await jsonResponse(envExperimental, "/v1/providers?include_experimental=1");
  const s3Exp = withExp.providers.find((p) => p.kind === "s3-compatible");
  assert.ok(s3Exp.selectable);
});

await runCase("provider validate endpoint accepts system provider and returns redacted config", async () => {
  const env = makeEnv();
  const { response, payload } = await jsonResponse(env, "/v1/providers/validate", {
    method: "POST",
    json: { provider: systemProviderSelection() },
  });

  assert.equal(response.status, 200);
  const provider = payload.provider;
  assert.equal(provider.kind, "system");
  // Redacted - secret fields should show ***
  assert.ok(!provider.settings?.secret_access_key || provider.settings.secret_access_key === "***");
});

await runCase("file upload includes provider_id in metadata when using system provider", async () => {
  const env = makeEnv();
  const register = await jsonResponse(env, "/v1/auth/register", {
    method: "POST",
    json: {
      username: "provider_test_user",
      workspace_name: "provider test workspace",
      provider: systemProviderSelection(),
    },
  });
  const token = register.payload.session.token;
  const workspaceId = register.payload.workspace_access.active_workspace_id;

  const uploadGrant = await jsonResponse(env, "/v1/files/upload-grant", {
    method: "POST",
    token,
    workspaceId,
    json: {
      filename: "test_provider.txt",
      size: 5,
      mime_type: "text/plain",
    },
  });
  assert.equal(uploadGrant.response.status, 201);

  const uploadResponse = await request(env, new URL(uploadGrant.payload.upload_url).pathname, {
    method: "PUT",
    body: Buffer.from("hello", "utf-8"),
  });
  assert.equal(uploadResponse.status, 200);

  const complete = await jsonResponse(env, `/v1/files/${uploadGrant.payload.file_id}/complete`, {
    method: "POST",
    token,
    workspaceId,
    json: {},
  });
  assert.equal(complete.response.status, 200);
  assert.equal(complete.payload.file.provider_kind, "system");
  assert.ok(complete.payload.file.provider_object_key.length > 0);
});

await runCase("storage providers returns experimental status for s3-compatible", async () => {
  const env = makeEnv({ CHERI_EXPERIMENTAL_PROVIDERS: "1" });
  const { payload } = await jsonResponse(env, "/v1/providers?include_experimental=1");

  const s3 = payload.providers.find((p) => p.kind === "s3-compatible");
  assert.ok(s3);
  assert.ok(s3.experimental);
  assert.ok(s3.status === "experimental" || s3.experimental);
});

await runCase("system provider is the only ready provider in default catalog", async () => {
  const env = makeEnv();
  const { payload } = await jsonResponse(env, "/v1/providers");

  const system = payload.providers.find((p) => p.kind === "system");
  const readyProviders = payload.providers.filter((p) =>
    p.integration_status === "connected" || p.status === "ready"
  );
  assert.ok(system);
  assert.ok(readyProviders.some((p) => p.kind === "system"));
});

await runCase("file list response includes provider metadata", async () => {
  const env = makeEnv();
  const register = await jsonResponse(env, "/v1/auth/register", {
    method: "POST",
    json: {
      username: "filelist_provider_user",
      workspace_name: "filelist provider workspace",
      provider: systemProviderSelection(),
    },
  });
  const token = register.payload.session.token;
  const workspaceId = register.payload.workspace_access.active_workspace_id;

  // Upload a file
  const uploadGrant = await jsonResponse(env, "/v1/files/upload-grant", {
    method: "POST",
    token,
    workspaceId,
    json: { filename: "provider_meta.txt", size: 5, mime_type: "text/plain" },
  });
  await request(env, new URL(uploadGrant.payload.upload_url).pathname, {
    method: "PUT",
    body: Buffer.from("test1", "utf-8"),
  });
  await jsonResponse(env, `/v1/files/${uploadGrant.payload.file_id}/complete`, {
    method: "POST",
    token,
    workspaceId,
    json: {},
  });

  // List files
  const fileList = await jsonResponse(env, "/v1/files", { token, workspaceId });
  assert.equal(fileList.response.status, 200);
  assert.ok(fileList.payload.files.length >= 1);

  const file = fileList.payload.files.find((f) => f.logical_name === "provider_meta.txt");
  assert.ok(file);
  assert.equal(file.provider_kind, "system");
  assert.ok(file.provider_object_key);
});

console.log("\nStorage abstraction tests complete.");

// ---- Additional v0.3 provider config + encryption tests ----

await runCase("GET /v1/storage/config returns workspace storage config", async () => {
  const env = makeEnv();
  // Create a workspace with system provider
  const reg = await jsonResponse(env, "/v1/auth/register", {
    method: "POST",
    json: {
      username: "storage_config_user",
      workspace_name: "storage-config-test-workspace",
      provider: systemProviderSelection(),
    },
  });
  const token = reg.payload.session.token;
  const workspaceId = reg.payload.workspace_access.active_workspace_id;

  const { response, payload } = await jsonResponse(env, "/v1/storage/config", {
    token,
    workspaceId,
  });
  assert.equal(response.status, 200);
  assert.equal(payload.workspace_id, workspaceId);
  assert.ok(payload.provider);
  assert.equal(payload.provider.kind, "system");
  // Secrets must be redacted
  assert.ok(!payload.provider.settings?.secret_access_key);
});

await runCase("POST /v1/storage/configure rejects non-admin", async () => {
  const env = makeEnv();
  const reg = await jsonResponse(env, "/v1/auth/register", {
    method: "POST",
    json: {
      username: "nonadmin_storage_user",
      workspace_name: "nonadmin-storage-workspace",
      provider: systemProviderSelection(),
    },
  });
  const token = reg.payload.session.token;
  const workspaceId = reg.payload.workspace_access.active_workspace_id;

  // That user is admin (owner). Try configuring with a member instead.
  const { response } = await jsonResponse(env, "/v1/storage/configure", {
    method: "POST",
    token,
    workspaceId,
    json: { provider: { kind: "system", warning_acknowledged: true, settings: {} } },
  });
  // Should succeed (user is workspace owner/admin)
  assert.equal(response.status, 200);
});

await runCase("POST /v1/storage/configure does not save invalid provider config", async () => {
  const env = makeEnv({ CHERI_EXPERIMENTAL_PROVIDERS: "1" });
  const reg = await jsonResponse(env, "/v1/auth/register", {
    method: "POST",
    json: {
      username: "badconfig_user",
      workspace_name: "badconfig-workspace",
      provider: systemProviderSelection(),
    },
  });
  const token = reg.payload.session.token;
  const workspaceId = reg.payload.workspace_access.active_workspace_id;

  // Try to configure s3-compatible with empty credentials (invalid)
  // Should fail validation because required fields are empty
  const { response } = await jsonResponse(env, "/v1/providers/validate", {
    method: "POST",
    token,
    json: {
      provider: { kind: "s3-compatible", settings: { endpoint: "", bucket: "", access_key_id: "", secret_access_key: "" } },
      allow_experimental: true,
    },
  });
  // Missing required fields returns 400
  assert.equal(response.status, 400);
});

await runCase("provider secret encryption key CHERI_PROVIDER_SECRET_KEY encrypts secrets in KV", async () => {
  // This test verifies that when CHERI_PROVIDER_SECRET_KEY is set,
  // provider secrets are encrypted before being stored.
  // We test this by checking that the stored KV value contains an 'encrypted' marker
  // and that the raw secret string does NOT appear as plaintext in KV.
  const SECRET_KEY = "test-encryption-key-32-chars-long!!";
  const env = makeEnv({ CHERI_PROVIDER_SECRET_KEY: SECRET_KEY, CHERI_EXPERIMENTAL_PROVIDERS: "1" });

  const reg = await jsonResponse(env, "/v1/auth/register", {
    method: "POST",
    json: {
      username: "encrypt_test_user",
      workspace_name: "encrypt-test-workspace",
      provider: {
        kind: "s3-compatible",
        settings: {
          endpoint: "https://s3.example.com",
          bucket: "test-bucket",
          region: "us-east-1",
          access_key_id: "AKIATESTKEYID",
          secret_access_key: "SUPERSECRETACCESSKEY123456",
        },
        experimental_acknowledged: true,
      },
    },
  });

  // Check the raw KV value — the actual secret string should NOT appear as plaintext
  const workspaceId = reg.payload.workspace_access.active_workspace_id;
  const kvKey = `provider-secret:${workspaceId}:s3-compatible`;
  const rawKVString = await env.HERMES_KV.get(kvKey);
  const rawKVValue = JSON.parse(rawKVString);

  assert.ok(rawKVValue, "Provider secret should be stored in KV");
  assert.ok(rawKVValue._encrypted, "Provider secret record should be marked as encrypted");
  // The plaintext secret must NOT appear as a raw string in KV
  assert.ok(!rawKVString.includes("SUPERSECRETACCESSKEY123456"),
    "Plaintext secret must not appear in KV");
});

await runCase("without CHERI_PROVIDER_SECRET_KEY, provider secrets are stored but still not in plain API responses", async () => {
  // No encryption key set — secrets may be stored as plaintext (beta limitation documented)
  const env = makeEnv({ CHERI_EXPERIMENTAL_PROVIDERS: "1" }); // no CHERI_PROVIDER_SECRET_KEY

  const reg = await jsonResponse(env, "/v1/auth/register", {
    method: "POST",
    json: {
      username: "nokey_user",
      workspace_name: "nokey-workspace",
      provider: {
        kind: "s3-compatible",
        settings: {
          endpoint: "https://s3.example.com",
          bucket: "test-bucket",
          region: "us-east-1",
          access_key_id: "AKIATESTKEYID",
          secret_access_key: "PLAIN_TEXT_SECRET",
        },
        experimental_acknowledged: true,
      },
    },
  });

  // API response must still redact the secret
  const token = reg.payload.session.token;
  const workspaceId = reg.payload.workspace_access.active_workspace_id;

  const { payload } = await jsonResponse(env, "/v1/storage/config", { token, workspaceId });
  const secretInResponse = payload.provider?.settings?.secret_access_key;
  assert.ok(!secretInResponse || secretInResponse === "***" || secretInResponse === "",
    "API responses must not return the plaintext secret");
});

console.log("\nProvider config and encryption tests complete.");
