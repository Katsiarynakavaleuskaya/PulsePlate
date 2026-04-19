# Cloudflare Pages + Worker Deploy

## Scope

This repo supports a split Cloudflare deployment:

- `frontend/` -> Cloudflare Pages static SPA
- `worker.js` -> optional Cloudflare Worker API proxy for `/api/*`

The Worker is bounded by policy and should be deployed only when you need a
first-party API proxy in front of an existing HTTPS origin.

This runbook adds a modern frontend deployment lane only. It does **not** move
the current production domain away from the existing backend-origin stack.

## Authentication

Use one of these two auth modes before any real deploy:

1. Interactive local auth:

   ```bash
   npx wrangler login
   npx wrangler whoami
   ```

2. Token-based auth for CI or non-interactive local deploys:

   ```bash
   export CLOUDFLARE_API_TOKEN=<your-token>
   npx wrangler whoami
   ```

If `npx wrangler whoami` prints `You are not authenticated`, neither auth mode
is active in the current shell.

## Frontend (Pages)

### Build settings

- Root directory: `frontend`
- Build command: `npm ci && npm run build`
- Build output directory: `dist`

### Production ownership note

- Current production remains backend-origin based: `Cloudflare -> Caddy -> uvicorn`
- Cloudflare Pages is a separate frontend lane for modern SPA delivery
- Production domain cutover is intentionally out of scope for this lane

### Required Pages environment variables

- `VITE_API_BASE`
  - Required.
  - Recommended value when using the Worker proxy:
    `https://<worker-name>.<account-subdomain>.workers.dev`
  - Alternative value when calling an existing public API directly:
    `https://<public-api-origin>/api/v1`

### Optional Pages environment variables

- `VITE_ANALYTICS_ENABLED`
  - Default repo example: `false`
- `VITE_VIP_MODULE_ENABLED`
  - Default repo example: `false`
- `VITE_HPP_LIVE_WS_URL`
  - Leave unset unless a websocket-capable public endpoint exists

### SPA routing

Cloudflare Pages needs a fallback for React Router. The repo provides it via:

- `frontend/public/_redirects`

## Worker (`worker.js`)

### Deploy command

```bash
npx wrangler deploy
```

### Required Worker variables

- `TARGET_BASE`
  - Required.
  - Must be an explicit HTTPS origin.
  - Example: `https://pulseplate.app`
- `WORKER_ALLOWED_ORIGINS`
  - Required for browser use.
  - Comma-separated trusted origins.
  - Example:
    `https://pulseplate-frontend.pages.dev,https://app.pulseplate.app`

### Secret handling

Do not commit runtime secrets into `wrangler.toml`.
Set Worker values in the Cloudflare dashboard or via Wrangler secrets/vars.

## Token creation guidance

### Local manual deploy

1. Create a Cloudflare API token in the dashboard.
2. Prefer the minimal Pages permission set when you only need direct upload.
3. Export it in the local shell:

   ```bash
   export CLOUDFLARE_API_TOKEN=<your-token>
   npx wrangler whoami
   ```

### CI / GitHub Actions

1. Add `CLOUDFLARE_API_TOKEN` to GitHub Actions secrets.
2. If a future Pages/Workers workflow needs account-level parameters, also add
   `CLOUDFLARE_ACCOUNT_ID`.
3. Use token-based auth in CI; do not rely on `wrangler login`.

### Recommended standard

- Project default: `CLOUDFLARE_API_TOKEN`
- Debug-only fallback: `npx wrangler login`

## Recommended rollout

1. Deploy the Worker first if Pages should call it as `VITE_API_BASE`.
2. Copy the Worker URL.
3. Set `VITE_API_BASE` in the Pages project.
4. Deploy Pages.

## Verification

### Worker

```bash
npx wrangler whoami
npx wrangler deploy
```

### Pages

```bash
cd frontend
npm ci
VITE_API_BASE=https://<worker-or-api-origin> npm run build
npx wrangler pages deploy dist --project-name <pages-project-name>
```
