# Production Deployment (Auto-deploy)

This repo publishes production images to GHCR and can optionally auto-deploy to a production server via
SSH + `docker compose`.

## Source of truth: production image

For any tag `vX.Y.Z`, the production build publishes:

- `ghcr.io/<owner>/<repo>:prod-vX.Y.Z`

Deployments should use a pinned digest (preferred) or `prod-v*` tags (acceptable). Do not deploy
`latest` as it may be pushed by multiple workflows.

## Server prerequisites (one-time)

On the production server:

- Docker + Docker Compose v2 installed (`docker compose version`)
- A deploy directory (default: `/srv/pulseplate-production`) containing:
  - `docker-compose.yml` (or a compose file you run from that directory)
  - `.env` (application runtime env; not committed)
- Compose must reference `IMAGE_REF` (recommended) or `TAG` (backwards-compatible):

Example `docker-compose.yml`:

```yaml
services:
  app:
    image: ${IMAGE_REF:?IMAGE_REF is required}
    restart: unless-stopped
    ports: ["8000:8000"]
    env_file: [".env"]
    command: >
      uvicorn app.main:app --host 0.0.0.0 --port 8000
      --proxy-headers
```

## GitHub Environment + Secrets

Configure GitHub Environment `production` with required reviewers (recommended).

Secrets (store in the `production` environment):

- `SSH_HOST_PRODUCTION`
- `SSH_USER`
- `SSH_KEY` (private key)
- `GHCR_READ_TOKEN` (PAT with `read:packages`, if the image is private)
- `PRODUCTION_DOMAIN` (public domain used for post-deploy healthcheck)

## Post-merge checklist (first production auto-deploy)

1. Ensure the production server deploy directory exists at either `/opt/pulseplate` or
   `/srv/pulseplate-production` and contains the compose file + `.env`.
2. Ensure the compose file uses `IMAGE_REF` (preferred) or `TAG` (backwards-compatible).
3. Wait for a successful Nightly run on `main`, then create and push a new semver tag (e.g. `v0.2.2`).
4. Approve the `deploy-production` job in the GitHub `production` environment prompt.
5. Verify `/health` via `https://$PRODUCTION_DOMAIN/health` and confirm the running container uses the
   expected `ghcr.io/<owner>/<repo>@sha256:...` digest.

## Rollback

Rollback is re-deploying the previous `prod-v*` digest/tag using the same mechanism.
