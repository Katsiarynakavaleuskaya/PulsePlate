# Проверка Production сервера (без SSH)

## ⚠️ Проблема: SSH недоступен

Если `ssh root@pulseplate.app` выдает `Connection timed out`, это нормально, если:

- Сервер за Cloudflare (проксирует только 80/443, не 22)
- Firewall блокирует SSH
- SSH на другом порту

## ✅ Решение: Проверка через публичные endpoints

### Шаг 1: Проверка Health Endpoint

```bash
curl -fsS https://pulseplate.app/health | jq .
```

**Ожидаемый результат:**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "git_sha": "abc12345",  // не "unknown"
  "timestamp": "2026-01-01T13:05:58.902552+00:00",
  "environment": "production"  // не "development"
}
```

**Текущий статус (проблема):**

- ❌ `"environment": "development"` → должно быть `"production"`
- ❌ `"git_sha": "unknown"` → должно быть реальный SHA

### Шаг 2: Проверка портов (если есть доступ к серверу через другой метод)

Если у вас есть доступ к серверу через:

- DigitalOcean Console (web terminal)
- VPS provider console
- Self-hosted runner
- Другой SSH порт (например, `ssh -p 2222 root@pulseplate.app`)

Тогда выполните на сервере:

```bash
# Найти deploy директорию
sudo find / -maxdepth 4 -name "docker-compose.production.yaml" 2>/dev/null

# Перейти в найденную директорию (замените /srv/pulseplate-production на реальный путь)
cd /srv/pulseplate-production  # или /opt/pulseplate

# Проверить контейнеры
docker compose -f docker-compose.production.yaml ps

# Проверить environment переменные
docker compose -f docker-compose.production.yaml exec -T app python -c "import os; print('APP_ENV:', os.getenv('APP_ENV')); print('ENVIRONMENT:', os.getenv('ENVIRONMENT')); print('GIT_SHA:', os.getenv('GIT_SHA'))"

# Проверить health изнутри Docker сети
docker compose -f docker-compose.production.yaml exec -T caddy wget -qO- http://app:8000/health && echo
```

### Шаг 3: Исправление environment переменных (на сервере)

Если `environment` показывает `"development"`, нужно добавить в `.env`:

```bash
cd /srv/pulseplate-production  # или ваш путь
echo "APP_ENV=production" >> .env
echo "ENVIRONMENT=production" >> .env
echo "GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')" >> .env

# Перезапустить app контейнер
docker compose -f docker-compose.production.yaml up -d --force-recreate app
```

### Шаг 4: Проверка после исправления

```bash
# Снова проверить health endpoint
curl -fsS https://pulseplate.app/health | jq .

# Должно показать:
# "environment": "production"
# "git_sha": "abc12345" (или реальный SHA)
```

## 🔧 Альтернативные способы доступа к серверу

### 1. DigitalOcean Console (рекомендуется)

**Подробная инструкция:** См. `scripts/DIGITALOCEAN_CONSOLE_ACCESS.md`

**Кратко:**
1. Зайдите в https://cloud.digitalocean.com
2. Выберите **"Droplets"** в левом меню
3. Нажмите на имя вашего сервера
4. Нажмите кнопку **"Console"** (или **"Access"** → **"Launch Droplet Console"**)
5. Войдите в систему (username: `root`, password: ваш пароль)
6. Выполните команды из Шага 2

### 2. Проверка через другой SSH порт

```bash
# Попробуйте другие порты (если настроены)
ssh -p 2222 root@pulseplate.app
ssh -p 22022 root@pulseplate.app
```

### 3. Self-hosted runner (рекомендуется)

Если у вас настроен self-hosted runner на сервере, используйте его для выполнения команд:

```yaml
# В GitHub Actions workflow
- name: Check server status
  if: runner.labels.pulseplate-prod
  run: |
    cd /srv/pulseplate-production
    docker compose ps
    docker compose exec -T app python -c "import os; print(os.getenv('APP_ENV'))"
```

## 📋 Чеклист для исправления

- [ ] Проверить health endpoint: `curl https://pulseplate.app/health`
- [ ] Найти способ доступа к серверу (Console, другой порт, self-hosted runner)
- [ ] Найти deploy директорию: `sudo find / -maxdepth 4 -name "docker-compose.production.yaml"`
- [ ] Добавить `APP_ENV=production` в `.env`
- [ ] Добавить `ENVIRONMENT=production` в `.env`
- [ ] Добавить `GIT_SHA=...` в `.env` (опционально)
- [ ] Перезапустить app контейнер: `docker compose up -d --force-recreate app`
- [ ] Проверить health endpoint снова: должно быть `"environment": "production"`

## 🚨 Если ничего не помогает

1. Проверьте, что Caddy контейнер запущен: `docker compose ps caddy`
2. Проверьте логи: `docker compose logs app` и `docker compose logs caddy`
3. Проверьте, что порты 80/443 открыты: `sudo ss -tlnp | grep -E ':(80|443)'`
4. Проверьте Cloudflare настройки (DNS должен быть "Proxied", не "DNS only")
