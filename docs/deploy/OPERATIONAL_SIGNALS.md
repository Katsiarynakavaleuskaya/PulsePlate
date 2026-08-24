# Operational Signals

Canonical operator runbook for PulsePlate health, private Prometheus activation,
premium-alias evidence, and non-destructive telemetry rollback.

Repository merge, host synchronization, secret bootstrap, private staging,
production release authorization, production deployment, baseline eligibility,
human `T₀`, the 30-day evidence decision, alias retirement, and TSDB deletion are
separate states. Evidence from one state never authorizes another.

## Runtime probes

| Surface | Purpose | Expected behavior | Source of truth |
| --- | --- | --- | --- |
| `/health` | Liveness | Always `200`; does not depend on the DB | `app/routers/health.py`, `app/main.py`, `app/AGENTS.md` |
| `/health/db` | DB readiness | `200` when DB is reachable, `503` otherwise | `app/routers/health.py`, `app/main.py`, `app/AGENTS.md` |
| `/ready` | Readiness alias | Same behavior as `/health/db`; hidden from OpenAPI | `app/routers/health.py`, `app/main.py`, `app/AGENTS.md` |
| `/api/v1/health` | Compatibility alias | Mirrors `/health` payload | `app/routers/health.py`, `app/main.py` |
| `/debug_env` | Local/operator debug surface | Limited output only when debug/operator access is enabled | `app/routers/admin_operations.py`, `app/services/admin_operations.py` |

Use `/health` for liveness and `/ready` or `/health/db` for
dependency-aware readiness.

## Metrics and private Prometheus contour

- Application surface: private `GET /metrics`, hidden from OpenAPI.
- Application registration: `app.main` calls `register_metrics(app)`.
- Authentication header: `X-API-Key`.
- Dedicated file credential:
  `/run/secrets/pulseplate_metrics_scrape_key`.
- Existing valid application keys remain compatible with `/metrics`; the
  dedicated metrics key cannot authorize another protected endpoint.
- Prometheus job: `pulseplate-api`.
- Exact target: `app:8000/metrics`.
- Scrape interval and timeout: `30s` and `10s`.
- Retention: `45d`, carried only by
  `--storage.tsdb.retention.time=45d` because the merged verifier recognizes
  that exact argument. The flag is supported but deprecated; any future move
  to the Prometheus v3 configuration field must update and merge the verifier
  contract first.
- TSDB: named `prometheus_data` volume mounted at `/prometheus`.
- Network: private Docker `observability` network with `internal: true`.
- Public exposure: no host port, no Caddy route, no remote write, and no
  lifecycle/admin API.
- Failure direction: the app never depends on Prometheus. Prometheus failure
  makes telemetry and `T₀` eligibility `HOLD`; it must not take down app or
  Caddy.

The three repository contours must keep the same Prometheus projection:

- `deploy/docker-compose.staging.yaml`
- `deploy/docker-compose.production.yaml`
- `deploy/docker-compose.production.selfhosted.yaml`

Managed versus colocated PostgreSQL remains product-topology truth. Runner
transport such as `PROD_DEPLOY_MODE=self-hosted` does not select a database
contour. Only an exact canonical `COMPOSE_FILE` does so.

## Host secret contract

The secret is a human-owned server-local artifact. Repository workflows and
deploy scripts never create, rotate, print, shell-source, archive, or delete
its value.

Before activation, the account that runs Docker Compose must verify:

- the `secrets` directory is owned by that account, is a real non-symlink
  directory, and has mode `0700`;
- `secrets/pulseplate_metrics_scrape_key` is owned by that account, is a real
  non-symlink regular file, and has mode `0444`;
- the file contains one 32-256 byte printable non-whitespace ASCII token with
  no newline;
- the token differs from `API_KEY`;
- only `app` and `prometheus` receive the file mount.

The `0444` leaf is intentional: the parent directory restricts host access,
while two different non-root container identities must read the same
read-only bind mount. Rotation is a human-owned atomic replacement. Never
include the value in `.env`, Prometheus YAML, command output, logs, evidence,
or support messages.

## Repository validation is not activation

The repository contour may establish:

- exact image/tag/index/platform-manifest binding;
- suppression-free image scan results at a recorded scanner snapshot;
- Prometheus syntax;
- normalized Compose structure;
- deterministic deploy ordering and failure behavior.

It cannot establish:

- current host files, filesystem policy, secret presence, or disk capacity;
- the identity or writability of an existing production volume;
- current running images, process count, target continuity, or scrape success;
- production baseline eligibility, `T₀`, 30-day completeness, or retirement
  authority.

No-data, partial data, stale identity, or ambiguous host state is `HOLD`.

## Private staging activation

Private staging is a human infrastructure action after the OBS1B repository
change is merged. It never starts the production clock.

1. Keep `STAGING_ATTESTED_DIGEST_READY=false` while synchronizing the exact
   merged `deploy.sh`, staging Compose, Prometheus config, image manifest,
   Caddyfile, and backup helper.
2. Create the server-local secret directory and file under the frozen host
   permission contract without exposing the token.
3. Record the merged application SHA, backend image, Caddy image, Prometheus
   runtime image, normalized Compose identity, config hash, manifest hash, and
   intended named volume.
4. Run the contract-v3 preflight. It must reject invalid metadata, config,
   manifest, architecture, or canonical application invariants before worker,
   database, app, or Caddy mutation.
5. Only after the exact host contracts and secret/bootstrap checks are
   complete may the human re-enable `STAGING_ATTESTED_DIGEST_READY`.
6. Run the separately authorized staging deploy. Product migration, app,
   worker, Caddy, and external readiness complete before Prometheus starts.
7. Run canonical BMR and gaps API smoke plus Web Nutrition Setup smoke.
8. Create a private mode-`0700` staging evidence directory and run the
   verifier in `baseline` mode.
9. Preserve the staging receipt as staging-only evidence. Do not author `T₀`.

Use an explicit absolute repository Python selected by the operator:

```bash
REPO_PYTHON="${REPO_PYTHON:?set REPO_PYTHON to the absolute repository interpreter}"
"$REPO_PYTHON" scripts/verify_premium_alias_telemetry.py baseline \
  --compose-file deploy/docker-compose.staging.yaml \
  --evidence-dir "$EVIDENCE_DIR"
```

The verifier resolves Docker through `shutil.which()`, uses argument arrays,
and reaches Prometheus only through `docker compose exec`; it does not require
or authorize a host port.

## Production authorization and baseline

Production requires a separate exact human authorization. Before presenting a
release candidate, collect a fresh host census without changing the host:

- exact Compose path and selected managed or colocated PostgreSQL contour;
- current app, worker, Caddy, and Prometheus images;
- one API container and one Uvicorn process;
- database topology and readiness;
- server-local `.env`, secret metadata, config, and manifest identities;
- existing `prometheus_data` identity, capacity, and free disk;
- exact application release SHA/tag and intended Caddy and Prometheus images.

Only after the human authorizes that exact release may the tag and production
deploy occur. The deploy sequence must remain:

1. validate incoming archive/contracts and host secret metadata;
2. normalize Compose and pull exact images;
3. run exact-image promtool and the canonical `app.main` production invariant;
4. preserve migrations, app, worker, Caddy, and product readiness order;
5. start Prometheus last and require both promtool ready and healthy checks.

If Prometheus fails, the deploy returns a telemetry failure while the proven
product remains running. That failure is not permission to delete or recreate
the TSDB.

After canonical API and Web smoke, run the production baseline:

```bash
REPO_PYTHON="${REPO_PYTHON:?set REPO_PYTHON to the absolute repository interpreter}"
"$REPO_PYTHON" scripts/verify_premium_alias_telemetry.py baseline \
  --compose-file deploy/docker-compose.production.yaml \
  --evidence-dir "$EVIDENCE_DIR"
```

Use the exact self-hosted Compose path only when that database topology was
explicitly selected and authorized.

## Human-authored T0

The verifier reports eligibility but never selects or writes `T₀`. A human
records:

```text
T₀ = max(
  production_deploy_success,
  canonical_API_and_Web_smoke_success,
  first_successful_Prometheus_scrape,
  four_numeric_alias_baselines_confirmed
)
```

All four alias series must be present, finite, numeric, and attributable to the
exact one-container/one-process production topology. Missing or malformed data
is `HOLD`, not zero.

## Daily checkpoint

Run one checkpoint per UTC calendar day. This repository contour adds no
production scheduler; invocation remains operator-owned unless a separate host
scheduler is explicitly authorized.

```bash
REPO_PYTHON="${REPO_PYTHON:?set REPO_PYTHON to the absolute repository interpreter}"
"$REPO_PYTHON" scripts/verify_premium_alias_telemetry.py checkpoint \
  --compose-file deploy/docker-compose.production.yaml \
  --evidence-dir "$EVIDENCE_DIR" \
  --baseline-evidence "$BASELINE_EVIDENCE"
```

A missing daily receipt requires investigation. It does not itself determine
the final disposition and never changes `T₀`; the final decision requires the
complete TSDB range proof.

## Final 30-day evidence

Evaluate only at `T₁ >= T₀ + 30 x 24h`:

```bash
REPO_PYTHON="${REPO_PYTHON:?set REPO_PYTHON to the absolute repository interpreter}"
"$REPO_PYTHON" scripts/verify_premium_alias_telemetry.py final \
  --compose-file deploy/docker-compose.production.yaml \
  --evidence-dir "$EVIDENCE_DIR" \
  --baseline-evidence "$BASELINE_EVIDENCE" \
  --t0 "$HUMAN_APPROVED_T0"
```

For every exact versioned alias, the final proof requires:

- finite `sum(increase(http_requests_total{method="POST",route="<path>"}[30d]))`
  exactly equal to numeric zero, without a status filter and without
  `or vector(0)`;
- exactly one `pulseplate-api` target;
- `min_over_time(up{job="pulseplate-api"}[30d]) = 1`;
- at least `86400` `up` samples for a 30-second interval;
- unchanged app and Prometheus image identities, Prometheus config hash,
  `prometheus_data` identity, and one-container/one-process topology;
- retention at least 45 days and no known supported consumer.

Empty vectors, gaps, `up=0`, insufficient samples, drift, `NaN`, infinity,
negative values, or any positive alias hit produce `HOLD`. A positive hit does
not automatically restart the clock; a human must first classify the consumer.

Only a separate future PR may remove all and only the four versioned aliases.
Root aliases remain a separate auth and consumer lane.

## Rollback

For a Prometheus-only failure:

1. keep or restore the proven app and Caddy release;
2. stop or roll back only the Prometheus contour through a separately
   authorized human host action;
3. preserve `prometheus_data`, evidence receipts, config/manifest identities,
   and the dedicated secret grant until evidence disposition;
4. mark any existing `T₀` invalid;
5. require a new baseline before a future observation window.

Never run `down -v`, remove or prune `prometheus_data`, delete evidence, rotate
or delete the secret, remove aliases, or substitute an image as an automatic
rollback. Destructive TSDB cleanup requires separate exact human authorization.

## Existing tracing and request telemetry

`app.main` also registers request telemetry and OpenTelemetry tracing. These
in-process hooks remain separate from the private Prometheus retention
contour. Centralized error reporting remains follow-up work; its absence does
not mean health, metrics, tracing, or request telemetry are absent.
