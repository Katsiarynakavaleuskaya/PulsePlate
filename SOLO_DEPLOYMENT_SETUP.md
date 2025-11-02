# 🚀 Solo Deployment Setup - PulsePlate

**Для соло-разработки:** Упрощённая, но безопасная конфигурация.

## 📋 Быстрая настройка

### 1. GitHub Environments (минимально необходимое)

**Создайте environments:**
- `staging` (для main branch)
- `production` (для tags v*)

**Secrets для `staging`:**
```
STAGING_DOMAIN=pulseplate-staging.duckdns.org
SSH_HOST_STAGING=ваш_ip_или_домен
SSH_USER=ubuntu
SSH_KEY=приватный_ssh_ключ
GHCR_READ_TOKEN=github_pat_token
```

**Secrets для `production`:**
```
PRODUCTION_DOMAIN=pulseplate.app
SSH_HOST_PRODUCTION=ваш_ip_или_домен
SSH_USER=ubuntu
SSH_KEY=тот_же_ssh_ключ (или отдельный)
GHCR_READ_TOKEN=тот_же_токен
```

### 2. Генерация SSH ключа (один раз)

```bash
ssh-keygen -t ed25519 -C "pulseplate-deploy" -f ~/.ssh/pulseplate_deploy
# Скопируйте публичный ключ на сервер:
cat ~/.ssh/pulseplate_deploy.pub | ssh user@your-server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Добавьте приватный ключ в GitHub Secrets:
cat ~/.ssh/pulseplate_deploy
```

### 3. GitHub PAT Token

1. https://github.com/settings/tokens → Generate new token (classic)
2. Отметьте только: `read:packages`
3. Скопируйте токен → добавьте как `GHCR_READ_TOKEN` в оба environment

## 🔒 Минимальная безопасность (для соло)

### Обязательно:

1. **SSH:** `PasswordAuthentication no` на сервере
2. **Cloudflare:** SSL Full (strict) + HSTS включён
3. **GitHub:** Branch protection на `main` (можно без reviewers, но с require status checks)
4. **Secrets:** Используйте GitHub Environments, не коммитьте в код

### Опционально (но рекомендуется):

- Cloudflare WAF (базовые правила)
- Rate limiting на admin endpoints
- Healthcheck после деплоя (автооткат при падении)

## ⚡ Упрощённый workflow

**Staging:** Автоматический деплой при push в `main`
**Production:** Автоматический деплой при создании tag `v*` (можно добавить manual approval, если нужно)

## 🎯 Быстрый старт

1. Регистрация доменов (см. `DOMAIN_SETUP.md`)
2. Добавьте секреты в GitHub (см. выше)
3. Push в main → staging деплой
4. Tag v1.0.0 → production деплой

**Готово!** 🎉
