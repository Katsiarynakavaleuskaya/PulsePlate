# 🚀 Staging Server Setup Guide

## Protected PostgreSQL staging contract v5

This section owns the current bootstrap for existing DigitalOcean staging
Droplet `594869239` (`pulseplate-staging-fra1-01`, FRA1). Production hosts and
managed production remain outside this operation. The owner authorized one
50 GiB Volume named `pulseplate-staging-data`, at $5/month; no additional paid
snapshots are included. Check actual disk/data use before creation. An active
Droplet or reachable SSH port does not prove a working administrative login.

The current operator login is `pulseplate-ops` with key authentication;
root and password SSH logins are disabled. Use the dedicated
`~/.ssh/pulseplate_staging_obs1_20260824` key and
`~/.ssh/known_hosts_pulseplate_staging_obs1_20260824` trusted host record,
with strict host-key checking and the authenticated Droplet address.
Use `sudo` from that account for privileged preparation and deployment.
A trusted SSH fingerprint must come from the authenticated Recovery Console or
an existing trusted host record. A console timeout is not evidence that the VM is
down. Do not reset/rebuild the VM or disable host-key checking to work around it.
After login, census Docker/Compose, mounts, existing containers/volumes, data
and available capacity. The fresh-host path below requires observed absence of
old application data. A discovered existing database, TSDB or named volume must
be preserved and given an explicit backup/restore migration before re-binding.

### Install the exact merged bundle

Copy these paths from the same verified merged revision under
`/srv/pulseplate-staging`, preserving the relative directories shown:

- `scripts/deploy.sh` becomes `deploy.sh`; `deploy/docker-compose.staging.yaml`
  becomes `docker-compose.staging.yaml`; `deploy/Caddyfile` becomes `Caddyfile`.
- `scripts/ops/postgres_backup.sh`, `scripts/ops/postgres_restore.sh` and
  `scripts/ops/check_staging_security.py` retain their `scripts/ops/` paths.
- `scripts/ci/check_pgvector_attestations.py` and
  `scripts/ci/check_docker_provenance_attestation.py` retain `scripts/ci/`.
- `deploy/postgres-pgvector/image-manifest.json` and `pg_hba.conf` become
  `postgres-pgvector/image-manifest.json` and `postgres-pgvector/pg_hba.conf`.
- `deploy/prometheus/prometheus.yml` and `image-manifest.json` become the
  corresponding `prometheus/` files.
- `deploy/systemd/pulseplate-staging-storage.conf` and
  `pulseplate-staging-postgres-backup.service.example` become
  `systemd/pulseplate-staging-storage.conf` and
  `systemd/pulseplate-postgres-backup.service.example`, respectively. Retain
  the existing backup timer example as well.

Use root-owned regular files, mode `0644` for helpers/systemd files and `0755`
for shell entrypoints; PostgreSQL HBA is `0444`. Keep the current staging marker
and all CD checksum guards. The marker is not a replacement for synchronization.
Install the official Docker/Compose, Python, OpenSSL and GitHub CLI runtime if
absent, then record their actual versions. Registry verification uses temporary
credentials and exact digests; the host never receives DHI credentials.

### Bind the encrypted device before storage writers

Authenticate the returned DigitalOcean Volume ID and attachment to only this
Droplet. Check its actual `/dev/disk/by-id/scsi-0DO_Volume_pulseplate-staging-data`
identity and size before any format command. Format only an observed new blank
Volume as ext4; do not reformat an existing filesystem. Read its filesystem UUID
with native `blkid` and mount it at `/mnt/pulseplate-staging-data`.

Provision these directories on that mounted device:

| Directory | Owner | Mode |
|---|---|---|
| mount root | `0:0` | `0755` |
| `postgres` | `70:70` | `0700` |
| `prometheus` | `65532:65532` | `0700` |
| `backups` | `0:0` | `0700` |
| `secrets` | `0:0` | `0700` |

Bind-mount its `secrets` directory at `/srv/pulseplate-staging/secrets`; use a
real mount, not a symlink. Configure UUID-bound systemd/fstab mounts for both
paths. The escaped unit names are
`mnt-pulseplate\x2dstaging\x2ddata.mount` and
`srv-pulseplate\x2dstaging-secrets.mount`. Docker and backup consumers depend
on both mounts through `RequiresMountsFor`, `BindsTo` and `After`. Do not make
these mounts required by `multi-user.target`, so the VM remains available for
host recovery when the Volume cannot activate. Both consumers must fail closed
on mount failure; do not add a root-disk storage fallback.

Write root-owned mode-`0600` `.staging-storage.json` with the exact closed fields:

```json
{
  "schema": "pulseplate.staging-storage.v1",
  "droplet_id": 594869239,
  "volume_id": "REPLACE_WITH_AUTHENTICATED_VOLUME_UUID",
  "volume_name": "pulseplate-staging-data",
  "filesystem_uuid": "REPLACE_WITH_OBSERVED_FILESYSTEM_UUID",
  "mountpoint": "/mnt/pulseplate-staging-data",
  "device": "/dev/disk/by-id/scsi-0DO_Volume_pulseplate-staging-data",
  "size_gib": 50,
  "backend_uid": 0,
  "backend_gid": 0
}
```

The two `0` values above are deliberately invalid placeholders, not defaults. Obtain UID/GID from
the admitted backend image in a disposable network-disabled container and use
those actual values. The record is operator configuration of expected bindings,
not standalone evidence of provider encryption or of actual attachment.
The checker independently requires the real block device, exact mount, UUID,
50 GiB capacity, directory identities and a separate root filesystem.

Install `systemd/pulseplate-staging-storage.conf` as
`/etc/systemd/system/docker.service.d/pulseplate-storage.conf`, then reload
systemd. This staging-only drop-in checks storage before Docker starts, binds
the daemon to both mount units and explicitly disables live restore. Validate
the loaded unit and actual Docker setting before enabling application writers.
Inspect any existing named volumes' `Driver` and `Options`; Compose changes do
not convert an existing ordinary Docker volume into the new bind-backed volume.

### Preserve the existing cluster before the v5 cutover

The trusted 2026-09-13 census found PostgreSQL `15.19` with TLS off,
`pulseplate_staging` at about 7.95 MB and zero public tables, plus the
`postgres` maintenance database. The old PostgreSQL volume uses about
47,308 KiB; Prometheus and food cache volumes use about 4 KiB each. This is
an existing cluster to preserve, even though application tables are absent.
Refresh these observations immediately before the operator-selected migration.

Staging keeps its existing Compose project and logical `postgres_data` and
`prometheus_data` sources. Its reviewed Compose selects new physical names
`pulseplate-staging_postgres_data_v5` and
`pulseplate-staging_prometheus_data_v5`, bound to the encrypted `postgres` and
`prometheus` directories. Existing `pulseplate-staging_postgres_data`,
`pulseplate-staging_prometheus_data` and food cache volumes remain intact.
Do not change their driver options, rebind them, delete them or use
`external: true` to bypass the checked bind-volume contract.

This preparation is the owner's selected preservation/migration and first
application setup, separate from automatic `deploy.sh` execution:

1. Census writers, the actual PGDATA/data mount, PostgreSQL version, databases,
   roles, extensions, `pg_tblspc` links and any external `pg_wal` location.
   A complete copy must include WAL and all tablespaces; an unverified external
   path remains HOLD rather than being silently omitted.
2. Keep app/worker traffic quiesced and stop the old PostgreSQL server cleanly.
   Copy the complete stopped cluster through a read-only source mount into the
   verified empty encrypted PostgreSQL directory. Preserve numeric ownership,
   permissions and file contents; verify the copy and retain an independently
   restorable private cluster backup before changing the service binding.
   Do not copy live PGDATA or initialize over either old or copied data.
3. Stop Prometheus before copying its TSDB into the empty encrypted Prometheus
   directory; verify the copy and apply the selected runtime ownership only to
   that copy. Preserve the original history and old volume for rollback.
4. Prepare the TLS/credential files described below. The copied roles retain
   their persisted password verifiers: a new password file does not change
   them. Establish matching admitted password/passfile contents and SCRAM
   compatibility without logging passwords or verifiers. MD5-only verifiers,
   an incompatible legacy password format or failed `verify-full` authentication
   remain HOLD for the selected credential migration on the copy; the original
   cluster remains unchanged.
5. Start and verify the copied cluster using the exact selected PostgreSQL
   image, TLS configuration and new named-volume binding. Verify database/role
   preservation and real `pg_stat_ssl` through the application passfile.
   Cut the existing Compose `postgres` service over to that verified copy,
   retaining the project identity. A running old-volume service will fail the
   deploy volume-name check; a new volume without a trustworthy running service
   also remains HOLD.
6. Because the observed copied application database has zero public tables,
   run canonical `alembic upgrade head` from the verified backend image against
   the copied TLS database while writers remain quiesced. Verify the actual
   application schema and migration head. This is first application setup on
   the preserved copy, not permission to initialize over discovered data.
   Then execute the substantive backup/isolated-restore checks and normal
   deployment. Do not create a dummy table or weaken the archive gate to let an
   empty-cluster automatic deployment pass.

Retain the old immutable image identity, runtime configuration and untouched
volumes. If copied-cluster, TLS, schema or cutover verification fails, keep
writers quiesced and restore the old service binding/configuration using the
retained original cluster. Normal deploy must pass its storage, running-state,
TLS/passfile and substantive backup gates after preparation; these steps do not
add a deployment bypass.

### Provision TLS and database credentials

Use a dedicated staging CA. Keep its private signing key outside the containers
and repository; only the CA certificate and signed server certificate belong
on the host. Generate the server key and certificate with SAN `DNS:postgres`,
server-auth usage and a recorded renewal date. Do not print key/password data,
commit it, or include it in CI artifacts. Provision under the encrypted secrets
mount:

| File | Owner | Mode |
|---|---|---|
| `postgres_ca` | `0:0` | `0444` |
| `postgres_server_crt` | `0:0` | `0444` |
| `postgres_server_key` | `0:70` | `0640` |
| `postgres_password` | `70:70` | `0400` |
| `postgres_pgpass` | actual backend UID/GID | `0600` |

Generate a cryptographically random URL-safe secret of at least 32 characters;
the accepted file shape is 32–128 ASCII letters/digits/underscore/hyphen, with
at most one terminal newline. The libpq passfile is exactly one newline-ended
entry `postgres:5432:<POSTGRES_DB>:<POSTGRES_USER>:<password>`, matching the
selected Compose database and role. Use admitted lowercase SQL identifiers.
The setup validates CA trust, server name, key pair and at least one day of
remaining server-certificate validity. Renew by preparing and verifying a new
pair, then using the normal bounded deploy/reload procedure; never downgrade
client verification to work around expiration.

The staging `.env` supplies `POSTGRES_USER`, `POSTGRES_DB`, application secrets
and the existing explicit `STAGING_DOMAIN`. Remove `POSTGRES_PASSWORD` and
`PGPASSWORD`; staging Compose constructs the passwordless `postgresql+psycopg`
URL with `sslmode=verify-full`, CA and passfile. No redundant host-shell DB
exports are required by deploy. PostgreSQL joins only the internal database
network and rejects every non-TLS network connection. Local socket
administration remains confined to the PostgreSQL container.

### Validate deployment, backups and crash recovery

Connect as `pulseplate-ops` using the trusted dedicated SSH key/host record.
Execute privileged bootstrap/deploy with `sudo`: protected credential and
storage files are intentionally inaccessible to other users. Keep root/password
SSH disabled and do not change production SSH settings.

Run `deploy.sh --preflight-only <backend-digest-ref> <caddy-digest-ref>` after
installing the selected files/mounts. It verifies actual storage/TLS inputs,
rendered Compose and existing volume backing before product mutation. The
normal deployment additionally verifies the original PostgreSQL attestation
tuple and backend/passfile UID. With an existing database, it verifies the new
application passfile against the running predecessor using `verify-full` TLS
before stopping any product writers. A new password file cannot change a
persisted PostgreSQL role password. Incompatible credentials or legacy TLS
setups HOLD for an explicit verified migration that preserves the existing
data; deployment does not rotate credentials or fall back to plaintext.
After admission it waits for the database, migrates and checks an
actual TLS session through the application before exposure. Respect existing
staging enablement and public-release locks; this work does not authorize a
production rollout or public release.

Install `deploy/systemd/pulseplate-staging-postgres-backup.service.example`
as `pulseplate-postgres-backup.service` plus the existing daily timer. The
generic `pulseplate-postgres-backup.service.example` is for self-hosted
production and must not replace the staging unit. Its
`EnvironmentFile`, selected Compose file and encrypted `BACKUP_DIR` must match
deployment. `/srv/pulseplate-staging` and the selected Compose basename
`docker-compose.staging.yaml` are reserved staging identities; either requires
the encrypted-storage checks even when supplied through a relative path.
Production operators use their production project and Compose filenames.
Check `systemctl list-timers`, execute one backup and retain its
exit/metadata receipt. Complete native archive parsing and substantive table
inventory must succeed before publication/pruning. Droplet backups do not
implicitly cover the attached Volume.

For an isolated restore, pass the source identity and selected Compose/env
through the existing helper interface:

```bash
PROJECT_DIR=/srv/pulseplate-staging \
COMPOSE_FILE=docker-compose.staging.yaml \
ENV_FILE=/srv/pulseplate-staging/.env \
POSTGRES_USER=pulseplate POSTGRES_DB=pulseplate \
  /srv/pulseplate-staging/scripts/ops/postgres_restore.sh --verify-into pulseplate_restore_check_01 /mnt/pulseplate-staging-data/backups/selected.dump
```

Use the actual observed source role/database rather than assuming the example.
An existing target fails; verification does not drop the source. Inspect the
restored sentinel/rows before cleaning the owned test database. Ordinary
replacement recovery now requires the explicit `--replace-existing TARGET_DB`
mode; do not invoke it as a verification test.

Replacement is bounded to the `public` schema. Before mutation, the helper
rejects archives and targets with non-public user schemas or unsupported global
objects, including large objects; it does not silently filter archived data.
It pre-renders complete native SQL into private temporary storage (the admitted
encrypted backup directory on staging), then resets `public`, restores the
archive and checks its substantive table inventory in one transaction. SQL or
inventory failure rolls the whole replacement back. Quiesce writers and verify
the authorized target before explicit replacement; unsupported schema layouts
HOLD for a separately verified migration. Verification restore selects the
configured source database as its maintenance connection, so role and database
names may differ.

Native Linux CI uses disposable PostgreSQL storage/PKI and actual TLS, pgvector,
dump/restore and process-crash checks. Its temporary Compose project exercises
the actual backup and restore wrappers, including all three native public-schema
archive shapes, stale-object removal, and a late SQL failure that must roll back
the complete replacement. Wrapper commands use their deployed local socket;
separate TCP queries verify TLS. The selected DHI entrypoint owns the PostgreSQL
executable, so Compose supplies only `-c` arguments. On failure, the driver
retains bounded redacted query and container diagnostics before owned cleanup.
It does not emulate DigitalOcean
at-rest encryption. On the real staging host additionally prove mount identity,
actual application/worker TLS, Prometheus scrape/required series and history
surviving restart, with no public `5432` or `9090`. Record staging observation
start separately from production T0. Never inject faults into production or
interrupt a real storage device to simulate a crash.

## 💰 Budget-Friendly VPS Options

**Last updated: 2026-07-13** - *Maintainers: Update this date when deployment requirements change*

> Current CD artifacts are `linux/amd64` only. Do not select an ARM staging host
> until the CD workflow explicitly restores and validates multi-platform builds.

### Recommended Providers (Cheapest First)

1. **Hetzner Cloud** - €3.29/month (1 vCPU, 2GB RAM)
   - Excellent performance/price ratio
   - German company, GDPR compliant
   - [hetzner.com/cloud](https://www.hetzner.com/cloud)

2. **DigitalOcean** - $6/month (1 vCPU, 1GB RAM)
   - $200 free credits for new users
   - Great documentation
   - [digitalocean.com](https://www.digitalocean.com/)

3. **Vultr** - $2.50/month (1 vCPU, 512MB RAM)
   - Cheapest option
   - Good for testing
   - [vultr.com](https://www.vultr.com/)

4. **Linode** - $5/month (1 vCPU, 1GB RAM)
   - Reliable and fast
   - Good support
   - [linode.com](https://www.linode.com/)

### Free Options (Limited)

1. **Oracle Cloud Always Free** - 0€/month
   - 1/8 OCPU, 1GB RAM (x86)
   - ARM shapes are not compatible with the current staging artifact
   - Requires credit card verification
   - [oracle.com/cloud/free](https://www.oracle.com/cloud/free/)

2. **Google Cloud Free Tier** - $300 credits
   - 1 f1-micro instance
   - 12 months free
   - [cloud.google.com/free](https://cloud.google.com/free)

## 🛠 Server Setup (Ubuntu 22.04)

### 1. Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again, or run:
newgrp docker

# Verify Docker installation
docker --version
docker compose version
```

### 2. Create Staging Directory

```bash
# Create staging directory
sudo mkdir -p /srv/pulseplate-staging
sudo chown $USER:$USER /srv/pulseplate-staging
```

### 3. Copy Deployment Files

```bash
# Copy files from your repository
sudo cp deploy/docker-compose.staging.yaml /srv/pulseplate-staging/
sudo cp deploy/Caddyfile /srv/pulseplate-staging/
sudo cp scripts/deploy.sh /srv/pulseplate-staging/
sudo install -d -m 0755 /srv/pulseplate-staging/scripts/ops /srv/pulseplate-staging/scripts/ci \
  /srv/pulseplate-staging/postgres-pgvector /srv/pulseplate-staging/prometheus \
  /srv/pulseplate-staging/systemd
sudo cp scripts/ops/postgres_backup.sh /srv/pulseplate-staging/scripts/ops/
sudo cp scripts/ops/postgres_restore.sh /srv/pulseplate-staging/scripts/ops/
sudo install -m 0644 scripts/ops/check_staging_security.py /srv/pulseplate-staging/scripts/ops/
sudo install -m 0644 scripts/ci/check_pgvector_attestations.py \
  scripts/ci/check_docker_provenance_attestation.py /srv/pulseplate-staging/scripts/ci/
sudo install -m 0644 deploy/postgres-pgvector/image-manifest.json /srv/pulseplate-staging/postgres-pgvector/
sudo install -m 0444 deploy/postgres-pgvector/pg_hba.conf /srv/pulseplate-staging/postgres-pgvector/
sudo install -m 0644 deploy/prometheus/prometheus.yml deploy/prometheus/image-manifest.json \
  /srv/pulseplate-staging/prometheus/
sudo install -m 0644 deploy/systemd/pulseplate-staging-storage.conf /srv/pulseplate-staging/systemd/
sudo install -m 0644 deploy/systemd/pulseplate-staging-postgres-backup.service.example \
  /srv/pulseplate-staging/systemd/pulseplate-postgres-backup.service.example
sudo install -m 0644 deploy/systemd/pulseplate-postgres-backup.timer.example /srv/pulseplate-staging/systemd/
sudo chown root:root /srv/pulseplate-staging/deploy.sh /srv/pulseplate-staging/docker-compose.staging.yaml \
  /srv/pulseplate-staging/Caddyfile /srv/pulseplate-staging/scripts/ops/*.sh
sudo chmod +x /srv/pulseplate-staging/deploy.sh
sudo chmod +x /srv/pulseplate-staging/scripts/ops/postgres_backup.sh
sudo chmod +x /srv/pulseplate-staging/scripts/ops/postgres_restore.sh

# Create this marker only after copying all files from the same merged commit.
printf '%s' 'pulseplate-staging-attested-digest-v1' | \
  sudo tee /srv/pulseplate-staging/.attested-digest-deploy-v1 >/dev/null
sudo chown root:root /srv/pulseplate-staging/.attested-digest-deploy-v1
sudo chmod 0644 /srv/pulseplate-staging/.attested-digest-deploy-v1
```

The marker is an activation contract, not a substitute for file synchronization.
CD compares SHA-256 for the complete protected bundle, including both
`scripts/ci` attestation helpers, the operations helpers, PostgreSQL HBA/manifest,
Prometheus configuration/manifest and staging systemd files, against the current
workflow commit before sending the GHCR read token. Set the staging
Environment variable `STAGING_ATTESTED_DIGEST_READY=true` only after that
server-local contract has been installed and reviewed. Provisioning is manual
from one verified merged revision; the SSH deployment does not synchronize or
automatically install missing helpers. Once enabled, a marker or
hash mismatch fails the CD job before registry credentials are transmitted, even
when the later SSH deployment remains optional.

### 4. Configure Environment

```bash
# Create environment file
sudo tee /srv/pulseplate-staging/.env > /dev/null << 'EOF'
# Application Configuration
STAGING_DOMAIN=staging.yourdomain.com
POSTGRES_DB=pulseplate
POSTGRES_USER=pulseplate
# Database credentials use the protected files from contract v5 above.
SUBSCRIPTION_DB_ENABLED=true
ALLOW_DEV_API_KEY=false
API_KEY_REQUIRED=true
SECRET_KEY=your-secret-key-here
DEBUG=false

# Add your application-specific variables here
EOF

sudo chown $USER:$USER /srv/pulseplate-staging/.env
sudo chmod 0600 /srv/pulseplate-staging/.env
```

Staging uses the same Postgres-first deploy contract as production: the compose stack includes an internal-only `postgres` service, deploy backups go through `scripts/ops/postgres_backup.sh`, and readiness must be verified via `/ready` or `/health/db`.

### 5. Configure Firewall

```bash
# Install UFW if not present
sudo apt install -y ufw

# Allow SSH, HTTP, and HTTPS
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status
```

### 6. Security Hardening

```bash
# Install fail2ban for SSH protection
sudo apt install -y fail2ban

# Configure fail2ban for SSH
sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

# Enable and start fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Install automatic security updates
sudo apt install -y unattended-upgrades

# Configure automatic updates
sudo dpkg-reconfigure -plow unattended-upgrades

# Basic SSH hardening (use double quotes for variable expansion)
sudo tee -a /etc/ssh/sshd_config > /dev/null << EOF

# Security hardening
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
AllowUsers $USER
EOF

# Test SSH config (IMPORTANT: Keep current session open!)
sudo sshd -t

# If config is valid, restart SSH service
sudo systemctl restart sshd

# Verify fail2ban is working
sudo fail2ban-client status sshd
```

**⚠️ Security Notes:**

- Always test SSH config with `sudo sshd -t` before restarting
- Keep an active SSH session open when making SSH changes
- Use a non-root user with sudo privileges
- Consider changing the default SSH port (22) for additional security
- Monitor fail2ban logs: `sudo tail -f /var/log/fail2ban.log`

## 🔑 SSH Key Setup

### Generate SSH Key Pair

```bash
# On your local machine
ssh-keygen -t ed25519 -C "pulseplate-staging"
# Save as ~/.ssh/pulseplate_staging

# Copy public key to server
ssh-copy-id -i ~/.ssh/pulseplate_staging.pub user@your-server-ip
```

### Test SSH Connection

```bash
ssh -i ~/.ssh/pulseplate_staging user@your-server-ip
```

## 🌐 Domain Setup

### Option 1: Subdomain (Recommended)

1. Add A record: `staging.yourdomain.com` → `your-server-ip`
2. Wait for DNS propagation (5-60 minutes)

### Option 2: Free Subdomain Services

1. **Freenom** - Free domains (.tk, .ml, .ga, .cf)
2. **No-IP** - Free dynamic DNS
3. **DuckDNS** - Free subdomains

## 🔧 GitHub Environment Setup

### 1. Create Environment

1. Go to GitHub → Settings → Environments
2. Click "New environment"
3. Name: `staging`

### 2. Enable staging deploy and add secrets

Set the **Environment variable** (Settings → Environments → staging → Environment variables):

- `WEB_IOS_RELEASE_READY` = `false` (default). Keep this `false` until both web and iOS are release-ready.
- `STAGING_DEPLOY_ENABLED` = `true` — enables SSH deploy logic, but deploy still runs only when all three rollout gates are true.
- `STAGING_ATTESTED_DIGEST_READY` = `false` (default). Set this to `true` only after the server-local two-digest deploy contract, marker, Compose file, Caddyfile, and deploy script have been synchronized and verified.
- `STAGING_DEPLOY_REQUIRED` = `true|false` (optional, default `false`) — controls whether a failed staging SSH deploy should fail the whole CD workflow. Keep `false` for non-blocking staging; set `true` when staging deploy must be strict/blocking.

**Build-only policy (canonical):**
- Unless `WEB_IOS_RELEASE_READY=true`, `STAGING_DEPLOY_ENABLED=true`, and `STAGING_ATTESTED_DIGEST_READY=true`, CD remains in build/validation mode (image build+push only, no staging SSH deploy).
- When all three rollout gates are true, deploy runs only when every required staging secret is present.
- If `STAGING_DEPLOY_REQUIRED=true`, a missing rollout gate or required secret fails the workflow instead of silently skipping deployment.

Add these **secrets** to the `staging` environment:

- `SSH_HOST_STAGING` - Your server IP or domain
- `SSH_USER` - `pulseplate-ops` for the current staging Droplet; use its
  dedicated key and privileged `sudo` execution, with root/password SSH disabled
- `SSH_KEY` - Full private SSH key (PEM format), including `-----BEGIN ... KEY-----` and `-----END ... KEY-----`; preserve newlines when pasting to avoid "ssh: no key found"
- `SSH_HOST_STAGING_FINGERPRINT` - Required staging **server** host key fingerprint, usually `SHA256:...`. **Easiest from your laptop:** run `ssh -o VisualHostKey=yes user@your-staging-host` and copy the `SHA256:...` line shown when connecting. **Or on the server:** after SSH in, run `sudo ssh-keygen -l -f /etc/ssh/ssh_host_ed25519_key.pub` (or `ssh_host_rsa_key.pub` / `ssh_host_ecdsa_key.pub` if present; list with `ls /etc/ssh/ssh_host_*.pub`).
- `GHCR_READ_TOKEN` - GitHub PAT with `read:packages` permission
- `STAGING_DOMAIN` - Your staging domain

#### Host key fingerprint mismatch (CI error)

If CD fails with `ssh: handshake failed: ssh: host key fingerprint mismatch`, rotate `SSH_HOST_STAGING_FINGERPRINT` to the current host key:

```bash
# From your laptop (preferred): get current ed25519 host key fingerprint
ssh-keyscan -t ed25519 your-staging-host 2>/dev/null \
  | ssh-keygen -lf - -E sha256 \
  | awk '{print $2}'
```

Expected output format: `SHA256:...`

After updating the GitHub environment secret, re-run the failed CD workflow.

#### Staging TLS in build-only mode

When `WEB_IOS_RELEASE_READY` is not `true`, SSH deploy to `/srv/pulseplate-staging` is skipped by design.
Evidence: `.github/workflows/cd.yml:83`, `.github/workflows/cd.yml:98`

To avoid `ERR_SSL_PROTOCOL_ERROR` on the public staging URL in this mode, production Caddy keeps a
fallback vhost (`{$STAGING_FALLBACK_DOMAIN:pulseplate-staging.duckdns.org}`) and serves it from the
running app container.
Evidence: `deploy/Caddyfile.production:25`, `deploy/docker-compose.production.yaml:46`

- This fallback is transport-level only (TLS + reverse proxy) and does not replace a real staging deploy.
- Once full staging deploy is enabled (`WEB_IOS_RELEASE_READY=true`,
  `STAGING_DEPLOY_ENABLED=true`, `STAGING_ATTESTED_DIGEST_READY=true` + staging secrets), verify
  `/srv/pulseplate-staging` compose stack is active and remove fallback dependency from ops checks.
- Temporary seam tracking:
  - ADR: `docs/architecture/ADR_STAGING_TLS_FALLBACK_SEAM_2026-03-04.md`
  - Backlog: `docs/roadmap/BACKLOG_LEDGER.md` (`P1: Remove staging TLS fallback seam after full staging readiness`)

### 3. Create GitHub PAT

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes: `read:packages`
4. Copy the token and add it as `GHCR_READ_TOKEN`

## 🧪 Test Deployment

### Manual Test

```bash
# On your server
cd /srv/pulseplate-staging
read -rsp "GHCR read token: " GHCR_TOKEN
printf '\n'
STAGING_DOMAIN=staging.yourdomain.com \
GHCR_USER=<read-only-ghcr-user> \
GHCR_TOKEN="$GHCR_TOKEN" \
./deploy.sh \
  ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:<verified-backend-digest> \
  ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:<verified-caddy-digest>
unset GHCR_TOKEN
```

Use digests from the same successful CD attestation run. Tags, commit SHAs,
`staging-latest`, and `latest` are rejected. Image rollback reuses previously
verified exact digests; it does not reverse Alembic migrations. Restoring a
pre-migration database backup is a separate human-approved operation.

### Automatic Test

Once all three rollout gates are enabled, successful pushes to `main` can
deploy automatically. The repository does not enforce a per-run human approval
for staging; configure required reviewers on the GitHub `staging` environment
if that operational control is desired.

1. Push a commit to `main` branch
2. Check GitHub Actions → CD workflow
3. Visit your staging domain
4. Verify `/ready` endpoint returns 200

## 🔍 Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   - Check firewall settings
   - Verify SSH key permissions
   - Test SSH connection manually

2. **Docker Permission Denied**
   - Add user to docker group: `sudo usermod -aG docker $USER`
   - Logout and login again

3. **Domain Not Resolving**
   - Check DNS propagation: `nslookup staging.yourdomain.com`
   - Wait up to 24 hours for full propagation

4. **SSL Certificate Issues**
   - Caddy automatically handles Let's Encrypt
   - Check Caddy logs: `docker logs caddy`

### Useful Commands

```bash
# Check Docker containers
docker ps

# View application logs
docker logs app

# View Caddy logs
docker logs caddy

# Check disk space
df -h

# Check memory usage
free -h
```

## 💡 Cost Optimization Tips

1. **Use right-sized x86_64 instances** - Current staging artifacts are amd64-only
2. **Enable auto-shutdown** - Stop server when not in use
3. **Monitor usage** - Set up billing alerts
4. **Use spot instances** - Up to 90% cheaper (with risk of termination)

## 📊 Monitoring

### Basic Health Checks

```bash
# Check if application is running
curl -f https://staging.yourdomain.com/ready

# Optional DB-specific readiness check
curl -f https://staging.yourdomain.com/health/db

# Check response time
curl -w "@curl-format.txt" -o /dev/null -s https://staging.yourdomain.com/ready
```

### Log Monitoring

```bash
# Follow application logs
docker logs -f app

# Follow Caddy logs
docker logs -f caddy
```

---

**Total Monthly Cost**: €3-6 for a basic staging environment
**Setup Time**: 30-60 minutes
**Maintenance**: Operator-managed; app/Caddy artifact deployment can be
automated after all rollout gates are enabled. Host maintenance, backups,
volumes, DNS/TLS, and server-local contract synchronization remain manual.
