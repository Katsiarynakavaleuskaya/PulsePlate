# Agent instructions (scope: deploy/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `deploy/` and below.
- Key files: `deploy/Caddyfile`, `deploy/Caddyfile.production`, `deploy/docker-compose.staging.yaml`,
  `deploy/docker-compose.production.yaml`, `frontend/Dockerfile.caddy-spa`,
  root `Dockerfile`, root `docker-compose.yaml`.

## Production Caddy + SPA (apex)

- **Contract:** [`docs/deploy/SPA_APEX_ROUTING_CONTRACT.md`](../docs/deploy/SPA_APEX_ROUTING_CONTRACT.md) — path/method split (legacy POST/OPTIONS/GET vs SPA GET on `/bmi`), proxy prefixes, default `VITE_API_BASE=/api/v1` (same-origin). FastAPI legacy HTML surfaces under `/legacy*` are proxied via the `@api` matcher (`deploy/Caddyfile.production:42`) so they are not swallowed by SPA `try_files`.
- **Build Caddy image** (from repo root; compose uses `frontend/` as build context so root `.dockerignore` stays backend-focused):

```bash
docker compose -f deploy/docker-compose.production.yaml build caddy
```

- **Override API base at image build time** (staging / alternate host):

```bash
VITE_API_BASE=https://staging.example.com/api/v1 docker compose -f deploy/docker-compose.production.yaml build caddy
```

- **`deploy/docker-compose.production.yaml`** references `env_file: .env` for the `app` service (path relative to `deploy/`). Create a local `deploy/.env` (gitignored) before `docker compose config` / up, or Compose will error if the file is missing.
- **Validate Caddyfile** (requires Docker daemon + placeholder env for `{$PRODUCTION_DOMAIN}`):

```bash
PRODUCTION_DOMAIN=example.com STAGING_FALLBACK_DOMAIN=staging.example.com \
  docker run --rm -e PRODUCTION_DOMAIN -e STAGING_FALLBACK_DOMAIN \
  -v "$PWD/deploy/Caddyfile.production:/etc/caddy/Caddyfile:ro" \
  caddy:2.10.2 caddy validate --config /etc/caddy/Caddyfile
```

## Commands (run from repo root)
- Build images: `make docker-build`, `make docker-build-dev`
- Run containers: `make docker-run`, `make docker-run-dev`
- Stop containers: `make docker-stop`

## Conventions
- Keep staging and production configs in sync with documented env vars.
- Avoid changes that alter runtime ports without updating clients and docs.

## Docker entrypoint invariants
Docker must run FastAPI as:
- `app.main:app`

Do not COPY missing legacy files (e.g., app.py) after refactors.

Verify with:
```bash
# Check for obsolete app.py copies
rg -n "COPY .*app\.py|COPY .*legacy_app\.py" Dockerfile

# Verify uvicorn entrypoint
rg -n "uvicorn\s+app(:|.main:app)|legacy_app" Dockerfile Makefile docker-compose.yaml -S

# Should use app.main:app
rg -n "app\.main:app" Dockerfile Makefile docker-compose.yaml -S
```
