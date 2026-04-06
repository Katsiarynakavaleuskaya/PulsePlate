# Postgres on Droplet: production database lanes

**Evidence (compose):** `deploy/docker-compose.production.yaml:22` (managed `DATABASE_URL`), `deploy/docker-compose.production.selfhosted.yaml:1` (colocated Postgres).

## Lane A — Managed PostgreSQL (default production)

- **Compose:** `deploy/docker-compose.production.yaml`
- **Contract:** `app` uses an external instance via `DATABASE_URL` only (no `postgres` service in that file).
- **Operator flow:** provision managed Postgres (snapshots / PITR per provider), set `DATABASE_URL` in `deploy/.env`, then bring up `app` + `caddy`.

```bash
# From repo root (after deploy/.env is populated)
docker compose --project-directory deploy -f deploy/docker-compose.production.yaml config
docker compose --project-directory deploy -f deploy/docker-compose.production.yaml up -d
```

Health via the edge (after DNS/TLS):

- Liveness: `GET /health` (must stay DB-free)
- Readiness: `GET /ready` (may be 503 when DB is down)

## Lane B — Self-hosted Postgres on the same Droplet

- **Compose:** `deploy/docker-compose.production.selfhosted.yaml`
- **Contract:** internal `postgres` service (no host-published `5432`), `app` has `depends_on: postgres` with `condition: service_healthy`, `DATABASE_URL` must target `@postgres:5432` inside the compose network.
- **Security:** keep Postgres off the public internet; rely on Docker network isolation and host firewall.

```bash
# From repo root (after deploy/.env is populated — see .env.example for keys)
docker compose --project-directory deploy -f deploy/docker-compose.production.selfhosted.yaml config
docker compose --project-directory deploy -f deploy/docker-compose.production.selfhosted.yaml up -d
docker compose --project-directory deploy -f deploy/docker-compose.production.selfhosted.yaml ps
docker compose --project-directory deploy -f deploy/docker-compose.production.selfhosted.yaml exec postgres \
  pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

### Migrations (both lanes)

Run Alembic in a one-off `app` container (same compose file as the running stack):

```bash
docker compose --project-directory deploy -f deploy/docker-compose.production.selfhosted.yaml run --rm app alembic upgrade head
```

Swap the `-f` path when using the managed stack.

### Caddy image build (self-hosted lane)

The `caddy` service builds from `frontend/Dockerfile.caddy-spa` (context `frontend/`). From repo root:

```bash
docker compose --project-directory deploy -f deploy/docker-compose.production.selfhosted.yaml build caddy
```

### Backup and restore

**Host backup script** (calls `docker compose exec` — run on the Droplet, not inside a container):

```bash
PROJECT_DIR=/srv/pulseplate/deploy \
COMPOSE_FILE=docker-compose.production.selfhosted.yaml \
POSTGRES_USER=... POSTGRES_DB=... \
  /srv/pulseplate/scripts/ops/postgres_backup.sh
```

**Restore** (operator adjusts paths and dump file):

```bash
POSTGRES_USER=... POSTGRES_DB=... scripts/ops/postgres_restore.sh /absolute/path/to/file.dump
```

**Scheduled backups:** examples under `deploy/systemd/pulseplate-postgres-backup.service.example` and `deploy/systemd/pulseplate-postgres-backup.timer.example` (install to `/etc/systemd/system/` and adjust `WorkingDirectory` / paths).

### Environment contract

Required keys and semantics live in **`.env.example`** (`DATABASE_URL`, `POSTGRES_*`, `IMAGE_REF`, `PRODUCTION_DOMAIN`, etc.). Do not copy live credentials into runbooks.

### Extension: `pg_trgm` (search candidates)

Alembic revision `alembic/versions/202604060001_enable_pg_trgm_foods_candidate_indexes.py` runs `CREATE EXTENSION IF NOT EXISTS pg_trgm` when supported.

**Managed providers:** enable `pg_trgm` in the control plane if migrations fail on privilege.

**Evidence / design:** `docs/architecture/ADR_SEARCH_PGTRGM_CANDIDATES_LANE_P2.md`, `app/services/food_store.py:603` (`_load_semantic_candidates`).

**Follow-up (P2):** `docs/roadmap/BACKLOG_LEDGER.md` anchor `ledger-p2-search-zero-downtime-swap-orchestration`.

### Production DB invariant (repo policy)

Paid runtime, subscriptions, entitlement state, and client history must not ship on SQLite as canonical production storage. SQLite remains for local development, tests, and documented fallback paths.

See: `AGENTS.md` (Production DB invariant), `core/db_fallback.py`.
