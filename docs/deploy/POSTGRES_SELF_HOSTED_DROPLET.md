# Postgres Self-Hosted Droplet Foundation

> Alternate lane only. Canonical production now uses managed PostgreSQL via external `DATABASE_URL`.
> Keep this document for self-hosted droplet operations, staging experiments, or disaster-recovery drills.

**Purpose:** Self-hosted Postgres reference for PulsePlate on a Droplet. This is no longer the canonical production database baseline.

**Design rationale (architecture):**

- Postgres runs internal-only (no public 5432); app connects via `DATABASE_URL` within compose network.
- Production/staging fail closed on primary DB init errors; SQLite is not an accepted canonical runtime baseline there.
- SQLite fallback remains local/dev/test only.
- Health checks use `/health/db` for readiness; `DATABASE_URL` is required for production/staging.
- Managed PostgreSQL with provider snapshots / PITR is the canonical production path; this document remains the self-hosted alternate.

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
docker compose run --rm app alembic upgrade head
```

---

## 3. How to start the application

```bash
docker compose up -d app caddy
curl http://127.0.0.1/health/db
curl http://127.0.0.1/ready
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
- `DATABASE_URL` — format `postgresql+psycopg://<user>:<password>@<host>:5432/<dbname>`

**DATABASE_URL host modes:**

- **Docker Compose / Droplet:** `@postgres:5432` (service name in compose network)
- **Native local run:** `@localhost:5432` (Postgres on host)

See `.env.example` for the canonical contract.
