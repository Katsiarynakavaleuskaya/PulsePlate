# 🚀 Production Server Setup Guide

## Overview

This guide covers setting up a production server for PulsePlate with automated deployments via GitHub Actions.

## Optional Cloudflare Worker Edge Proxy

The Cloudflare Worker runtime is supported only as a bounded first-party proxy in front of the API.

- Scope: proxy only `/api/*` paths.
- Methods: allow only `GET`, `POST`, and `OPTIONS`.
- Required config:
  - `TARGET_BASE`: explicit API origin; placeholder values are forbidden.
  - `WORKER_ALLOWED_ORIGINS`: comma-separated trusted browser origins allowed to receive reflected CORS headers.
- CORS policy:
  - wildcard `Access-Control-Allow-Origin: *` is forbidden
  - trusted origins are reflected exactly with `Vary: Origin`
  - browser preflight fails closed when origin/path is not allowed
- Header policy:
  - bounded forwarding only (`Accept`, `Content-Type`, `Authorization`, `X-API-Key`, `Cookie`)
  - hop/proxy headers and arbitrary pass-through are forbidden
- Redirect policy:
  - upstream fetches must remain `redirect: "manual"` to avoid broad proxy behavior

If you do not need this bounded edge proxy, do not deploy `worker.js` at all.

## Prerequisites

- Production server (VPS/Cloud instance)
- Domain name configured
- GitHub repository with Actions enabled
- SSH key pair for server access

## 🛠 Server Setup

### 1. Initial Server Configuration

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

### 1.5 Security Hardening (Обязательно!)

**RU: Базовый hardening для production сервера.
EN: Basic security hardening for production server.**

```bash
# Install security tools
sudo apt install -y ufw fail2ban unattended-upgrades

# UFW Firewall configuration
# Verify SSH port first (default is 22 if not set in /etc/ssh/sshd_config)
SSH_PORT=$(grep -E "^Port " /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' || echo "22")
echo "SSH port detected: $SSH_PORT"
sudo ufw allow ${SSH_PORT}/tcp   # Allow SSH on detected port
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable

# Verify firewall status
sudo ufw status

# fail2ban configuration (protection against SSH brute force)
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

sudo systemctl enable --now fail2ban

# Verify fail2ban is working
sudo fail2ban-client status sshd

# SSH daemon hardening
sudo tee -a /etc/ssh/sshd_config > /dev/null << 'EOF'

# Security hardening (production)
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
EOF

# Test SSH config before restarting (IMPORTANT!)
sudo sshd -t

# ⚠️ SAFETY CHECK: Prevent SSH lockout before restarting sshd
# - Keep this SSH session open until you verify a new connection works
# - Open a NEW terminal/SSH session from your local machine
# - Attempt to connect with your SSH key: ssh user@server
# - Only if the NEW session connects successfully, proceed with restart below
# - If new session fails, do NOT restart sshd (fix config first or restore from backup)
# - Having this session open allows you to revert changes if needed

# If config is valid AND new SSH session works, restart SSH
sudo systemctl restart sshd

# Enable automatic security updates
sudo dpkg-reconfigure -plow unattended-upgrades
```

**⚠️ ВАЖНО:** После настройки SSH вы сможете подключаться только по SSH ключу. Убедитесь, что ваш публичный ключ уже добавлен в `~/.ssh/authorized_keys` на сервере перед выполнением этих команд!

**⚠️ IMPORTANT:** After SSH hardening, you can only connect using SSH keys. Ensure your public key is already added to `~/.ssh/authorized_keys` on the server before running these commands!

### 2. Create Production Directory

```bash
# Create production directory
sudo mkdir -p /srv/pulseplate-production
sudo chown $USER:$USER /srv/pulseplate-production
```

### 3. Copy Deployment Files

```bash
# Copy deployment templates
sudo cp deploy/Caddyfile /srv/pulseplate-production/
sudo cp scripts/deploy.sh /srv/pulseplate-production/
sudo chmod +x /srv/pulseplate-production/deploy.sh
```

### 4. Configure Production Environment

```bash
# Create environment file
sudo tee /srv/pulseplate-production/.env > /dev/null << 'EOF'
# Production Configuration
PRODUCTION_DOMAIN=yourdomain.com
DATABASE_URL=sqlite:///app/cache/app.db
SECRET_KEY=your-production-secret-key-here
DEBUG=false

# Add your production-specific variables here
EOF

sudo chown $USER:$USER /srv/pulseplate-production/.env
```

### 5. Update Docker Compose for Production

```bash
# Update docker-compose.production.yaml
sudo tee /srv/pulseplate-production/docker-compose.production.yaml > /dev/null << 'EOF'
version: "3.9"

networks:
  web:
    external: false

services:
  app:
    image: ghcr.io/katsiarynakavaleuskaya/pulseplate:${TAG:-latest}
    env_file:
      - /srv/pulseplate-production/.env
    restart: always
    networks: [web]
    expose:
      - "8000"
    # RU: Bind mount БД на хост для персистентности и бэкапов
    # EN: Bind mount DB to host for persistence and backups
    volumes:
      - /srv/pulseplate-production/app_data:/app/cache
    command: >
      uvicorn app:app --host 0.0.0.0 --port 8000
      --proxy-headers --forwarded-allow-ips="caddy"
    # RU: Resource limits (deploy: блок удалён из примера, т.к. работает только в Swarm)
    # EN: Resource limits (deploy: block removed from example as it only works in Swarm)
    # Limits can be set via docker-compose CLI flags if needed
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  caddy:
    image: caddy:2
    restart: always
    networks: [web]
    ports:
      - "80:80"
      - "443:443"
    environment:
      - PRODUCTION_DOMAIN=${PRODUCTION_DOMAIN}
    volumes:
      - /srv/pulseplate-production/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - app

volumes:
  caddy_data:
  caddy_config:
  # RU: app_data volume не используется, т.к. БД монтируется через bind mount
  # EN: app_data volume not used, as DB is mounted via bind mount
EOF
```

### 6. Update Caddyfile for Production

```bash
# Update Caddyfile with security headers
sudo tee /srv/pulseplate-production/Caddyfile > /dev/null << 'EOF'
{$PRODUCTION_DOMAIN} {
    encode gzip
    reverse_proxy app:8000

    # RU: Безопасные заголовки по умолчанию (дополняет Cloudflare)
    # EN: Basic security headers (complements Cloudflare)
    header {
        # HSTS уже настроен в Cloudflare, но дублируем на origin
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        # Минимальная CSP: разрешаем всё с того же источника
        Content-Security-Policy "default-src 'self'; frame-ancestors 'none'; object-src 'none'"
    }
}
EOF
```

### 7. Update Deploy Script for Production

```bash
# Update deploy.sh for production
sudo tee /srv/pulseplate-production/deploy.sh > /dev/null << 'EOF'
#!/usr/bin/env bash
# Production deployment script
set -euo pipefail

# Validate required environment variables
PRODUCTION_DOMAIN=${PRODUCTION_DOMAIN:?"PRODUCTION_DOMAIN not set"}
GHCR_TOKEN=${GHCR_TOKEN:?"GHCR_TOKEN not set"}
GHCR_USER=${GHCR_USER:?"GHCR_USER not set"}

IMG_REF="${1:-latest}"
COMPOSE="docker compose -f /srv/pulseplate-production/docker-compose.production.yaml"

# Warn if using latest tag
if [ "$IMG_REF" = "latest" ]; then
  echo "⚠️  WARNING: Using 'latest' tag. For production deployments, use specific commit SHA tags."
fi

echo "[1/4] Login GHCR"
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin

echo "[2/4] Pull image $IMG_REF"
export TAG="$IMG_REF"
$COMPOSE pull app

echo "[3/4] Start stack and DB backup"
$COMPOSE up -d app caddy

# Wait for app container to be ready
echo "Waiting for app container to be ready..."
max_wait=60
wait_count=0
while [ $wait_count -lt $max_wait ]; do
  if $COMPOSE ps app | grep -q "Up"; then
    echo "App container is running"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for app container... ($wait_count/$max_wait)"
  sleep 1
done

if [ $wait_count -eq $max_wait ]; then
  echo "❌ App container failed to start within $max_wait seconds"
  exit 1
fi

# Get the actual container name dynamically
APP_CONTAINER=$($COMPOSE ps -q app | tr -d '\n\r ')
if [ -z "$APP_CONTAINER" ]; then
  echo "❌ Failed to find app container"
  exit 1
fi
echo "Using app container: $APP_CONTAINER"

# Create database backup if it exists
if docker exec "$APP_CONTAINER" test -f /app/cache/app.db 2>/dev/null; then
  timestamp=$(date +"%Y%m%d_%H%M%S")
  backup_dir="/srv/pulseplate-production/backups"
  mkdir -p "$backup_dir"
  backup_path="$backup_dir/app.db.backup-$timestamp"
  echo "Creating database backup: $backup_path"
  docker cp "$APP_CONTAINER:/app/cache/app.db" "$backup_path"

  # RU: Храним 30 последних бэкапов для production
  # EN: Keep last 30 backups for production
  ls -t "$backup_dir"/app.db.backup-* 2>/dev/null | tail -n +31 | xargs -r rm -f
  # See section 7.2 for detailed disk usage and compression guidance
  echo "Database backup completed"
else
  echo "No existing database found, skipping backup"
fi

echo "[4/4] Run migrations"
# Wait for app to be ready
echo "Waiting for app to be ready for migrations..."
max_wait=30
wait_count=0
while [ $wait_count -lt $max_wait ]; do
  if docker exec "$APP_CONTAINER" python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" 2>/dev/null; then
    echo "App is ready for migrations"
    break
  fi
  wait_count=$((wait_count + 1))
  echo "Waiting for app readiness... ($wait_count/$max_wait)"
  sleep 1
done

if [ $wait_count -eq $max_wait ]; then
  echo "❌ App failed to become ready within $max_wait seconds"
  exit 1
fi

# Run migrations
echo "Running database migrations in container: $APP_CONTAINER"
if docker exec "$APP_CONTAINER" alembic upgrade head; then
  echo "✅ Database migrations completed successfully in container: $APP_CONTAINER"
else
  migration_exit_code=$?
  echo "❌ Database migrations failed in container: $APP_CONTAINER (exit code: $migration_exit_code)" >&2
  echo "Check container logs with: docker logs $APP_CONTAINER" >&2
  exit $migration_exit_code
fi

echo "[post] Production health check"
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
  attempt=$((attempt + 1))
  echo "Health check attempt $attempt/$max_attempts..."

  curl_output=$(curl -fsS "https://${PRODUCTION_DOMAIN}/health" 2>&1)
  curl_exit_code=$?

  if [ $curl_exit_code -eq 0 ]; then
    echo "✅ Production health check successful"
    break
  else
    echo "❌ Health check failed (exit code: $curl_exit_code)" >&2
    echo "Error details: $curl_output" >&2

    if [ $attempt -eq $max_attempts ]; then
      echo "❌ Production health check failed after ${max_attempts} attempts" >&2
      echo "Final error: $curl_output" >&2
      exit 1
    fi

    echo "Waiting 2 seconds before retry..."
    sleep 2
  fi
done

echo "✅ Production deployed: $IMG_REF"
EOF

sudo chmod +x /srv/pulseplate-production/deploy.sh
```

### 7.1. Set Up Disk Space Monitoring and Alerts

To prevent disk space issues from backups and logs, set up automated alerts when free space drops below a threshold.

**Recommended Threshold**: Alert when free disk space falls below **20%** of total capacity.

**Monitoring Options**:

1. **Prometheus + node_exporter + Alertmanager** (recommended for self-hosted):

   ```bash
   # Install node_exporter on the server
   # Configure Prometheus to scrape disk metrics
   # Set up alert rule in Alertmanager:
   # - alert: LowDiskSpace
   #   expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 < 20
   ```

2. **Cloud Provider Monitoring** (DigitalOcean, AWS, etc.):
   - Enable disk space monitoring in your cloud provider's dashboard
   - Configure alerts via their native alerting system
   - Set threshold to 20% free space

3. **Simple Cron-based Script** (quick setup):

   ```bash
   # Create monitoring script
   sudo tee /usr/local/bin/check-disk-space.sh > /dev/null << 'EOF'
   #!/usr/bin/env bash
   set -euo pipefail
   THRESHOLD=20  # Alert when free space < 20%
   MOUNTPOINT="/"

   # Extract used percentage and validate it's numeric
   USED_PERCENT=$(df "$MOUNTPOINT" | awk 'NR==2 {print $5}' | sed 's/%//')

   # Validate USED_PERCENT is non-empty and numeric
   if [ -z "$USED_PERCENT" ] || ! [[ "$USED_PERCENT" =~ ^[0-9]+$ ]]; then
       echo "ERROR: Failed to extract valid disk usage percentage. Got: '$USED_PERCENT'" >&2
       exit 1
   fi

   FREE_PERCENT=$((100 - USED_PERCENT))

   if [ "$USED_PERCENT" -gt $((100 - THRESHOLD)) ]; then
       echo "ALERT: Disk space on $MOUNTPOINT is ${USED_PERCENT}% used (threshold: $((100 - THRESHOLD))%)"
       # Send notification (see notification channels below)
   fi
   EOF

   sudo chmod +x /usr/local/bin/check-disk-space.sh

   # Add to crontab (check every 5 minutes)
   (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/check-disk-space.sh") | crontab -
   ```

**Check Frequency**:

- **Every 5-15 minutes** for production environments
- Use retention-aware alerting to suppress flapping (require alert to persist for 2-3 consecutive checks before firing)

**Notification Channels**:

- **Email**: Send alerts to operations team email
- **Slack**: Configure webhook for Slack channel notifications
- **PagerDuty**: For critical production environments requiring on-call escalation

**Example Alert Suppression** (for cron script):

```bash
# Add state tracking to prevent alert flapping
STATE_FILE="/var/run/disk-alert-state"
CONSECUTIVE_THRESHOLD=3  # Require 3 consecutive checks

if [ "$USED_PERCENT" -gt $((100 - THRESHOLD)) ]; then
    if [ -f "$STATE_FILE" ]; then
        COUNT=$(cat "$STATE_FILE")
        COUNT=$((COUNT + 1))
    else
        COUNT=1
    fi
    echo "$COUNT" > "$STATE_FILE"

    if [ "$COUNT" -ge "$CONSECUTIVE_THRESHOLD" ]; then
        # Fire alert and reset counter
        echo "ALERT: Disk space critical..."
        # Send notification
        echo "0" > "$STATE_FILE"
    fi
else
    # Reset counter when disk space is healthy
    echo "0" > "$STATE_FILE"
fi
```

### 7.2. Backup Retention: Disk Usage and Compression Guidance

This section provides detailed guidance on managing disk space for database backups and optional compression strategies.

#### Disk Usage Estimation

**RU: Примечание о использовании диска**
**EN: Disk usage note**

To estimate the size of a single backup, use:

```bash
du -sh "$backup_dir"/app.db.backup-* | head -1
```

**Example Calculation**:

- If one backup ≈ 500MB, then 30 backups ≈ 15GB
- Monitor disk usage regularly: `df -h`
- Verify available disk space before enabling retention
- Set up monitoring/alerts or automated pruning when free space falls below a threshold (e.g., <20% free)

#### Backup Compression (Optional)

**RU: Опционально: сжатие бэкапов для экономии места**
**EN: Optional: backup compression to reduce disk usage**

To reduce disk usage, consider compressing backups. Common approaches:

1. **gzip compression**:

   ```bash
   gzip "$backup_path"
   # Creates: app.db.backup-YYYYMMDD_HHMMSS.gz
   ```

2. **SQLite dump with compression**:

   ```bash
   sqlite3 app.db .dump | gzip > "$backup_dir/backup-$timestamp.sql.gz"
   ```

**Compression Ratios**:

- Typical SQLite compression: **2-5x** for common databases
- Example: if uncompressed backup ≈ 500MB, after compression ≈ 100-250MB
- 30 compressed backups ≈ 3-7.5GB (vs 15GB uncompressed)

**Important Considerations**:

- **Always test restores** after implementing compression:

  ```bash
  # Test decompression and restore
  gunzip backup.sql.gz
  sqlite3 restored.db < backup.sql
  ```

- Monitor compressed backup sizes when setting retention thresholds
- Sizes may vary depending on data content and compression algorithm
- Update retention policies to account for compressed file sizes

**Modified Backup Script with Compression** (example):

```bash
# Create compressed backup
timestamp=$(date +"%Y%m%d_%H%M%S")
backup_dir="/srv/pulseplate-production/backups"
mkdir -p "$backup_dir"
backup_path="$backup_dir/app.db.backup-$timestamp"
docker cp "$APP_CONTAINER:/app/cache/app.db" "$backup_path"
gzip "$backup_path"  # Compress immediately after creation

# Retention: keep last 30 compressed backups
ls -t "$backup_dir"/app.db.backup-*.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
```

## 🔑 GitHub Environment Setup

### 1. Create Production Environment

1. Go to GitHub → Settings → Environments
2. Click "New environment" and name it `production`
3. Add required secrets:
   - `SSH_HOST_PRODUCTION`: IP address or hostname of your production server
   - `SSH_USER`: SSH username (e.g., `ubuntu`)
   - `SSH_KEY`: Private SSH key (content of `~/.ssh/pulseplate_production`)
   - `GHCR_READ_TOKEN`: GitHub Personal Access Token (PAT) with `read:packages` scope
   - `PRODUCTION_DOMAIN`: Your production domain (e.g., `yourdomain.com`)

**⚠️ Important**: All secrets must be configured before the first deployment attempt. Missing secrets will cause the workflow to fail with "missing server host" error.

**📝 Note**: The deployment scripts use `set -euo pipefail` for strict error handling instead of the deprecated `script_stop` parameter. This ensures the workflow fails immediately if any command in the deployment script fails.

### 2. Configure Protection Rules

1. In the `production` environment settings:
2. Add protection rules:
   - **Required reviewers**: Add team members who can approve production deployments
   - **Wait timer**: Optional delay before deployment (e.g., 5 minutes)
   - **Deployment branches**: Restrict to specific branches (e.g., `main` only)

## 🚀 Deployment Process

### Automatic Deployment

Production deployments are triggered by:

1. **Tag pushes**: `git tag v1.0.0 && git push origin v1.0.0`
2. **Manual approval**: Required reviewers must approve the deployment
3. **Health checks**: Automatic verification after deployment

### Manual Deployment

```bash
# On your local machine
git tag v1.0.0
git push origin v1.0.0

# The GitHub Action will:
# 1. Build and push Docker image
# 2. Wait for approval
# 3. Deploy to production
# 4. Run health checks
```

## 🔒 Security Considerations

### Production Security

1. **Firewall**: Only allow SSH (22), HTTP (80), HTTPS (443)
2. **SSL/TLS**: Automatic via Caddy
3. **Database backups**: Automatic before each deployment
4. **Secrets management**: All secrets stored in GitHub
5. **Access control**: SSH key-based authentication only

### Monitoring

1. **Health checks**: Automatic monitoring of `/health` endpoint
2. **Logs**: Available via `docker logs` commands
3. **Backups**: Automatic database backups before deployments
4. **Rollback**: Previous image tags available for quick rollback

### Disk Space Monitoring and Alerts

**RU:** Для предотвращения проблем с нехваткой места на диске рекомендуется настроить мониторинг и автоматическую очистку.

**EN:** To prevent disk space issues, it's recommended to set up monitoring and automated cleanup.

#### Existing Cleanup Scripts

The project includes cleanup scripts that can be scheduled via cron:

- **Cache cleanup:** `scripts/clean-cache.sh` - Removes Python cache files and temporary data
- **Food DB update:** `scripts/schedule_food_db_update.py` - Automated database updates (see [CRON.md](../runbooks/CRON.md))

#### Setting Up Disk Space Alerts

**RU:** Пример настройки cron-задачи для проверки дискового пространства и автоматической очистки при падении свободного места ниже 20%:

**EN:** Example cron setup for disk space checking and automatic cleanup when free space falls below 20%:

```bash
# Create dedicated cleanup script
sudo tee /usr/local/bin/pulseplate-backup-cleanup.sh > /dev/null << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/srv/pulseplate-production/backups"
THRESHOLD=80

# Compute disk usage percentage
USED=$(df "$BACKUP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')

# Validate USED is non-empty and numeric (0-100)
if [ -z "$USED" ] || ! [[ "$USED" =~ ^[0-9]+$ ]] || [ "$USED" -lt 0 ] || [ "$USED" -gt 100 ]; then
    echo "ERROR: Failed to extract valid disk usage percentage. Got: '$USED'" >&2
    echo "Skipping backup cleanup to avoid acting on invalid value." >&2
    exit 1
fi

# Check if usage exceeds threshold
if [ "$USED" -gt "$THRESHOLD" ]; then
    # Remove older backups while retaining the last 30
    ls -t "$BACKUP_DIR"/app.db.backup-* 2>/dev/null | tail -n +31 | xargs -r rm -f
    echo "$(date): Cleaned up old backups (disk usage was ${USED}%)"
fi
EOF

sudo chmod +x /usr/local/bin/pulseplate-backup-cleanup.sh

# Add to crontab: crontab -e
# Check disk space every hour and clean backups if >80% used (i.e., <20% free)
0 * * * * /usr/local/bin/pulseplate-backup-cleanup.sh >> /var/log/pulseplate-disk-cleanup.log 2>&1

# Run cache cleanup weekly (Sunday at 3 AM)
0 3 * * 0 /path/to/PulsePlate/scripts/clean-cache.sh >> /var/log/pulseplate-cache-cleanup.log 2>&1
```

#### Alternative: External Monitoring Solutions

**RU:** Для более продвинутого мониторинга можно использовать:

- **Prometheus + Alertmanager** - для метрик и алертов
- **Grafana** - для визуализации использования диска
- **Cloud provider monitoring** - встроенные алерты DigitalOcean/AWS/etc. при <20% свободного места

**EN:** For advanced monitoring, consider:

- **Prometheus + Alertmanager** - for metrics and alerts
- **Grafana** - for disk usage visualization
- **Cloud provider monitoring** - built-in alerts from DigitalOcean/AWS/etc. when free space <20%

#### Quick Disk Space Check

```bash
# Check backup directory size
du -sh /srv/pulseplate-production/backups

# Check overall disk usage
df -h

# Estimate backup retention impact
du -sh /srv/pulseplate-production/backups/app.db.backup-* | head -1
```

**RU:** Рекомендуется регулярно проверять использование диска и корректировать retention-политики в зависимости от размера бэкапов и доступного места.

**EN:** Regularly check disk usage and adjust retention policies based on backup sizes and available space.

## 🧪 Testing Production Setup

### 1. Local Test

```bash
# Test the production configuration locally
docker compose -f deploy/docker-compose.staging.yaml up -d
curl -f http://localhost:8000/health
docker compose -f deploy/docker-compose.staging.yaml down
```

### 2. Production Test

```bash
# On your production server
cd /srv/pulseplate-production
./deploy.sh latest

# Check health
curl -f https://yourdomain.com/health
```

## 📋 Production Checklist

- [ ] Server configured with Docker
- [ ] Domain DNS pointing to server
- [ ] SSL certificate working (automatic via Caddy)
- [ ] GitHub environment configured
- [ ] Protection rules enabled
- [ ] SSH keys configured
- [ ] Health checks passing
- [ ] Database backups working
- [ ] Monitoring in place

## 🆘 Troubleshooting

### Common Issues

1. **Deployment fails**: Check GitHub Actions logs
2. **Health check fails**: Check app logs with `docker logs <container>`
3. **SSL issues**: Verify domain DNS and Caddy configuration
4. **Database issues**: Check migration logs and backup status

### Emergency Rollback

```bash
# On production server
cd /srv/pulseplate-production
export TAG=previous-tag
./deploy.sh $TAG
```

## 📞 Support

For production issues:

1. Check GitHub Actions logs
2. Review server logs
3. Verify environment configuration
4. Test health endpoints
5. Check database backup status
