# Исправление Environment переменных на Production сервере

## 🚨 Проблема

Production deploy contract теперь Postgres-first и fail-closed. Сервер не должен запускаться с:

- `DATABASE_URL=sqlite:///...`
- отсутствующим `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`
- dev-friendly флагами вроде `ALLOW_DEV_API_KEY=true`

## ✅ Канонический production env contract

```bash
cd /srv/pulseplate-production

cat >> .env <<'EOF'
PRODUCTION_DOMAIN=yourdomain.com
DATABASE_URL=postgresql+psycopg://<user>:<password>@postgres:5432/<dbname>
POSTGRES_DB=pulseplate
POSTGRES_USER=pulseplate
POSTGRES_PASSWORD=replace-with-strong-secret
SUBSCRIPTION_DB_ENABLED=true
ALLOW_DEV_API_KEY=false
API_KEY_REQUIRED=true
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

1. Требует `postgres` service в production compose
2. Нормализует `APP_ENV`, `ENVIRONMENT`, `SUBSCRIPTION_DB_ENABLED`, `ALLOW_DEV_API_KEY`, `API_KEY_REQUIRED`
3. Проверяет `DATABASE_URL`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
4. Падает, если `DATABASE_URL` не использует `postgresql+psycopg://`
5. Валидирует compose и перезапускает сервисы

## 🔍 Ручная проверка

```bash
cd /srv/pulseplate-production

grep -E '^DATABASE_URL=' .env
grep -E '^POSTGRES_(DB|USER|PASSWORD)=' .env

docker compose --env-file .env -f docker-compose.production.yaml config >/dev/null
docker compose --env-file .env -f docker-compose.production.yaml up -d --force-recreate

curl -fsS https://pulseplate.app/ready | jq .
```

## ⚠️ Важные замечания

1. `POSTGRES_PASSWORD=dummy` больше не является допустимым production workaround.
2. `postgres` не должен становиться optional через `profiles` для production.
3. `DATABASE_URL` должен указывать на `@postgres:5432` внутри compose network.
4. SQLite разрешён только для local/dev/test fallback, не для canonical production deploy path.

## 🔐 Security Notes

- Используйте сильный `POSTGRES_PASSWORD` и храните `.env` с правами `600`.
- Проверяйте readiness через `/ready` или `/health/db`, а не через liveness-only `/health`.
- Не удаляйте `depends_on: postgres` из production compose: приложение должно ждать healthy DB.

## 📝 Чеклист

- [ ] В `.env` задан Postgres DSN
- [ ] `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` заданы
- [ ] `SUBSCRIPTION_DB_ENABLED=true`
- [ ] `ALLOW_DEV_API_KEY=false`
- [ ] `API_KEY_REQUIRED=true`
- [ ] `docker compose ... config` проходит
- [ ] `curl https://pulseplate.app/ready | jq .` возвращает 200
