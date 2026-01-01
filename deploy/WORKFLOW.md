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
2. Workflow собирает Docker image
3. Image пушится в GHCR: `ghcr.io/katsiarynakavaleuskaya/pulseplate:latest`

**Проверка:**
- Зайди в GitHub → Actions → проверь, что workflow зелёный
- Проверь GHCR: <https://github.com/katsiarynakavaleuskaya/pulseplate/pkgs/container/pulseplate>

---

### 3️⃣ **DigitalOcean (сервер) — Только pull и restart**

**RU:** На сервере **только** обновляем образ и перезапускаем контейнеры.
**EN:** On server **only** update image and restart containers.

**Что делаем:**
- ✅ `docker pull` нового образа
- ✅ `docker-compose up -d --force-recreate` (или `docker run`)
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
docker-compose -f docker-compose.production.yaml pull

# 2. Перезапустить сервисы
docker-compose -f docker-compose.production.yaml up -d --force-recreate

# 3. Проверить статус
docker-compose -f docker-compose.production.yaml ps

# 4. Проверить health
curl -fsS <https://pulseplate.app/health> | jq .
```

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

# Обновить и перезапустить
docker-compose -f docker-compose.production.yaml pull
docker-compose -f docker-compose.production.yaml up -d --force-recreate

# Проверить
curl -fsS <https://pulseplate.app/health> | jq .
```

---

## 🧠 Ментальная модель

| Где                | Что делаем                                    | Что НЕ делаем                          |
| ------------------ | ---------------------------------------------- | --------------------------------------- |
| **Cursor**         | Код, фиксы, коммиты, PR                       | Правка на сервере                       |
| **GitHub Actions** | Автоматическая сборка Docker image             | Ручная сборка                           |
| **DigitalOcean**   | `docker pull` + `docker-compose up`            | Правка кода, git clone, изменение файлов |

---

## ⚠️ Важные правила

### ❌ Никогда не делай на сервере:

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

### ✅ Правильно:

1. **Изменить код локально → commit → push → pull image на сервере**

2. **Изменить `.env` на сервере (это конфиг, не код):**
   ```bash
   # ✅ ПРАВИЛЬНО
   cd /srv/pulseplate-production
   nano .env  # добавить APP_ENV=production
   docker-compose up -d --force-recreate app
   ```

3. **Изменить `Caddyfile.production` на сервере (это конфиг):**
   ```bash
   # ✅ ПРАВИЛЬНО
   cd /srv/pulseplate-production
   nano Caddyfile.production
   docker-compose up -d --force-recreate caddy
   ```

---

## 🔍 Проверка после деплоя

### 1. Проверить, что новый образ подтянут:

```bash
docker images | grep pulseplate
# Должен быть свежий image с актуальным timestamp
```

### 2. Проверить, что контейнер использует новый образ:

```bash
docker inspect pulseplate-production_app_1 | grep Image
# Должен показывать актуальный image ID
```

### 3. Проверить health endpoint:

```bash
curl -fsS <https://pulseplate.app/health> | jq .
# Должен показывать актуальные значения:
# - "environment": "production"
# - "git_sha": "abc12345" (если GIT_SHA установлен)
```

### 4. Проверить логи:

```bash
docker-compose -f docker-compose.production.yaml logs app --tail=50
# Не должно быть ошибок
```

---

## 🚨 Troubleshooting

### Проблема: `/health` всё ещё показывает старые значения

**Причина:** Контейнер использует старый образ.

**Решение:**
```bash
# 1. Убедиться, что новый образ подтянут
docker-compose -f docker-compose.production.yaml pull

# 2. Принудительно пересоздать контейнер
docker-compose -f docker-compose.production.yaml up -d --force-recreate app

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
docker-compose -f docker-compose.production.yaml up -d --force-recreate app

# 4. Проверить env внутри контейнера
docker exec pulseplate-production_app_1 env | grep -E 'APP_ENV|ENVIRONMENT'
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

---

## 🔐 Security Notes

- Никогда не коммить `.env` файлы
- Используй GitHub Secrets для чувствительных данных
- Регулярно обновляй Docker images (security patches)
- Используй `docker-compose pull` перед `up` для получения последних security updates
