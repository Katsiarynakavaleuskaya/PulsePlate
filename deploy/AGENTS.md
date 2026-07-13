# Agent instructions (scope: deploy/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `deploy/` and below.
- Key files: `deploy/Caddyfile`, `deploy/Caddyfile.production`, `deploy/docker-compose.staging.yaml`,
  `deploy/docker-compose.production.yaml`, `deploy/docker-compose.production.selfhosted.yaml`,
  `frontend/Dockerfile.caddy-spa`, root `Dockerfile`, root `docker-compose.yaml`.
- **METATRON offensive lab (out-of-band):** `deploy/metatron-lab/` — optional isolated-network
  stub only; see `deploy/metatron-lab/README.md:1` and ADR
  `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`.

## Production Caddy + SPA (apex)

- **Contract:** [`docs/deploy/SPA_APEX_ROUTING_CONTRACT.md`](../docs/deploy/SPA_APEX_ROUTING_CONTRACT.md) — path/method split (legacy POST/OPTIONS/GET vs SPA GET on `/bmi`), proxy prefixes, default `VITE_API_BASE=/api/v1` (same-origin). FastAPI legacy HTML surfaces under `/legacy*` are proxied via the `@api` matcher (`deploy/Caddyfile.production:42`) so they are not swallowed by SPA `try_files`.
- **Build Caddy image** (from repo root; compose uses `frontend/` as build context so root `.dockerignore` stays backend-focused):

```bash
docker compose -f deploy/docker-compose.production.yaml build caddy
```

- **Self-hosted Postgres lane** (colocated `postgres` + `app` + `caddy`): `deploy/docker-compose.production.selfhosted.yaml`. Build Caddy the same way with that file:

```bash
docker compose --project-directory deploy -f deploy/docker-compose.production.selfhosted.yaml build caddy
```

- **Override API base at image build time** (staging / alternate host):

```bash
VITE_API_BASE=https://staging.example.com/api/v1 docker compose -f deploy/docker-compose.production.yaml build caddy
```

- **`deploy/docker-compose.production.yaml`** references `env_file: .env` for the `app` service (path relative to `deploy/`). Create a local `deploy/.env` (gitignored) before `docker compose config` / up, or Compose will error if the file is missing.
- **Validate Caddyfile** with the repo-owned hardened image (requires Docker daemon + placeholder env for `{$PRODUCTION_DOMAIN}`):

```bash
docker build -f frontend/Dockerfile.caddy-spa -t pulseplate-caddy:contract frontend
PRODUCTION_DOMAIN=example.com STAGING_FALLBACK_DOMAIN=staging.example.com \
  docker run --rm -e PRODUCTION_DOMAIN -e STAGING_FALLBACK_DOMAIN \
  -v "$PWD/deploy/Caddyfile.production:/etc/caddy/Caddyfile:ro" \
  pulseplate-caddy:contract caddy validate --config /etc/caddy/Caddyfile
```

- Staging deploys accept only two distinct `ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:<digest>` references (backend and Caddy). Floating tags and `latest` are forbidden.
- `STAGING_ATTESTED_DIGEST_READY=true` may be enabled only after the server-local Compose, Caddyfile, deploy script, Postgres backup helper, root-owned contract marker, and current-commit hashes are synchronized. The staging `.env` must be a regular non-symlink file with mode `0600`; it is Compose data and must never be shell-sourced by the deploy path. Merge alone does not update `/srv/pulseplate-staging`.

## Commands (run from repo root)
- Build images: `make docker-build`, `make docker-build-dev`
- Run containers: `make docker-run`, `make docker-run-dev`
- Stop containers: `make docker-stop`

## Experiment Runner image

- `deploy/experiment-runner/Containerfile` is a local evidence image, not a
  production or devcontainer image.
- Keep its Python base tag pinned by OCI digest, install only locked
  `runtime-dev` requirements through BuildKit secrets, and keep the final user
  non-root.
- Image builds may use the approved private proxy. Experiment runs must use a
  prebuilt immutable `name@sha256:<digest>` reference and must not install
  dependencies or pull images after the strict backend probe.
- Post-build admission must inspect image history/config for private-proxy
  secret names and values. Apple runs use the exact inspected
  `name@sha256:<digest>`; Docker runs use the verified local digest with
  `--pull never` and re-check the name-to-digest binding before execution.
- Do not add Compose services, runtime sockets, host home/keychain mounts,
  `SYS_ADMIN`, or other broad capabilities for this image.

## Conventions
- Keep staging and production configs in sync with documented env vars.
- Avoid changes that alter runtime ports without updating clients and docs.

## Production tag gate
- Semver production tags stay build-only until all three deploy inputs agree: `PROD_DEPLOY_MODE`,
  `WEB_IOS_RELEASE_READY=true`, and `PRODUCTION_ENV_READY=true`.
- `PRODUCTION_ENV_READY=true` is infra-owned and can be set only after the target host already has
  the server-local runtime env file (`/srv/pulseplate-production/.env` or `$DEPLOY_DIR/.env`).
- If the default `github.token` cannot read production-scoped Actions variables, the bridge job may
  retry through `PRODUCTION_ENV_READ_TOKEN`; keep that secret aligned with the deploy runbook.

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
