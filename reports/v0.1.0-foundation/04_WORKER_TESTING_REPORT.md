# Worker Testing Report

## What Changed

Worker tests were already present and passing (`tests/node/worker.test.mjs`). This phase confirmed they work correctly and document the backend route coverage.

## Test Results

```
node tests/node/worker.test.mjs
ok - provider catalog exposes system as ready and other providers as coming soon
ok - provider catalog can expose experimental selectability when explicitly enabled
ok - register, login, logout, workspace selection, and invite join flows work end to end
ok - file upload, list, download, and activity flows work through the system provider
ok - task registry routes and security checks behave correctly
ok - worker only returns CORS headers for explicitly allowed origins
----------------------------------------------------------------------
6 test cases, all PASS
```

## Route Coverage

| Route | Test Coverage |
|-------|--------------|
| `GET /v1/providers` | Covered — system selectable, others coming_soon |
| `GET /v1/providers?include_experimental=1` | Covered — experimental providers exposed with flag |
| `POST /v1/auth/register` | Covered — full register/login/logout flow |
| `POST /v1/auth/login` | Covered — bootstrap secret login |
| `POST /v1/auth/logout` | Covered — session revocation |
| `GET /v1/session` | Covered — 401 on invalid session |
| `POST /v1/workspaces/select` | Covered — workspace create/use |
| `POST /v1/teams/invites` | Covered — invite creation |
| `POST /v1/teams/invites/accept` | Covered — invite acceptance |
| `GET /v1/teams` | Covered — team snapshot with members |
| `POST /v1/files/upload-grant` | Covered — upload grant creation |
| `PUT /upload/<id>` | Covered — actual file upload |
| `POST /v1/files/<id>/complete` | Covered — upload completion |
| `GET /v1/files` | Covered — file listing |
| `POST /v1/files/<id>/download-grant` | Covered — download grant |
| `GET /v1/activity` | Covered — activity feed |
| `POST /v1/tasks` | Covered — task creation |
| `GET /v1/tasks` | Covered — task listing |
| `DELETE /v1/tasks/<id>` | Covered — task deletion |
| `GET /healthz` | Covered — CORS header tests |

## Provider Gating Tests

**System provider**:
- `selectable: true`, `coming_soon: false` — users can select it
- Full upload/download/invite flow works

**S3-compatible**:
- `selectable: false`, `coming_soon: true` — cannot be selected in default flow

**Google Drive**:
- `selectable: false`, `coming_soon: true` (default), `experimental: true` (with flag)

**Backblaze B2**:
- `selectable: false`, `coming_soon: true` (default), `experimental: true` (with flag)

## Mock Infrastructure

- `FakeKV` — in-memory Map with get/put/delete/list methods
- `FakeR2Bucket` — in-memory object store with put/get/head/delete/list methods
- `makeEnv()` — constructs full Worker env with FakeKV + FakeR2 + CORS config
- `request()` / `jsonResponse()` — HTTP test helpers using worker.fetch directly

## Files Changed

- No structural changes to `tests/node/worker.test.mjs` (already working)
- `package.json` — test scripts remain: `npm run test:worker` and `npm test`

## Known Limitations

- Worker tests use direct import of `../../worker/index.js` which must resolve correctly
- `CHERI_EXPERIMENTAL_PROVIDERS` env var must be set to "1" to enable experimental providers in catalog
- No test for non-System provider actual file operations (S3/GDrive/B2) — not implemented yet