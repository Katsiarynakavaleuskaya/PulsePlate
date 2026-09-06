# Operational Signals

Canonical operator runbook for PulsePlate health, the immutable local
PostgreSQL plus pgvector contour, private Prometheus activation, premium-alias
evidence, and non-destructive telemetry rollback.

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

## Immutable local PostgreSQL plus pgvector contour

Only private staging and the explicitly selected
`deploy/docker-compose.production.selfhosted.yaml` contour run a local
PostgreSQL service. Managed production continues to use the separately owned
DigitalOcean PostgreSQL database and does not receive this service.

The operator-selected DigitalOcean topology for the later activation is not
host-census evidence: staging runs on its own DigitalOcean droplet; the
production application droplet runs app, Caddy, and private Prometheus through
`deploy/docker-compose.production.yaml`; production PostgreSQL remains a
separate DigitalOcean database resource reached through `DATABASE_URL`.
`production.selfhosted` is a maintained fallback contour, not the selected
production database topology. A fresh read-only host census must still confirm
these identities before any activation or `T₀` claim.

The closed repository record is
`deploy/postgres-pgvector/image-manifest.json`. It binds:

- DHI PostgreSQL `15.19-alpine3.23` runtime and `15.19-alpine3.23-dev` exact
  linux/amd64 platform manifests;
- pgvector `0.8.6` commit/archive SHA-256 and the exact two-stage
  `deploy/postgres-pgvector/Containerfile`;
- the deterministic APK/build/artifact closure and source epoch;
- the derived existing-package GHCR platform/config digest;
- Trivy `0.74.0` `vuln,secret` and `os,library` HIGH/CRITICAL exit-1 scan with
  an empty ignore file and no Rego, VEX, `ignore-unfixed`, or other suppression.

Both local contours keep `postgres_data:/var/lib/postgresql/data`, explicitly
set `PGDATA=/var/lib/postgresql/data`, select `linux/amd64`, and expose no host
port. This preserves the existing volume root while changing the image owner.
The base image default `/var/lib/postgresql/15/data` is evidence, not the
Compose mount contract.

The derived image contains one empty `/var/lib/postgresql/data` directory with
owner `70:70` and mode `0700`. This closes only the fresh named-volume
initialization precondition for the tested Docker engine while preserving the
inherited non-root UID 70 entrypoint. A mounted existing volume hides that
image directory; therefore the layer cannot repair, chown, migrate, inspect,
or prove any existing staging or production volume. Host activation still
requires one exact legacy-or-current image/config identity, UID 70, one exact
`PGDATA`/named-volume target, live PostgreSQL `15.19`, stable container/runtime
identity across the quiesced backup, and a mode-0600 custom dump that
`pg_restore --list` can parse before the old database stops. Any identity,
ownership, receipt, or data drift is `HOLD`, not permission for an automatic
host `chown`, copy, restore, replacement, or deletion.

Pull requests validate only repository contracts and the public pinned
pgvector semantic oracle; they receive no DHI credentials and write no image.
Only the exact trusted `push` to `refs/heads/main` job may use the repository
`DHI_USERNAME` and `DHI_ACCESS_TOKEN`, reproduce the expected digest twice,
scan exact runtime/dev/builder/final images, publish into the existing
`ghcr.io/katsiarynakavaleuskaya/pulseplate` package, attach derived
provenance/SPDX evidence, and verify pullback. That publication still performs
no staging or production deployment.

Docker DHI Community remains the only admitted entitlement and adds no Docker
hosting resource. [Docker's current DHI documentation](https://docs.docker.com/dhi/#community-features)
states that Community core images are free to use, share, and build on under Apache 2.0. Authenticated
GitHub package settings showed the existing `pulseplate` GHCR package as
`public` on 2026-08-27. The exact-main workflow therefore verifies this
existing public owner/name/source/visibility before candidate publication and
after canonical promotion, but never creates a package or changes visibility.
Any terms, entitlement, package identity, or visibility drift is `HOLD`; no
subscription purchase or automatic registry substitution is authorized.
This bounded engineering disposition was rechecked at `2026-08-27T17:41:16Z`
against the [DHI usage guide](https://docs.docker.com/dhi/how-to/use/), the
[Docker Terms effective 2026-08-26](https://www.docker.com/legal/docker-terms-use/),
and Docker's separate [Select/Enterprise mirror contract](https://docs.docker.com/dhi/how-to/mirror/).
The resulting image is a PulsePlate-owned incorporated deployment component,
not an unmodified DHI redistribution, official DHI, Docker-managed mirror,
customized Select/Enterprise artifact, certification, SLA, or support claim.
Preserve inherited notices and upstream PostgreSQL/pgvector attribution; any
terms, tier, source-image, package, or artifact-topology drift returns this
disposition to `HOLD`.

Exact DHI source provenance uses Docker Scout CLI `v1.24.0` from the official
release archive, with its Linux-amd64 SHA-256 and binary build commit pinned in
`.github/workflows/cd.yml`. Each receipt must name the exact runtime or builder
linux/amd64 platform subject. Docker's
[DHI verification guide](https://docs.docker.com/dhi/how-to/verify/) documents
that some DHI attestations lack a public Rekor entry and permits
`--verify --skip-tlog` with Scout `>=1.18.2`; here it means Docker-key signature
verification without transparency-log proof. It is limited to the two frozen
DHI source subjects and is not a Trivy suppression, VEX exception, derived
attestation bypass, or permission to weaken GitHub attestation verification.

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
   merged `deploy.sh`, staging Compose, Prometheus config/image manifest,
   PostgreSQL image manifest, Caddyfile, and backup helper.
2. Create the server-local secret directory and file under the frozen host
   permission contract without exposing the token.
3. Record the merged application SHA, backend image, Caddy image, PostgreSQL
   image, Prometheus runtime image, normalized Compose identity, config hashes,
   both image-manifest hashes, and intended named volumes.
4. Run the contract-v4 preflight. It must reject invalid metadata, config,
   manifest, architecture, PostgreSQL identity/PGDATA/mount drift, or canonical
   application invariants before worker, database, app, or Caddy mutation.
5. Only after the exact host contracts and secret/bootstrap checks are
   complete may the human re-enable `STAGING_ATTESTED_DIGEST_READY`.
6. Run the separately authorized staging deploy. It pulls and inspects the
   exact PostgreSQL image under temporary GHCR credentials, removes those
   credentials, and performs a current-container/image/volume census. For an
   existing database it quiesces worker, Caddy, and app, creates and verifies a
   backup from the still-running healthy old PostgreSQL container, then stops
   it and starts the candidate with `--pull never`. An orphan/ambiguous volume
   is `HOLD`; only proven volume absence is a fresh path. PostgreSQL health,
   migration, app, worker, Caddy, and external readiness complete before
   Prometheus starts.
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
- current app, worker, Caddy, PostgreSQL (when self-hosted), and Prometheus
  images;
- one API container and one Uvicorn process;
- database topology and readiness;
- server-local `.env`, secret metadata, config, Prometheus manifest, and any
  self-hosted PostgreSQL manifest identities;
- existing `prometheus_data` identity, capacity, and free disk;
- exact application release SHA/tag and intended Caddy and Prometheus images.

Only after the human authorizes that exact release may the tag and production
deploy occur. The deploy sequence must remain:

1. validate incoming archive/contracts and host secret metadata;
2. normalize Compose and pull exact images; for self-hosted PostgreSQL, inspect
   its platform/config/labels under temporary GHCR credentials, then remove
   credentials, census the existing container/image/volume, quiesce every
   writer, and verify a pre-transition backup before stopping the old database;
3. start the already-pulled self-hosted candidate only with `--pull never`,
   require PostgreSQL health before any migration, and run
   exact-image promtool plus the canonical `app.main` production invariant;
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

For a PostgreSQL image or migration failure, stop before product traffic
mutation when possible, preserve `postgres_data` and the pre-migration backup,
and record the exact image/config/volume identities. Do not retry with the old
floating image, change `PGDATA`, restore, delete a volume, or patch server-local
files automatically. Restore and destructive database actions require a
separate exact human authorization. A failed or rolled-back staging attempt
cannot establish a production baseline or `T₀`.

## Existing tracing and request telemetry

`app.main` also registers request telemetry and OpenTelemetry tracing. These
in-process hooks remain separate from the private Prometheus retention
contour. Centralized error reporting remains follow-up work; its absence does
not mean health, metrics, tracing, or request telemetry are absent.
