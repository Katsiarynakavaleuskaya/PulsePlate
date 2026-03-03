# Production Deployment (Auto-deploy)

This repo publishes production images to GHCR and can optionally auto-deploy to a production server via
SSH + `docker compose`.

**📌 Important:** See `deploy/WORKFLOW.md` for the canonical deployment workflow (where to make changes, when to deploy, etc.).

## Deploy mode (required)

Auto-deploy is controlled by repository or environment variable `PROD_DEPLOY_MODE`:

- `ssh`: Deploy from GitHub-hosted runners over SSH (port 22 reachable). SSH key must be full PEM including newlines to avoid "ssh: no key found". Required Environment "production" secrets: `SSH_HOST_PRODUCTION`, `SSH_USER`, `SSH_KEY`, `PRODUCTION_DOMAIN`, `GHCR_READ_TOKEN`.  <!-- pragma: allowlist secret -->
- `self-hosted`: Deploy from a self-hosted runner inside your infrastructure (recommended).

If `PROD_DEPLOY_MODE` is unset or any other value, deploy jobs are skipped (images are still built and pushed to GHCR).

## Global release-readiness lock (required)

Deployment jobs in CD are additionally gated by:

- `WEB_IOS_RELEASE_READY=true`

Canonical policy:

- While web and iOS are not release-ready, keep `WEB_IOS_RELEASE_READY` unset or `false`.
- In this state, CD remains build/validation only (no production deploy), while image build/push can still run.
- In this state, `STAGING_FALLBACK_DOMAIN` (default: `pulseplate-staging.duckdns.org`) is served by a fallback vhost in `deploy/Caddyfile.production`
  to keep staging HTTPS alive and avoid TLS handshake failures.
- Enable real production deploy only after release readiness is explicitly confirmed.

## Source of truth: production image

For any tag `vX.Y.Z`, the production build publishes:

- `ghcr.io/<owner>/<repo>:prod-vX.Y.Z`

Deployments should use a pinned digest (preferred) or `prod-v*` tags (acceptable). Do not deploy
`latest` as it may be pushed by multiple workflows.

## Server prerequisites (one-time)

On the production server:

- Docker + Docker Compose v2 installed (`docker compose version`)
- A deploy directory containing:
  - a compose file (`docker-compose.yml`, `docker-compose.production.yaml`, etc.)
  - `.env` (application runtime env; not committed)
  - `Caddyfile.production` (Caddy reverse proxy config; see Caddyfile Configuration below)
- Compose must reference `IMAGE_REF` (recommended) or `TAG` (backwards-compatible):
- **Firewall configured**: Ports 80 (HTTP) and 443 (HTTPS) must be open (see Firewall Setup below)

Example `docker-compose.production.yaml`:

```yaml
networks:
  web:
    external: false
    ipam:
      config:
        - subnet: 172.30.100.0/24

volumes:
  caddy_data:
  caddy_config:

services:
  app:
    image: ${IMAGE_REF:?IMAGE_REF is required}
    restart: unless-stopped
    networks: [web]
    expose: ["8000"]  # Internal only, accessed via Caddy
    env_file: [".env"]
    command: >
      uvicorn app.main:app --host 0.0.0.0 --port 8000
      --proxy-headers
      --forwarded-allow-ips="172.30.100.0/24"

  caddy:
    image: caddy:2.10.2
    restart: unless-stopped
    networks: [web]
    ports:
      - "80:80"
      - "443:443"
    environment:
      - PRODUCTION_DOMAIN=${PRODUCTION_DOMAIN}
      - STAGING_FALLBACK_DOMAIN=${STAGING_FALLBACK_DOMAIN:-pulseplate-staging.duckdns.org}  # optional fallback domain
    volumes:
      - ./Caddyfile.production:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on: [app]
```

## Caddyfile Configuration

The production Caddy configuration is located at:

**`deploy/Caddyfile.production`**

It already contains a complete and secure reverse proxy setup using the `{$PRODUCTION_DOMAIN}` environment variable and does not need to be created manually.
It also contains a staging TLS fallback vhost for `STAGING_FALLBACK_DOMAIN` (default: `pulseplate-staging.duckdns.org`) used during build-only phases.

**To use it on the production server:**

1. Copy the file to your deploy directory:

   ```bash
   cp deploy/Caddyfile.production /srv/pulseplate-production/
   # or
   cp deploy/Caddyfile.production /opt/pulseplate/
   ```

2. Ensure the file is readable by Docker (mode 644 or similar):

   ```bash
   chmod 644 ./Caddyfile.production
   ```

3. The compose file mounts it as `./Caddyfile.production` (relative to the deploy directory).

**Note:** The Caddyfile uses `{$PRODUCTION_DOMAIN}` which must be set in your `.env` file or exported as an environment variable when starting the compose stack.

## Required Environment Variables

The following environment variables must be set in your `.env` file or exported in the shell:

- **`PRODUCTION_DOMAIN`** (required): Your production domain name (e.g., `api.pulseplate.com`)
- **`STAGING_FALLBACK_DOMAIN`** (optional): staging hostname served by production fallback vhost in build-only mode (default: `pulseplate-staging.duckdns.org`)
- **`IMAGE_REF`** (required): Docker image reference (e.g., `ghcr.io/owner/repo@sha256:...`)

Example `.env` file:

```bash
PRODUCTION_DOMAIN=api.pulseplate.com
STAGING_FALLBACK_DOMAIN=pulseplate-staging.duckdns.org
IMAGE_REF=ghcr.io/owner/repo@sha256:abc123...
# Add other application-specific variables here
```

**Security Note:** Never commit `.env` files to the repository. If deploying via GitHub Actions, store sensitive variables as GitHub Secrets in the `production` environment.

## Firewall Setup (Critical!)

**RU: Критически важно открыть порты 80 и 443 для Caddy.**
**EN: Critical: Ports 80 and 443 must be open for Caddy.**

### UFW (Ubuntu/Debian)

```bash
# Install UFW if not present
sudo apt install -y ufw

# Allow SSH (verify your SSH port first!)
SSH_PORT=$(grep -E "^Port " /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' || echo "22")
sudo ufw allow ${SSH_PORT}/tcp

# Allow HTTP and HTTPS (REQUIRED for Caddy)
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# Enable firewall
sudo ufw --force enable

# Verify firewall status
sudo ufw status
```

Expected output should show:

```text
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

### DigitalOcean Firewall (if using DO Firewall)

In DigitalOcean Control Panel → Networking → Firewalls:

1. Create or edit firewall rules
2. Add inbound rules:
   - **HTTP**: Port 80, Protocol TCP, Source: All IPv4, All IPv6
   - **HTTPS**: Port 443, Protocol TCP, Source: All IPv4, All IPv6
   - **SSH**: Port 22 (or your custom port), Protocol TCP, Source: Your IP (recommended)

### Verify Ports Are Open

```bash
# Check if ports are listening (from server)
sudo netstat -tlnp | grep -E ':(80|443)'
# OR
sudo ss -tlnp | grep -E ':(80|443)'

# Expected output should show Caddy listening:
# tcp  0  0 0.0.0.0:80  0.0.0.0:*  LISTEN  <pid>/caddy
# tcp  0  0 0.0.0.0:443 0.0.0.0:*  LISTEN  <pid>/caddy

# Test from external machine (replace with your domain)
curl -I http://your-domain.com/health
curl -I https://your-domain.com/health
```

### Verify Caddy Container

```bash
# Check Caddy container is running
docker compose ps caddy

# Check Caddy logs
docker compose logs caddy

# Verify Caddy is proxying to app:8000
docker compose exec caddy cat /etc/caddy/Caddyfile
```

## Remote Server Check (when SSH is not available)

If `ssh root@pulseplate.app` times out (common when behind Cloudflare), you can still check the server status remotely:

### Quick Health Check (from anywhere)

```bash
curl -fsS https://pulseplate.app/health | jq .
```

Expected output:

```json
{
  "status": "ok",
  "environment": "production",  // Should be "production", not "development"
  "git_sha": "abc12345",         // Should be real SHA, not "unknown"
  ...
}
```

### Accessing the Server

If SSH port 22 is blocked, try:

1. **DigitalOcean Console** (or your VPS provider's web console):
   - Access via provider dashboard → Droplet → Console
   - Run commands directly on the server

2. **Alternative SSH port** (if configured):

   ```bash
   ssh -p 2222 root@pulseplate.app
   ```

3. **Self-hosted runner** (recommended):
   - If you have a self-hosted runner on the server, use it to execute commands
   - See `scripts/REMOTE_SERVER_CHECK.md` for detailed instructions

For detailed remote check instructions, see `scripts/REMOTE_SERVER_CHECK.md`.

## GitHub Environment + Secrets

Configure GitHub Environment `production` with required reviewers (recommended).

Secrets (store in the `production` environment):

- `SSH_HOST_PRODUCTION`
- `SSH_USER`
- `SSH_KEY` (private key)
- `GHCR_READ_TOKEN` (PAT with `read:packages`, if the image is private)
- `PRODUCTION_DOMAIN` (public domain used for post-deploy healthcheck)

Variables (store in the `production` environment):

- `DEPLOY_DIR` (optional): absolute path to the deploy directory on the production machine.
  If unset, the workflow auto-detects `/opt/pulseplate` then `/srv/pulseplate-production`.
- `WEB_IOS_RELEASE_READY` (required for deploy): set to `true` only when web+iOS release readiness is approved.

## Self-hosted runner (recommended)

If your server exposes only 443 publicly (common behind Cloudflare), GitHub-hosted runners cannot SSH
into it. Use a self-hosted runner on the production machine (or inside the same network).

Workflow expectation:

- runner labels: `self-hosted`, `linux`, `x64`, `pulseplate-prod`

High-level steps (run on the production server):

1. Create a dedicated user (recommended) and allow Docker access:

   - `sudo useradd -m -s /bin/bash github-runner`
   - `sudo usermod -aG docker github-runner`

2. Install and configure the GitHub Actions runner (use repo settings UI to generate the config token).
3. Add the runner label `pulseplate-prod`.
4. Set repository variable `PROD_DEPLOY_MODE=self-hosted`.

## Post-merge checklist (first production auto-deploy)

1. **Firewall**: Ensure ports 80 and 443 are open (see Firewall Setup above).
2. Ensure the production server deploy directory contains:
   - compose file (`docker-compose.production.yaml`)
   - `.env` (application runtime env)
   - `Caddyfile.production` (copied from `deploy/Caddyfile.production`)
3. Ensure the compose file uses `IMAGE_REF` (preferred) or `TAG` (backwards-compatible).
4. Wait for a successful Nightly run on `main`, then create and push a new semver tag (e.g. `v0.2.2`).
5. Ensure `PROD_DEPLOY_MODE` is set (`self-hosted` recommended).
6. Approve the deploy job in the GitHub `production` environment prompt.
7. **Verify deployment**:
   - Check Caddy container: `docker compose ps caddy`
   - Check ports: `sudo ss -tlnp | grep -E ':(80|443)'`
   - Verify health: `curl -I https://$PRODUCTION_DOMAIN/health`
   - Confirm container digest: `docker compose exec app cat /app/.git/HEAD` (or check image digest)

## Redeploy Caddy Container

If you need to redeploy the Caddy container (e.g., after updating `Caddyfile.production`), use the provided script:

### On the Server

```bash
# Option 1: Use the automated script (recommended)
bash scripts/redeploy_caddy.sh

# Option 2: Manual commands
cd /srv/pulseplate-production  # or your deploy directory
docker compose -f docker-compose.production.yaml pull caddy
docker compose -f docker-compose.production.yaml up -d caddy
docker compose -f docker-compose.production.yaml ps caddy
docker compose -f docker-compose.production.yaml logs --tail=100 caddy
```

The script will:

1. Auto-detect the deploy directory
2. Pull the latest Caddy image
3. Restart the Caddy container
4. Show container status and recent logs

**Note:** If SSH is not available, use DigitalOcean Console or self-hosted runner to execute these commands.

## Rollback

Rollback is re-deploying the previous `prod-v*` digest/tag using the same mechanism.
