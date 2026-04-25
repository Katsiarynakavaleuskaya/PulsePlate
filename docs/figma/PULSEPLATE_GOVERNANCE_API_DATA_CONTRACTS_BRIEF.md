# PulsePlate Governance Brief: 06_API_Data_Contracts

**Date:** 2026-04-25
**Figma file:** `2JDwOByQIbcPgp93FDzHii`
**Target page:** `06_API_Data_Contracts`
**Target frame:** `850:48`
**Mode:** Figma visual-support sync from repo runtime truth

## Purpose

Correct the `06_API_Data_Contracts` governance board so the design layer
mirrors current repo runtime contracts and does not preserve false API,
session, or binary-fetch claims.

Figma remains visual support only. Repo code, tests, backend OpenAPI contracts,
and governed API-client implementation remain the source of truth. Generated
frontend artifacts are contract evidence and consumer mirrors, not a separate
runtime authority.

## Runtime And Contract Evidence

- `frontend/src/api/client.ts`
- `frontend/src/api/schema.ts` (generated consumer mirror)
- `frontend/src/api/openapi.json` (generated contract artifact)
- `frontend/src/api/__tests__/client.fetchBlob.test.ts`
- `frontend/src/api/__tests__/client.normalizeUrl.test.ts`
- `frontend/src/api/__tests__/thin-client-guards.test.ts`
- `frontend/AGENTS.md`
- `docs/policy/openapi_stability.md`

## Allowed Claims

- `api()` is the JSON/API client surface.
- `fetchBlob()` is the binary/blob fetch surface.
- `VITE_API_BASE` provides the API base.
- `normalizeApiUrl()` joins API base and API path without duplicate API
  segments.
- Web consumes generated `schema.ts` / `openapi.json` artifacts.
- API-path requests default to `credentials=include` unless callers override
  credentials.
- `fetchBlob()` external absolute URLs strip auth headers and force
  `credentials=omit`.
- Internal/API-path `401/403` can route to `/enter-key` through the default
  fallback; callers with `onAuthError` own auth-error handling.

## Forbidden Claims

- Exclude `/login` from this board.
- Avoid referencing `fetchBinary`.
- Do not claim Zod runtime validation.
- Omit `/api/proxy`.
- Leave out `SessionExpiredModal`.
- Do not imply external URL `401/403` clears local key state or redirects.
- Keep text, fake labels, endpoint strings, and code snippets out of the
  icon image.

## Figma Text Updates

| Node | Replacement text |
| --- | --- |
| `850:57` | Backend OpenAPI remains the contract source; web consumes generated schema.ts/openapi.json. Keep endpoint copy tied to repo artifacts and regenerate through the governed OpenAPI workflow when routes or schemas change. |
| `850:60` | api() uses VITE_API_BASE + normalizeApiUrl(). API requests default to credentials=include. On 401/403, the default fallback clears local key state and routes to /enter-key; callers with onAuthError receive a clearApiKey helper and own the auth-error handling. |
| `850:63` | fetchBlob() supports API paths and absolute external URLs. API paths use normalizeApiUrl() and default to credentials=include; external URLs strip auth headers and force credentials=omit. |
| `850:66` | Figma may describe only the runtime contracts proven in repo: api(), fetchBlob(), VITE_API_BASE, normalizeApiUrl(), generated schema.ts/openapi.json mirrors, API-path credentials=include default unless overridden, fetchBlob external credentials=omit, and default internal API-path 401/403 fallback to /enter-key. |
| `850:67` | Design note: Visual support only. Repo remains runtime source of truth. |

## Icon Contract

Create `PP_Gov_Icon_APIContracts_v1` as a text-free vector governance icon for
API contracts. The icon may show an abstract API gateway node, schema blocks,
safe blob/download shape, internal API success path, and blocked external-auth
leakage line.

The icon must not contain text, fake labels, letters, endpoint strings, UI
screenshots, `/login`, `fetchBinary`, Zod symbols, `/api/proxy`, or
`SessionExpiredModal`.

## Validation

- Figma board `850:48` verified.
- Icon `PP_Gov_Icon_APIContracts_v1` exists.
- Visual support note exists.
- Forbidden claims absent from the Figma surface.
- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` OK.
- `git diff --check` PASS.
- `pre-commit run --all-files` PASS after hook-managed EOF cleanup.
- `make validate-changed` PASS with the root repo venv explicitly supplied via
  `VENV_PYTHON`.
- Targeted frontend Vitest command is not available directly in this isolated
  worktree because `frontend/node_modules/.bin/vitest` is absent.
- Runtime code unchanged.
