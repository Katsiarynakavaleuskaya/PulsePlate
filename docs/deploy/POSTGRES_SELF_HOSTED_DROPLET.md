# Postgres Self-Hosted Droplet Foundation

**Purpose:** Canonical production database baseline for PulsePlate on Droplet. Postgres is the primary prod DB; SQLite remains for local/dev/test fallback only.

**Design rationale (architecture):**

- Postgres runs internal-only (no public 5432); app connects via `DATABASE_URL` within compose network.
- DB fallback policy (`core/db_fallback.py`) unchanged: SQLite used when Postgres unavailable or explicitly configured for dev/test.
- Health checks use `/health/db` for readiness; `DATABASE_URL` is required for production.

---

## 1. How to start Postgres

```bash
cd /srv/pulseplate-production
docker compose up -d postgres
docker compose ps
docker compose exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

---

## 2. How to apply migrations

```bash
docker compose run --rm pulseplate alembic upgrade head
```

---

## 3. How to start the application

```bash
docker compose up -d pulseplate redis
curl http://127.0.0.1:8000/health/db
curl http://127.0.0.1:8000/ready
```

---

## 4. Backup and restore

**Backup:**

```bash
POSTGRES_USER=... POSTGRES_DB=... scripts/ops/postgres_backup.sh
```

**Restore:**

```bash
POSTGRES_USER=... POSTGRES_DB=... scripts/ops/postgres_restore.sh /absolute/path/to/file.dump
```

---

## 5. Environment contract

Required for production:

- `POSTGRES_DB` — database name
- `POSTGRES_USER` — database user
- `POSTGRES_PASSWORD` — strong password (no dev fallback)
- `DATABASE_URL` — format `postgresql+psycopg://<user>:<password>@postgres:5432/<dbname>`

See `.env.example` for the canonical contract.
