# Food Database Update Worker

Production and staging use one dedicated scheduler worker. The FastAPI
processes do not own the periodic loop, so increasing API worker count does not
multiply automatic update attempts.

## Runtime modes

`FOOD_UPDATE_SCHEDULER_MODE` accepts exact values only:

| Mode | Automatic owner | Allowed runtime |
|---|---|---|
| `external` | Dedicated worker | Production, staging, or development with PostgreSQL |
| `in_process_dev` | One development API process | Explicit non-production development/test only |
| `disabled` | None | Any runtime; production/staging still require PostgreSQL |

If the variable is absent, an explicit non-production development/test runtime
uses `in_process_dev`; all other runtimes resolve to `external`. Empty,
whitespace-padded, aliased, or unknown values fail closed. Production and
staging always reject `in_process_dev`.

## Canonical deployment

The production and staging Compose files take the exact mode from the protected
deployment `.env` (default `external`) and define a no-ingress service named
`worker`:

```bash
python -m core.food_apis.scheduler --serve
```

The deploy scripts pull the worker from the exact backend image, stop the
previous worker before any managed backup or migration, wait for the API to
become ready, then start and prove the worker process is still running. The API
and worker mount the same named `food_db_cache` volume. This is intentionally a
single-host topology.

`--serve` requires `external` mode and PostgreSQL. Startup rejects invalid mode
or database configuration before the periodic loop begins.

## Explicit one-shot operation

An operator or external job scheduler may request one leased due-check:

```bash
python -m core.food_apis.scheduler --once
```

`--once` is allowed in `external` and `disabled` modes and rejected in
`in_process_dev`. Exit code `0` means the leased attempt completed, was not yet
due, or observed definite lock contention; it is not proof that source data
changed. Exit code `1` means the attempt or lease failed, and `2` means the
runtime configuration was invalid.

The legacy `scripts/schedule_food_db_update.py` entrypoint is retained only for
offline/manual compatibility. Do not schedule it against the live shared cache
or run it concurrently with the canonical worker.

## Coordination guarantee and limits

Scheduled checks, `--once`, and admin force-update use one canonical
attempt-scoped lease. With PostgreSQL, acquisition, the complete update body,
and unlock use the same dedicated database session and a stable 64-bit advisory
key. Definite contention returns `409 update_already_in_progress` from admin
force-update. Unknown acquisition or release state fails closed and invalidates
the connection.

This prevents concurrent guarded bodies only among cooperating processes using
the same PostgreSQL database and advisory key while the lock session is valid.
It does not provide exactly-once execution, durable leadership, fencing,
fairness, multi-host file-cache coherence, or a worker health claim.

## Rollback and recovery

For an immediate automatic-update stop, stop the `worker` service while leaving
the API in `external` mode:

```bash
docker compose stop worker
```

For a durable no-automatic-update deployment, set the unquoted exact value
`FOOD_UPDATE_SCHEDULER_MODE=disabled` in the protected deployment `.env` and
redeploy. The deploy preflight rejects empty, aliased, or `in_process_dev`
values, starts the API in disabled mode, and leaves the worker stopped. Admin or
explicit `--once` operations remain lease-protected. To roll back the release,
deploy the previous attested backend/Compose bundle.
`DISABLE_BACKGROUND_UPDATES` controls only the legacy `in_process_dev` startup
path and is not an external-worker kill switch.

After recovery, confirm the configured mode, PostgreSQL connectivity, API
readiness, and worker process state before re-enabling automatic updates.
