# SPA at apex — routing contract (Caddy + FastAPI)

**Status:** Contract for production/staging Caddy in [`deploy/Caddyfile.production`](../../deploy/Caddyfile.production) (legacy matchers at `deploy/Caddyfile.production:14`).
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

Caddy `path` matching is **exact** (no automatic trailing-slash merge). Legacy matchers list both `/foo` and `/foo/` for POST, OPTIONS, and GET so clients that append a trailing slash still hit FastAPI (`deploy/Caddyfile.production:14`).

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
| `/privacy`, `/terms` | Legal JSON endpoints (no SPA route today) |
| `/legacy*` | FastAPI-only legacy surfaces (embedded HTML BMI UI: `legacy_app.py:1493`) |
| `/debug_env` | Debug (gate in prod env) |

**Caddy matcher evidence:** `/legacy*` is included in the `@api` path list in [`deploy/Caddyfile.production:42`](../../deploy/Caddyfile.production).

## Direct uvicorn / bypass Caddy

When traffic hits **FastAPI only** (port `8000`, misconfigured clients, internal probes), **`GET /`** returns a **small JSON probe** (stable `service` / `surface` / `links`; handler `legacy_app.py:1487`, payload builder `app/bootstrap/direct_api_root.py:18`). The historical embedded HTML calculator is at **`GET /legacy/bmi-calculator`** (`legacy_app.py:1493`, template `app/bootstrap/legacy_bmi_web_html.py:9`). Production browsers still receive **`text/html`** for **`GET /`** from Caddy’s `file_server` at apex; they do not see this JSON unless they bypass the edge.

**Operator trap:** `curl https://<your-apex-domain>/` **through Caddy** returns the SPA shell (`text/html`), **not** the JSON probe. Use direct uvicorn/port `8000`, or call **`GET /health`**, to verify the API behind the edge.

## Static (Caddy `file_server`)

- Built assets under `/srv/frontend` (from [`frontend/Dockerfile.caddy-spa`](../../frontend/Dockerfile.caddy-spa)).
- **`/favicon.ico`**: prefer `dist` (not proxied to app).

## CSP

- API responses may set CSP via app middleware.
- Static HTML from Caddy does not automatically get the same headers; avoid duplicating conflicting CSP on static responses unless product/security requires it (follow-up if needed).

## Build-time API base

- Docker build ARG `VITE_API_BASE` (default same-origin `/api/v1`). Override with an absolute URL for split-origin or Workers-backed API builds ([`frontend/Dockerfile.caddy-spa:17`](../../frontend/Dockerfile.caddy-spa)).

## QA smoke checklist (after deploy)

- **MIME (through Caddy):** `GET /` returns SPA `text/html` from static `file_server`; `GET /health` returns JSON (via proxy).
- **Direct API:** `GET /` on uvicorn returns JSON probe (`app/bootstrap/direct_api_root.py:18`); legacy HTML UI: `GET /legacy/bmi-calculator` (proxied via `/legacy*` in `deploy/Caddyfile.production:42`).
- **Deep link:** `GET /bmi` serves SPA `index.html` (not API); `GET /plan` (no SPA route) is proxied to the app.
- **Legacy POST:** `POST /bmi` (and peers) reaches FastAPI (not static 405 from `file_server`).
- **OpenAPI:** `GET /openapi.json` proxied (200, JSON).
- **Ops:** `GET /metrics` proxied when enabled; `GET /ready` behavior unchanged.
- **WebSocket:** upgrade to `/ws` reaches app when feature flag allows.

## References

- [`deploy/docker-compose.production.yaml`](../../deploy/docker-compose.production.yaml)
- [`deploy/AGENTS.md`](../../deploy/AGENTS.md)
