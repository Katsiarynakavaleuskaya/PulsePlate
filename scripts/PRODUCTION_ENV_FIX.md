# Исправление Environment переменных на Production сервере

## 🚨 Проблема

Production deploy contract теперь managed-PostgreSQL-only и fail-closed. Сервер не должен запускаться с:

- `DATABASE_URL=sqlite:///...`
- `DATABASE_URL`, указывающим на compose-local `@postgres:5432`
- dev-friendly флагами вроде `ALLOW_DEV_API_KEY=true`

## ✅ Канонический production env contract

```bash
cd /srv/pulseplate-production

cat >> .env <<'EOF'
PRODUCTION_DOMAIN=yourdomain.com
DATABASE_URL=postgresql+psycopg://<user>:<password>@db.example.com:25060/<dbname>
SUBSCRIPTION_DB_ENABLED=true
ALLOW_DEV_API_KEY=false
API_KEY_REQUIRED=true  # compatibility flag for request-time API-key enforcement
APP_ENV=production
ENVIRONMENT=production
EOF
```

## 🔧 Автоматизированное решение

Используйте готовый fail-closed helper:

```bash
cd /srv/pulseplate-production
bash scripts/fix_production_env.sh
```

Скрипт:

1. Требует отсутствие `postgres` service в canonical production compose
2. Нормализует `APP_ENV`, `ENVIRONMENT`, `SUBSCRIPTION_DB_ENABLED`, `ALLOW_DEV_API_KEY` и совместимый `API_KEY_REQUIRED`
3. Проверяет `DATABASE_URL`
4. Падает, если `DATABASE_URL` не использует `postgresql+psycopg://` или указывает на `@postgres:5432`
5. Валидирует compose и перезапускает сервисы

## 🔍 Ручная проверка

```bash
cd /srv/pulseplate-production

grep -E '^DATABASE_URL=' .env

docker compose --env-file .env -f docker-compose.production.yaml config >/dev/null
docker compose --env-file .env -f docker-compose.production.yaml up -d --force-recreate

PRODUCTION_DOMAIN="$(grep '^PRODUCTION_DOMAIN=' .env | tail -1 | cut -d'=' -f2- | tr -d '\r\n')"
curl -fsS "https://${PRODUCTION_DOMAIN}/ready" | jq .
```

## ⚠️ Важные замечания

1. `postgres` не должен появляться даже optional через `profiles` для canonical production.
2. `DATABASE_URL` не должен указывать на `@postgres:5432` внутри compose network.
3. SQLite разрешён только для local/dev/test fallback, не для canonical production deploy path.
4. Backup / PITR для production managed Postgres должны обеспечиваться провайдером, а не hot-path скриптом деплоя.

## 🔐 Security Notes

- Храните managed PostgreSQL credentials only inside `DATABASE_URL` and keep `.env` permissions at `600`.
- Проверяйте readiness через `/ready` или `/health/db`, а не через liveness-only `/health`.
- Не добавляйте `depends_on: postgres` или local `postgres` service обратно в canonical production compose.

## 📝 Чеклист

- [ ] В `.env` задан Postgres DSN
- [ ] DSN указывает на внешний managed Postgres host, не `@postgres:5432`
- [ ] `SUBSCRIPTION_DB_ENABLED=true`
- [ ] `ALLOW_DEV_API_KEY=false`
- [ ] При необходимости для совместимости задан `API_KEY_REQUIRED=true`
- [ ] `docker compose ... config` проходит
- [ ] `curl "https://${PRODUCTION_DOMAIN}/ready" | jq .` возвращает 200
