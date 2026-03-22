# SPA at apex — routing contract (Caddy + FastAPI)

**Status:** Contract for production/staging Caddy in [`deploy/Caddyfile.production`](../../deploy/Caddyfile.production).
**Scope:** Edge routing only — no thin-client or OpenAPI changes.

## Goals

- Browser **GET** `/` and client-side routes are served from **`frontend/dist`** (SPA fallback to `index.html`).
- All API and operational traffic reaches **FastAPI** (`app:8000`) unchanged.

## Method split (SPA vs legacy POST)

These paths are **React Router** pages for **GET** (see [`frontend/src/config/routes.ts`](../../frontend/src/config/routes.ts)) but **FastAPI** defines **POST** on the same path for legacy clients:

| Path | GET | POST |
|------|-----|------|
| `/bmi` | SPA (`file_server` + fallback) | `reverse_proxy` → app |
| `/plan` | SPA | `reverse_proxy` → app |
| `/insight` | SPA | `reverse_proxy` → app |
| `/premium_bmr` | SPA | `reverse_proxy` → app |
| `/premium_targets` | SPA | `reverse_proxy` → app |

Caddy matches **POST** only for this set before the general API matcher.

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

- Docker build ARG `VITE_API_BASE` (default `https://pulseplate.app/api/v1`). Override for staging/other hosts when building the Caddy image.

## QA smoke checklist (after deploy)

- **MIME:** `GET /` returns `text/html`; `GET /health` returns JSON (via proxy).
- **Deep link:** `GET /bmi` (or another client route) serves SPA `index.html` (not API).
- **Legacy POST:** `POST /bmi` (and peers) reaches FastAPI (not static 405 from `file_server`).
- **OpenAPI:** `GET /openapi.json` proxied (200, JSON).
- **Ops:** `GET /metrics` proxied when enabled; `GET /ready` behavior unchanged.
- **WebSocket:** upgrade to `/ws` reaches app when feature flag allows.

## References

- [`deploy/docker-compose.production.yaml`](../../deploy/docker-compose.production.yaml)
- [`deploy/AGENTS.md`](../../deploy/AGENTS.md)
