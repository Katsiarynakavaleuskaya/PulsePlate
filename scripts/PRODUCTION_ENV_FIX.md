# Исправление Environment переменных на Production сервере

## 🚨 Проблема

На сервере compose не может распарсить файл из-за отсутствующих переменных:
- `POSTGRES_PASSWORD` (если в compose есть postgres сервис)
- `APP_ENV=production`
- `ENVIRONMENT=production`

## ✅ Быстрое решение (Вариант B - dummy env)

Если нужно поднять app **прямо сейчас**:

```bash
cd /srv/pulseplate-production

# 1. Очистить дубли переменных и добавить правильные значения
sed -i '/^APP_ENV=/d;/^ENVIRONMENT=/d;/^POSTGRES_PASSWORD=/d' .env
printf "\nAPP_ENV=production\nENVIRONMENT=production\nPOSTGRES_PASSWORD=dummy\n" >> .env  # pragma: allowlist secret

# 2. Проверить compose движок (v1 имеет приоритет на серверах)
if command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
  echo "Using: docker-compose (v1)"
elif docker compose version >/dev/null 2>&1; then
  DC="docker compose"
  echo "Using: docker compose (v2)"
else
  echo "❌ Neither docker-compose nor docker compose found"
  exit 1
fi

# 3. Валидировать compose
# Note: docker-compose v1 читает .env автоматически, --env-file не нужен
if [ "$DC" = "docker-compose" ]; then
  $DC -f docker-compose.production.yaml config >/dev/null
else
  $DC --env-file .env -f docker-compose.production.yaml config >/dev/null
fi

# 4. Подтянуть свежие образы (важно для обновления Caddy!)
if [ "$DC" = "docker-compose" ]; then
  $DC -f docker-compose.production.yaml pull
else
  $DC --env-file .env -f docker-compose.production.yaml pull
fi

# 5. Перезапустить все сервисы
if [ "$DC" = "docker-compose" ]; then
  $DC -f docker-compose.production.yaml up -d --force-recreate
else
  $DC --env-file .env -f docker-compose.production.yaml up -d --force-recreate
fi

# 6. Проверить статус
if [ "$DC" = "docker-compose" ]; then
  $DC -f docker-compose.production.yaml ps
else
  $DC --env-file .env -f docker-compose.production.yaml ps
fi

# 7. Проверить env внутри контейнера
docker exec -it pulseplate-production_app_1 python -c "import os; print('APP_ENV:', os.getenv('APP_ENV')); print('ENVIRONMENT:', os.getenv('ENVIRONMENT'))"

# 8. Проверить health
curl -fsS https://pulseplate.app/health | jq .
```

## 🔧 Автоматизированное решение (скрипт)

Используйте готовый скрипт:

```bash
cd /srv/pulseplate-production
bash scripts/fix_production_env.sh
```

Скрипт автоматически:
1. Находит deploy директорию
2. Определяет версию docker compose (v2 или v1)
3. Проверяет, есть ли postgres в compose
4. Пытается найти существующий `POSTGRES_PASSWORD` из контейнера
5. Обновляет `.env` файл
6. Валидирует compose файл
7. Перезапускает app сервис

## 📋 Правильное решение (Вариант A - profiles)

Если в compose есть postgres, но он пока не нужен, используйте profiles:

### 1. Добавить profile к postgres в `docker-compose.production.yaml`:

```yaml
services:
  postgres:
    profiles: ["postgres"]
    # ... остальная конфигурация
```

### 2. Убрать `depends_on: [postgres]` у app (если есть)

### 3. Запуск без postgres:

```bash
docker compose -f docker-compose.production.yaml up -d
```

### 4. Когда понадобится postgres:

```bash
docker compose --profile postgres -f docker-compose.production.yaml up -d
```

## 🔍 Проверка текущего состояния

### Проверить, есть ли postgres в compose:

```bash
cd /srv/pulseplate-production
grep -E "^\s+(postgres|db):" docker-compose.production.yaml || echo "No postgres service found"
```

### Проверить зависимости app:

```bash
grep -A 10 "^\s+app:" docker-compose.production.yaml | grep -E "depends_on|DATABASE_URL"
```

### Проверить существующий postgres контейнер:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep -i postgres
```

Если контейнер есть, можно извлечь пароль:

```bash
CID="$(docker ps -q --filter "name=postgres" | head -1)"
docker inspect "$CID" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep POSTGRES_PASSWORD
```

## ⚠️ Важные замечания

1. **`POSTGRES_PASSWORD=dummy`** - это временное решение. Если postgres не используется, лучше использовать profiles (Вариант A).

2. **Проверка compose движка** - всегда используйте проверку версии:
   ```bash
   if docker compose version >/dev/null 2>&1; then
     DC="docker compose"
   else
     DC="docker-compose"
   fi
   ```

3. **Валидация перед запуском** - всегда проверяйте compose файл:
   ```bash
   # Для docker-compose v1 (читает .env автоматически)
   docker-compose -f docker-compose.production.yaml config >/dev/null

   # Для docker compose v2 (нужен --env-file)
   docker compose --env-file .env -f docker-compose.production.yaml config >/dev/null
   ```

4. **Важно: docker-compose v1 vs docker compose v2**:
   - `docker-compose` (v1) автоматически читает `.env` из текущей директории
   - `docker compose` (v2) требует `--env-file .env` явно
   - На большинстве серверов установлен v1, поэтому скрипт проверяет v1 первым

4. **Backup .env** - скрипт автоматически создаёт backup перед изменениями.

## 🔐 Security Notes

- `POSTGRES_PASSWORD=dummy` безопасен, если postgres не используется
- Для реального postgres используйте сильный пароль из GitHub Secrets
- `.env` файл должен иметь права `600`: `chmod 600 .env`

## 📝 Чеклист

- [ ] Проверить версию docker compose
- [ ] Проверить наличие postgres в compose
- [ ] Добавить необходимые переменные в `.env`
- [ ] Валидировать compose файл
- [ ] Перезапустить app сервис
- [ ] Проверить health endpoint: `curl https://pulseplate.app/health | jq .`
- [ ] Убедиться, что `environment: "production"`
