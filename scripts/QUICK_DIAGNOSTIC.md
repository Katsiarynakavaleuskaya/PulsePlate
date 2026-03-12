# Quick Diagnostic for Cloudflare 521 Error

## Вариант 0: публичная проверка из локального repo

Сначала подтвердите, что проблема действительно находится в публичной DNS/TLS топологии:

```bash
python3 scripts/check_domain_tls.py --domain pulseplate.app
```

Ожидаемое healthy-состояние:
- apex отвечает приложением и отдаёт один из ожидаемых статусов (`200/301/302/303/307/308/405`)
- `www` отдаёт `301/302/307/308` на `https://pulseplate.app`

Если script показывает `www ... 525`, переходите к origin-side диагностике ниже.

## Выполнить на Droplet (SSH)

### Вариант 1: Использовать server-side скрипт (рекомендуется)

```bash
# Скопировать скрипт на сервер
scp scripts/diagnose_production.sh user@your-droplet:/tmp/

# На сервере выполнить
ssh user@your-droplet
chmod +x /tmp/diagnose_production.sh
/tmp/diagnose_production.sh
```

### Вариант 2: Выполнить server-side команды вручную

```bash
# На Droplet (SSH)
cd /srv/pulseplate-production

# Если на сервере нет `docker compose` (v2), используйте `docker-compose` (v1):
# - Проверить:
#   docker compose version || true
#   docker-compose --version || true
#
# - В командах ниже замените `docker compose` на `docker-compose`, если нужно.

# 1) Кто слушает 80/443 на сервере
sudo ss -lntp | grep -E ':80|:443' || true

# 2) Контейнеры и порты
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'

# 3) Статус compose (важно: именно тот файл в /srv)
docker compose -f docker-compose.production.yaml ps

# 4) Логи Caddy (обычно там сразу видно причину)
docker compose -f docker-compose.production.yaml logs --tail=200 caddy

# 5) Логи app
docker compose -f docker-compose.production.yaml logs --tail=200 app

# 6) Firewall (если включен)
sudo ufw status || true

# 7) Проверить Caddyfile
ls -la /srv/pulseplate-production/Caddyfile.production
cat /srv/pulseplate-production/Caddyfile.production

# 8) Проверить PRODUCTION_DOMAIN
grep PRODUCTION_DOMAIN /srv/pulseplate-production/.env || echo "PRODUCTION_DOMAIN not found in .env"
```

## Что проверить

### ✅ Порты 80/443 слушаются
Должно быть:
```text
LISTEN  0  4096  0.0.0.0:80  0.0.0.0:*  users:(("caddy",pid=12345,fd=3))
LISTEN  0  4096  0.0.0.0:443  0.0.0.0:*  users:(("caddy",pid=12345,fd=4))
```

### ✅ Контейнеры запущены
Должно быть:
```text
NAMES          IMAGE          PORTS                    STATUS
caddy          caddy:2.7.6     0.0.0.0:80->80/tcp...    Up X minutes
app            ghcr.io/...     8000/tcp                 Up X minutes
```

### ✅ Caddyfile существует
```bash
ls -la /srv/pulseplate-production/Caddyfile.production
# Должен показать файл
```

### ✅ PRODUCTION_DOMAIN задан
```bash
grep PRODUCTION_DOMAIN /srv/pulseplate-production/.env
# Должно показать: PRODUCTION_DOMAIN=your-domain.com
```

## Типичные проблемы

### Проблема: Caddyfile не найден
```bash
# Решение:
sudo cp /path/to/repo/deploy/Caddyfile.production /srv/pulseplate-production/
sudo chmod 644 /srv/pulseplate-production/Caddyfile.production
cd /srv/pulseplate-production
docker compose -f docker-compose.production.yaml restart caddy
```

### Проблема: PRODUCTION_DOMAIN не задан
```bash
# Решение:
cd /srv/pulseplate-production
echo "PRODUCTION_DOMAIN=your-domain.com" >> .env
docker compose -f docker-compose.production.yaml restart caddy
```

### Проблема: Порт занят другим процессом
```bash
# Проверить:
sudo lsof -i :80
sudo lsof -i :443

# Остановить конфликтующий сервис:
sudo systemctl stop nginx
sudo systemctl stop apache2
```

### Проблема: Firewall блокирует
```bash
# Решение:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

### Проблема: Контейнеры не запущены
```bash
# Решение:
cd /srv/pulseplate-production
docker compose -f docker-compose.production.yaml up -d
docker compose -f docker-compose.production.yaml logs caddy
```
