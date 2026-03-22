# SPA at apex — routing contract (Caddy + FastAPI)

**Status:** Contract for production/staging Caddy in [`deploy/Caddyfile.production`](../../deploy/Caddyfile.production) (legacy matchers at `deploy/Caddyfile.production:12`).
**Scope:** Edge routing only — no thin-client or OpenAPI changes.

## Goals

- Browser **GET** `/` and client-side routes are served from **`frontend/dist`** (SPA fallback to `index.html`).
- All API and operational traffic reaches **FastAPI** (`app:8000`) unchanged.

## Method split (SPA vs legacy POST)

These paths overlap between **legacy HTTP clients** and the SPA:

- **`/bmi`**: **GET** is a React route ([`frontend/src/config/routes.ts:30`](../../frontend/src/config/routes.ts)); **POST** (and **OPTIONS** preflight) go to FastAPI.
- **`/plan`**, **`/insight`**, **`/premium_bmr`**, **`/premium_targets`**: no SPA routes today — **GET**, **POST**, and **OPTIONS** go to FastAPI so browsers do not receive an empty SPA shell for direct GETs.

| Path | GET | POST | OPTIONS |
|------|-----|------|---------|
| `/bmi` | SPA | `reverse_proxy` → app | `reverse_proxy` → app |
| `/plan` | `reverse_proxy` → app | `reverse_proxy` → app | `reverse_proxy` → app |
| `/insight` | `reverse_proxy` → app | `reverse_proxy` → app | `reverse_proxy` → app |
| `/premium_bmr` | `reverse_proxy` → app | `reverse_proxy` → app | `reverse_proxy` → app |
| `/premium_targets` | `reverse_proxy` → app | `reverse_proxy` → app | `reverse_proxy` → app |

Caddy evaluates **POST**, then **OPTIONS**, then **GET** (legacy-only paths), then the general API matcher, then SPA `file_server`.

## Paths proxied to FastAPI (all methods unless noted)

| Pattern | Notes |
|---------|--------|
| `/api*` | REST API |
| `/health*`, `/ready` | Probes |
| `/metrics` | Prometheus |
| `/ws*` | WebSocket foundation |
| `/docs*`, `/redoc*`, `/openapi.json` | OpenAPI / docs |
| `/admin*` | Admin |
| `/privacy`, `/terms` | Legacy HTML (no client route today) |
| `/debug_env` | Debug (gate in prod env) |

## Static (Caddy `file_server`)

- Built assets under `/srv/frontend` (from [`frontend/Dockerfile.caddy-spa`](../../frontend/Dockerfile.caddy-spa)).
- **`/favicon.ico`**: prefer `dist` (not proxied to app).

## CSP

- API responses may set CSP via app middleware.
- Static HTML from Caddy does not automatically get the same headers; avoid duplicating conflicting CSP on static responses unless product/security requires it (follow-up if needed).

## Build-time API base

- Docker build ARG `VITE_API_BASE` (default same-origin `/api/v1`). Override with an absolute URL for split-origin or Workers-backed API builds ([`frontend/Dockerfile.caddy-spa:17`](../../frontend/Dockerfile.caddy-spa)).

## QA smoke checklist (after deploy)

- **MIME:** `GET /` returns `text/html`; `GET /health` returns JSON (via proxy).
- **Deep link:** `GET /bmi` serves SPA `index.html` (not API); `GET /plan` (no SPA route) is proxied to the app.
- **Legacy POST:** `POST /bmi` (and peers) reaches FastAPI (not static 405 from `file_server`).
- **OpenAPI:** `GET /openapi.json` proxied (200, JSON).
- **Ops:** `GET /metrics` proxied when enabled; `GET /ready` behavior unchanged.
- **WebSocket:** upgrade to `/ws` reaches app when feature flag allows.

## References

- [`deploy/docker-compose.production.yaml`](../../deploy/docker-compose.production.yaml)
- [`deploy/AGENTS.md`](../../deploy/AGENTS.md)
