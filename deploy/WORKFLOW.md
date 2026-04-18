# Production Deployment Workflow

## 🎯 Canonical Workflow (запомни навсегда)

**RU:** Правильный порядок действий для деплоя в production.
**EN:** Correct order of operations for production deployment.

---

## 📍 Где что делать

### 1️⃣ **Cursor (локально) — Код и коммиты**

**RU:** Вся работа с кодом происходит **только локально** в Cursor.
**EN:** All code work happens **only locally** in Cursor.

**Что делаем:**
- ✅ Правка кода (`legacy_app.py`, `app/`, `core/`, и т.д.)
- ✅ Коммиты и push в GitHub
- ✅ Создание PR и merge

**Что НЕ делаем:**
- ❌ Правка кода напрямую на сервере
- ❌ Коммиты с сервера
- ❌ Изменение файлов в `/srv/pulseplate-production/` (кроме `.env` и конфигов)

**Пример:**

```bash
# В Cursor (локально)
git add app/legacy_app.py
git commit -m "fix(health): correct git_sha formatting and environment fallback"
git push origin main
```

⏳ **Ждём**, пока GitHub Actions:
- Соберёт Docker image **и** запушит его в `ghcr.io/<owner>/<repo>:latest` (или `prod-vX.Y.Z`)

---

### 2️⃣ **GitHub Actions — Сборка образа**

**RU:** GitHub Actions автоматически собирает Docker image после push.
**EN:** GitHub Actions automatically builds Docker image after push.

**Что происходит:**
1. Push в `main` → триггерит workflow
2. CI собирает Docker image
3. Образ пушится в GHCR: `ghcr.io/katsiarynakavaleuskaya/pulseplate:latest`

**Важно для production tags:**
- `build-production` сам по себе **не означает**, что production origin обновлён.
- Для semver tag `vX.Y.Z` production deploy запускается только после того, как
  workflow в `production-deploy-config` прочитает `PROD_DEPLOY_MODE` и
  `WEB_IOS_RELEASE_READY`, а также `PRODUCTION_ENV_READY`, через GitHub Actions variables API
  и разрешит ровно один deploy lane.
- Если стандартный `github.token` получает `403` на чтении `production`
  environment variables, bridge-job должен retry через секрет
  `PRODUCTION_ENV_READ_TOKEN`; иначе tag lane упадёт ещё до выбора deploy mode.
- Если эти флаги не выставлены корректно, CD останется в режиме build-only:
  образ будет в GHCR, но live origin не изменится.
- `PRODUCTION_ENV_READY=true` можно выставлять только после того, как infra/release
  owner уже создал серверный `/srv/pulseplate-production/.env` (или `$DEPLOY_DIR/.env`)
  и подтвердил, что host bootstrap is complete. GitHub Actions этот файл не создаёт.

**Проверка:**
- Зайди в GitHub → Actions → проверь, что workflow зелёный
- Проверь GHCR: <https://github.com/katsiarynakavaleuskaya/pulseplate/pkgs/container/pulseplate>

---

### 3️⃣ **DigitalOcean (сервер) — Только pull и restart**

**RU:** На сервере **только** обновляем образ и перезапускаем контейнеры.
**EN:** On server **only** update image and restart containers.

**Что делаем:**
- ✅ `docker pull` нового образа
- ✅ one-shot migrations через release image до рестарта приложения
- ✅ `docker compose up -d --force-recreate` (или `docker run`)
- ✅ Проверка health endpoint

**Что НЕ делаем:**
- ❌ Правка кода на сервере
- ❌ `git clone` или `git pull` на сервере
- ❌ Изменение файлов приложения (кроме `.env` и конфигов)

**Пример:**

```bash
# На сервере (через SSH или DigitalOcean Console)
ssh root@pulseplate.app
cd /srv/pulseplate-production

# 1. Подтянуть новый образ
docker compose -f docker-compose.production.yaml pull

# 2. Прогнать миграции через release image
docker compose --env-file .env -f docker-compose.production.yaml run --rm --no-deps app alembic upgrade head

# 3. Перезапустить сервисы
docker compose -f docker-compose.production.yaml up -d --force-recreate

# 4. Проверить статус
docker compose -f docker-compose.production.yaml ps

# 5. Проверить health
curl -fsS https://pulseplate.app/health | jq .
```

Пример ответа:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "git_sha": "f4c8b72e593f",  # pragma: allowlist secret
  "timestamp": "2026-01-01T13:27:54.215248+00:00",
  "environment": "production"
}
```

> ℹ️ `git_sha` нормализуется из `GIT_SHA`:
> - поддерживает `sha256:<digest>` и `repo@sha256:<digest>`
> - в `/health` отображаются первые **12 символов** digest

---

## 🔄 Полный цикл деплоя

### Шаг 1: Локально (Cursor)

```bash
# 1. Внести изменения в код
vim app/legacy_app.py  # или через Cursor UI

# 2. Проверить локально (опционально)
make test
make lint

# 3. Закоммитить
git add app/legacy_app.py
git commit -m "fix(health): improve environment detection"
git push origin main
```

### Шаг 2: GitHub Actions

1. Зайди в GitHub → Actions
2. Дождись завершения workflow (зелёный статус)
3. Проверь, что image собран и запушен в GHCR

### Шаг 3: На сервере (DigitalOcean)

```bash
# Подключиться к серверу
ssh root@pulseplate.app
# Или через DigitalOcean Console

# Перейти в deploy директорию
cd /srv/pulseplate-production

# Canonical production contract: managed PostgreSQL lives outside compose and is reached via DATABASE_URL

# Обновить образ app из registry (IMAGE_REF)
docker compose -f docker-compose.production.yaml pull app

# Прогнать миграции через one-shot release container
docker compose --env-file .env -f docker-compose.production.yaml run --rm --no-deps app alembic upgrade head

# Затем пересобрать Caddy из синхронизированного release shell bundle и перезапустить стек
docker compose -f docker-compose.production.yaml build caddy
docker compose -f docker-compose.production.yaml up -d --force-recreate

# Проверить
curl -fsS https://pulseplate.app/health | jq .
```

Пример ответа:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "git_sha": "f4c8b72e593f",  # pragma: allowlist secret
  "timestamp": "2026-01-01T13:27:54.215248+00:00",
  "environment": "production"
}
```

### Emergency apex shell recovery (DigitalOcean + Cloudflare drift)

Если production apex внезапно уходит в белый экран, JSON probe или пустой shell,
не чини это руками только в Cloudflare. Сначала восстанови repo-owned shell
bundle на origin.

**Жёсткое правило:** emergency shell sync разрешён только из **merged canonical
tree** (`origin/main` / release commit) или из CI-produced release bundle.
Нельзя копировать `deploy/` и `frontend/` с произвольного локального dirty checkout.

```bash
# Локально: перейти на merged canonical tree
git fetch origin main
git switch --detach origin/main

# С этого checkout синхронизировать production shell bundle на сервер
scp deploy/Caddyfile.production ubuntu@64.226.117.163:/srv/pulseplate-production/Caddyfile.production
scp deploy/docker-compose.production.yaml ubuntu@64.226.117.163:/srv/pulseplate-production/docker-compose.production.yaml
rsync -az --delete frontend/ ubuntu@64.226.117.163:/srv/frontend/
scp scripts/diagnose_web.sh ubuntu@64.226.117.163:/srv/pulseplate-production/scripts/diagnose_web.sh

# На сервере: rebuild/restart только edge shell
ssh ubuntu@64.226.117.163 '
  cd /srv/pulseplate-production &&
  bash scripts/redeploy_caddy.sh
'
```

После этого:

```bash
BASE_URL=https://pulseplate.app bash scripts/diagnose_web.sh
```

Если host всё ещё скрыт за full-host Cloudflare Access, используй private probe:

```bash
CF_ACCESS_CLIENT_ID=... \
CF_ACCESS_CLIENT_SECRET=... \
BASE_URL=https://pulseplate.app \
bash scripts/diagnose_web.sh
```

Если apex shell восстановился, а `/sitemap.xml` всё ещё не XML, значит edge уже
здоров, но backend image ещё не содержит нужный route. В этом случае нужен
отдельный deploy нового app image, а не очередная ручная правка Cloudflare.

### Public reopen after private recovery

Когда private verification прошла, снимай full-host Access не "в ноль", а вместе
с narrow temporary bypass только для публичных GET surfaces:

- `/`
- SPA routes
- `/assets/*`
- `/favicon*`
- `/sitemap.xml`
- `/privacy`
- `/terms`
- `/legacy/bmi-calculator`

Не ослабляй:

- `/api*`
- `/admin*`
- `/ws*`
- `/openapi.json`
- `/health`
- `/docs*`
- `/redoc*`
- `/debug_env`

---

## 🧠 Ментальная модель

| Где                | Что делаем                                    | Что НЕ делаем                          |
| ------------------ | ---------------------------------------------- | --------------------------------------- |
| **Cursor**         | Код, фиксы, коммиты, PR                       | Правка на сервере                       |
| **GitHub Actions** | Автоматическая сборка Docker image             | Ручная сборка                           |
| **DigitalOcean**   | `docker compose pull app` + one-shot `alembic upgrade head` + `build caddy` + `up` + `diagnose_web.sh` (см. `scripts/redeploy_caddy.sh`) | Правка кода, git clone, shell sync из unmerged/dirty checkout |

---

## ⚠️ Важные правила

### ❌ Никогда не делай на сервере

1. **Правка кода приложения:**
   ```bash
   # ❌ НЕПРАВИЛЬНО
   vim /srv/pulseplate-production/app/main.py
   ```

2. **Git операции:**
   ```bash
   # ❌ НЕПРАВИЛЬНО
   cd /srv/pulseplate-production
   git clone ...
   git pull ...
   ```

3. **Прямое изменение файлов в контейнере:**
   ```bash
   # ❌ НЕПРАВИЛЬНО
   docker exec -it app vim /app/legacy_app.py
   ```

### ✅ Правильно

1. **Изменить код локально → commit → push → pull image на сервере**

2. **Изменить `.env` на сервере (это конфиг, не код):**
   ```bash
   # ✅ ПРАВИЛЬНО
   cd /srv/pulseplate-production
   nano .env  # добавить APP_ENV=production
   docker compose up -d --force-recreate app
   ```

3. **Изменить `Caddyfile.production` на сервере (это конфиг):**
   ```bash
   # ✅ ПРАВИЛЬНО
   cd /srv/pulseplate-production
   nano Caddyfile.production
   docker compose up -d --force-recreate caddy
   ```

---

## 🔍 Проверка после деплоя

### 1. Проверить, что новый образ подтянут

```bash
docker images | grep pulseplate
# Должен быть свежий image с актуальным timestamp
```

### 2. Проверить, что контейнер использует новый образ

```bash
# Получить container id сервиса app и посмотреть image
APP_CID="$(docker compose -f docker-compose.production.yaml ps -q app)"
docker inspect "$APP_CID" --format '{{.Config.Image}}'
# Должен показывать актуальный image ID
```

### 3. Проверить health endpoint

```bash
curl -fsS https://pulseplate.app/health | jq .
```

Пример ответа:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "git_sha": "f4c8b72e593f",  # pragma: allowlist secret
  "timestamp": "2026-01-01T13:27:54.215248+00:00",
  "environment": "production"
}
```

> ℹ️ `git_sha` нормализуется из `GIT_SHA`:
> - поддерживает `sha256:<digest>` и `repo@sha256:<digest>`
> - в `/health` отображаются первые **12 символов** digest

### Release shell parity

- Tag-based production deploy must ship the public shell inputs together:
  `frontend/`, `deploy/Caddyfile.production`, and `scripts/diagnose_web.sh`.
- `scripts/deploy_production.sh` now rebuilds `caddy` during production deploy, so the
  public SPA shell stays aligned with the same release tree as the backend `IMAGE_REF`.
- SSH production deploys use run-scoped `/tmp` bundle paths and the production deploy
  lane is serialized so different tags cannot mix shell artifacts on the same host.
- If the backend digest is fresh but `GET /` still returns the direct API JSON probe,
  treat that as edge/shell parity drift and run `BASE_URL=https://$PRODUCTION_DOMAIN bash scripts/diagnose_web.sh`
  before assuming an application bug.

### 4. Проверить логи

```bash
docker compose -f docker-compose.production.yaml logs app --tail=50
# Не должно быть ошибок
```

### Git SHA verification

В production `GIT_SHA` может быть:
- git commit hash (CI)
- docker image digest (`sha256:...`)
- `repo@sha256:...`

Endpoint `/health` автоматически нормализует значение и показывает
короткий стабильный идентификатор (12 символов), пригодный для сверки деплоя.

---

## 🚨 Troubleshooting

### Проблема: `/health` всё ещё показывает старые значения

**Причина:** Контейнер использует старый образ.

**Решение:**
```bash
# 1. Убедиться, что новый образ подтянут
docker compose -f docker-compose.production.yaml pull

# 2. Принудительно пересоздать контейнер
docker compose -f docker-compose.production.yaml up -d --force-recreate app

# 3. Проверить, что контейнер пересоздан
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.CreatedAt}}'
```

### Проблема: `docker pull` не находит новый образ

**Причина:** GitHub Actions ещё не завершился, или image не запушен.

**Решение:**
1. Проверить GitHub Actions: <https://github.com/.../actions>
2. Проверить GHCR: <https://github.com/.../pkgs/container/pulseplate>
3. Убедиться, что используется правильный image tag

### Проблема: Environment переменные не применяются

**Причина:** `.env` не обновлён или контейнер не перезапущен.

**Решение:**
```bash
# 1. Проверить .env
cat .env | grep -E 'APP_ENV|ENVIRONMENT'

# 2. Обновить .env (если нужно)
nano .env

# 3. Перезапустить контейнер
docker compose -f docker-compose.production.yaml up -d --force-recreate app

# 4. Проверить env внутри контейнера (через service name, без хардкода)
docker compose -f docker-compose.production.yaml exec -T app env | grep -E 'APP_ENV|ENVIRONMENT'
```

---

## 📚 Связанные документы

- `deploy/PRODUCTION.md` - Полная документация по production deployment
- `scripts/PRODUCTION_ENV_FIX.md` - Исправление environment переменных
- `scripts/DIGITALOCEAN_CONSOLE_ACCESS.md` - Доступ к терминалу DigitalOcean

---

## 💡 Best Practices

1. **Всегда тестируй локально** перед push
2. **Всегда жди зелёного CI** перед деплоем на сервер
3. **Всегда проверяй health endpoint** после деплоя
4. **Используй pinned digests** для production (не `latest`)
5. **Делай backup `.env`** перед изменениями
6. **Используй provider snapshots / PITR** как baseline backup для managed PostgreSQL, а не локальный `pg_dump` в hot path

---

## 🔐 Security Notes

- Никогда не коммить `.env` файлы
- Используй GitHub Secrets для чувствительных данных
- Регулярно обновляй Docker images (security patches)
- Используй `docker compose pull` перед `up` для получения последних security updates
