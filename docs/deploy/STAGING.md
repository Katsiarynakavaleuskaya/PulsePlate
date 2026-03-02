# 🚀 Staging Server Setup Guide

## 💰 Budget-Friendly VPS Options

**Last updated: 2025-01-27** - *Maintainers: Update this date when pricing or provider information changes*

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
   - 1/8 OCPU, 1GB RAM (ARM)
   - 1/8 OCPU, 1GB RAM (x86)
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
sudo chmod +x /srv/pulseplate-staging/deploy.sh
```

### 4. Configure Environment

```bash
# Create environment file
sudo tee /srv/pulseplate-staging/.env > /dev/null << 'EOF'
# Application Configuration
STAGING_DOMAIN=staging.yourdomain.com
DATABASE_URL=sqlite:///app/cache/app.db
SECRET_KEY=your-secret-key-here
DEBUG=false

# Add your application-specific variables here
EOF

sudo chown $USER:$USER /srv/pulseplate-staging/.env
```

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

- `STAGING_DEPLOY_ENABLED` = `true` — required for CD to run SSH deploy. If unset, the CD workflow only builds and pushes the image (no deploy); this avoids "ssh: no key found" when secrets are not yet configured.

Add these **secrets** to the `staging` environment:

- `SSH_HOST_STAGING` - Your server IP or domain
- `SSH_USER` - SSH username (usually `root` or `ubuntu`)
- `SSH_KEY` - Full private SSH key (PEM format), including `-----BEGIN ... KEY-----` and `-----END ... KEY-----`; preserve newlines when pasting to avoid "ssh: no key found"
- `SSH_HOST_STAGING_FINGERPRINT` - Staging **server** host key fingerprint, usually `SHA256:...` (optional but recommended). **Easiest from your laptop:** run `ssh -o VisualHostKey=yes user@your-staging-host` and copy the `SHA256:...` line shown when connecting. **Or on the server:** after SSH in, run `sudo ssh-keygen -l -f /etc/ssh/ssh_host_ed25519_key.pub` (or `ssh_host_rsa_key.pub` / `ssh_host_ecdsa_key.pub` if present; list with `ls /etc/ssh/ssh_host_*.pub`).
- `GHCR_READ_TOKEN` - GitHub PAT with `read:packages` permission
- `STAGING_DOMAIN` - Your staging domain

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
./deploy.sh latest
```

### Automatic Test

1. Push a commit to `main` branch
2. Check GitHub Actions → CD workflow
3. Visit your staging domain
4. Verify `/health` endpoint returns 200

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

1. **Use ARM instances** - Often 20-30% cheaper
2. **Enable auto-shutdown** - Stop server when not in use
3. **Monitor usage** - Set up billing alerts
4. **Use spot instances** - Up to 90% cheaper (with risk of termination)

## 📊 Monitoring

### Basic Health Checks

```bash
# Check if application is running
curl -f https://staging.yourdomain.com/health

# Check response time
curl -w "@curl-format.txt" -o /dev/null -s https://staging.yourdomain.com/health
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
**Maintenance**: Minimal (automatic updates via GitHub Actions)
