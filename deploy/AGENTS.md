# Agent instructions (scope: deploy/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `deploy/` and below.
- Key files: `deploy/Caddyfile`, `deploy/Caddyfile.production`, `deploy/docker-compose.staging.yaml`,
  root `Dockerfile`, root `docker-compose.yaml`.

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
