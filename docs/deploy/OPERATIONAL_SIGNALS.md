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

### Alias and target rule activation (OBS2A PR1)

`deploy/prometheus/alias-alerts.yml` is the exact rule source. The three Compose
contours mount it read-only beside `prometheus.yml`; staging and production
deployment admit the file before product mutation. The pinned Prometheus image
must pass full `promtool check config` and `promtool check rules`, and CI runs
`promtool test rules` on `alias-alerts.test.yml`. The staging CD fingerprint
checks the rule hash in both remote passes, while the production shell archive
has an explicit file allowlist and a symlink-safe publication transaction.

Rules distinguish the exact `pulseplate-api` / `app:8000` target being absent
for 2 minutes, down for 2 minutes, or healthy while any specific seeded
`status="200"` POST series for `bmr`, `targets`, `plate`, or `gaps` is missing
for 5 minutes. A separate diagnostic alert reports a sampled any-status POST
counter increase in the last 15 minutes or a newly observed positive series;
an old steady positive cumulative value expires and does not keep it firing.
Temporary disappearance and reappearance of a positive series can also be
diagnostic, so this alert alone does not prove a request happened in-window.
Missing series is not zero. These rules do not determine baseline eligibility,
start `T₀`, authorize alias removal, or send email until the separately reviewed
Alertmanager lane is activated and actual delivery is verified.

For a monitoring-only host change, take a fresh Compose/secret/TSDB census,
verify the admitted file hashes and native rules, then recreate only the
Prometheus service while preserving `prometheus_data`. The general staging
`deploy.sh` path includes application and database operations and is not the
monitoring-only activation command. Preserve the previous baseline evidence
and create a new epoch after the config change; leave eligibility `HOLD` when
any exact series is absent or positive. No rule-file merge alone proves that
the host loaded the new rules.

### Optional Alertmanager email routing (OBS2A PR2)

The three Compose contours declare the `alerting` profile, which remains off
for ordinary app and metrics startup. Its official Alertmanager v0.34.1
linux/amd64 image is pinned by platform digest in the Compose files. The
service has no host port or Caddy route, runs as UID 65534 with a read-only
root, dropped capabilities, a 16 MiB temporary store, and no cluster listener.
Prometheus and Alertmanager share only the internal `alerting` network;
Alertmanager alone also joins `smtp-egress`. Its explicit gateway priority 2
exceeds the internal `alerting` attachment's priority 1, making SMTP egress
the default route. That bridge permits outbound networking and is not a
firewall restricting traffic to Resend. The installed Compose host must retain
both priority values in its normalized config before activation.

Prometheus sets the literal `staging` or `production` external `environment`
label, and drops the same name from scraped metric labels before ingestion.
Deploy admission rejects a missing, duplicate, crossed or shadowed contour
label. Existing seven target and alias rules retain their exact expressions
and send to the private `alertmanager:9093` target. The Resend route uses
`smtp.resend.com:2465` with implicit TLS, sender
`alerts@alerts.pulseplate.app`, recipient `pulseplate@pm.me`, a 30-second
group wait, five-minute group interval and 24-hour repeat interval. Resolved
messages are disabled. A restart loses temporary Alertmanager deduplication
state and may produce a duplicate notification.

Only a deliberately selected `alerting` profile requires the server-local
`secrets/alertmanager_smtp_key`, mounted only into Alertmanager at
`/run/secrets/alertmanager_smtp_key`. The file must be regular, non-symlink,
owned by the Compose account and mode `0444` under its mode-`0700` secrets
directory. Compose bind mounts do not remap file ownership; this lets runtime
UID 65534 read the key without granting the app or Prometheus the mount.
Create a Resend Free account, verify only `alerts.pulseplate.app`, and place
the separate SMTP key directly on the host; never place its value in Git,
logs, chat or Drive. Repository merge does not create the key or select the
profile. The exception for the exact bundled gRPC finding is recorded in
`docs/security/CVE-2026-84445-alertmanager.md`; a suppressed scan is not a
clean scan.

Keep `MERGED_REPO`, `MAIN_VERIFIED`, `HOST_ACTIVATED`, received Prometheus
email, received checkpoint-failure email and scheduled checkpoint as separate
evidence states. After both OBS2A PR2 and PR3 merge, conduct a fresh host
census and a separately authorized monitoring-only activation. Verify the
Compose project, current image/config hashes, actual SMTP 2465 reachability,
`alias-alerts.yml`, protected secret metadata and the existing
`prometheus_data` mount before changing any monitoring service. Save the old
config and hashes for rollback; preserve the TSDB, app, DB and #2404 receipts.
After a Prometheus config change, create a new baseline epoch. Test email
delivery with disposable Prometheus data and a separate checkpoint test
baseline; an accepted Alertmanager API call is not proof of mailbox receipt.
On failure, disable only the new profile/timer and restore the verified
previous Prometheus config. Do not run the general staging `deploy.sh` as a
monitoring-only activation or infer production `T₀` from staging evidence.
If a production contract publication stops between file replacements, treat
the mixed installed files as `HOLD`: the direct-host preflight rejects an
Alertmanager config or ignore that differs from the admitted contract. Preserve
app, DB and TSDB, then replay only the complete CI bundle through the existing
safe publication transaction and rerun preflight. Never repair one file by an
unverified manual copy or infer that a partly published bundle activated mail.

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
The setup exports its dedicated `DOCKER_CONFIG` before the first login/Buildx
operation and carries that same path to later steps. Scout source-provenance
verification uses step-local `DOCKER_SCOUT_HUB_USER` and
`DOCKER_SCOUT_HUB_PASSWORD` from the existing DHI credential pair; a registry
login is not proof of Scout backend authentication. Cleanup retains the owned
configuration, exact current-run resource identities and per-slot direct-child
temporary directories. Query failure remains distinct from confirmed absence.

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
   For the external scheduler, worker acceptance is a bounded native Docker
   running/identity check because its Compose healthcheck is disabled. One
   `up -d --pull never --no-deps worker` precedes Caddy; the same app/worker
   generation is observed again after HTTPS `/ready`, without a second `up`.
   `Running=true` and numeric `ExitCode=0` do not prove a scheduler cycle or
   alert delivery. A failed gate is `HOLD`, and a post-Caddy failure may leave
   partial host state; any recovery needs a new operator decision.
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


## Offline operational context report (OPS-01)

Run from the repository checkout:

```bash
python scripts/ops/ops_context_report.py --environment production --format json
python scripts/ops/ops_context_report.py --environment staging --service database --format json
python scripts/ops/ops_context_report.py --environment production --service database --observed artifacts/ops-observed.json --max-observation-age-seconds 3600 --format json
```

The stdlib CLI reads local files and one fixed read-only Git commit identity query. Git is
resolved only through the fixed POSIX system search path `/usr/bin:/bin`; caller PATH
cannot supply it and no user-path fallback is supported. The OS-managed directories and
their platform-managed symlink targets are trusted assumptions, not executable authenticity
proof. Missing system Git fails safely. Native Git resolves `HEAD^{commit}`; a blob, tree
or missing commit cannot become repo identity. This does not prove authorship, a clean
worktree or deployed revision. The CLI does
not contact providers, inspect running containers, evaluate configuration, read environment
credentials, or execute runbook commands. `--sources` defaults to
`docs/deploy/OPS_CONTEXT_SOURCES.json`; a canonical repository-relative alternate JSON index
is supported. Absolute paths, including paths inside the checkout, traversal, noncanonical
paths and unsafe filesystem objects are rejected. Static source policy is applied before
reading the index or any indexed member. Local observations remain separate from static
context and may use an explicit repository-relative artifact path. For index, member and
observation paths, any ancestor directory component equal to `secrets` after case folding
is denied before acquisition. All indexed member paths are checked before selection.
Static filename/suffix exclusions apply to the index and members; observations retain
their separate dynamic path policy. Callers must sanitize indexes, observations and custom
sources: the tool cannot detect confidential content under otherwise permitted names,
and a permitted content fingerprint is not inherently safe to publish.

The index is a reference catalogue: root keys are `schema_version` (exactly
`ops-context-sources.v1`) and `sources`. Each source has exactly `environment`, `service`,
`configuration` and `path`. Both environments and all four services must be represented;
no duplicate row is admitted. Production configuration labels are `managed_default`,
`selfhosted_alternative` or `shared`; staging uses `staging` or `shared`.
Production app, database and prometheus each require both `managed_default` and
`selfhosted_alternative` reference classes; `shared` cannot replace either class.
Every staging service requires its `staging` reference class; `shared` cannot substitute.
Production packages retains its existing grammar without a dual-class requirement.
These ten named relations and eight environment/service bindings are required for the whole
index before report selection, including alternate indexes; they neither require distinct
source paths nor verify live topology. Labels describe reference relationships.
Canonical production instructions remain in `deploy/PRODUCTION.md`,
staging in `docs/deploy/STAGING.md`; deployment configuration and package/image owners
retain their own truth. Production managed PostgreSQL is the documented default;
self-hosted PostgreSQL is a maintained alternative. `PROD_DEPLOY_MODE` describes a deployment
transport choice and cannot select database topology in this report. The staging database
references include the mounted PostgreSQL HBA access-policy file; the production local-image
manifest belongs to the self-hosted alternative. App references include the selected
environment's Caddy policy. The finite mounted-policy catalogue covers these two Caddy
files, staging HBA and Prometheus YAML, not arbitrary application or cloud policy. Existing
prohibited static source classes and designated secrets directories are denied before
acquisition; this is a finite path policy, not content-based secret detection. Named-volume
and provider state remain unknown. None of these references proves host activation.

A supplied observation file has this closed shape (synthetic example only):

```json
{
  "schema_version": "ops-observed.v1",
  "observations": [
    {
      "environment": "production",
      "service": "database",
      "resource_id": "synthetic-db-1",
      "provenance": "operator_entry",
      "observed_at": "2026-09-14T12:00:00Z",
      "repo_sha": null,
      "selected_config": "managed_default"
    }
  ]
}
```

All record fields above are required except `selected_config`. Provenance is only
`operator_entry` or `provider_export`, both supplied claims. Resource identifiers are
1–128 ASCII letters/digits/dots/underscores/hyphens, starting with a letter or digit.
This syntax cannot recognize every secret; sanitize identifiers before supplying them and
keep reports local. Do not paste private identifiers or their hashes into public evidence.
There are no fields for logs, command output, URLs, DSNs, credentials or unrestricted text.
Revision is null or a lowercase 40-character Git SHA. Timestamps use exact UTC
`YYYY-MM-DDTHH:MM:SSZ` syntax and cannot be in the future. Input JSON is limited to 64 KiB,
128 records, six nesting levels and 512 characters per string; duplicate keys, nonfinite
numbers, unknown fields and non-ASCII/control strings fail. Every record is validated
before environment/service filtering. An observation window must be a positive integer in seconds. Age equal to the window is fresh; greater age is stale.
The report records the evaluation time and window. Freshness is not authentication.

The versioned report separates acquired source-byte SHA-256 fingerprints, repository SHA,
supplied observations, literal `revision_match`, freshness, unknown live identity and
same-environment/service conflicts. SHA equality does not verify dirty-file contents or
live configuration; acquired source fingerprints cover actual bytes without claiming an
atomic repository snapshot. A missing revision gives null equality; a differing revision
gives false. Both retain unknown live identity. Two different resource IDs or selected
configuration claims remain conflicting even across maintained alternatives, stale records
or mismatched revisions. No preferred record or automatic winner is selected. Identical
records retain multiplicity and provide no independent corroboration. A conflict describes
supplied bindings, not a broken live topology or authority to remove a resource.

Without observations, useful selected references remain and live identity stays unknown.
Unknowns and conflicts produce a report with exit 0. Invalid selectors, malformed inputs,
unsafe or missing selected sources and Git identity failures produce exit 2, a fixed
sanitized diagnostic and no partial JSON report. Valid output may contain supplied IDs;
this is not universal data-loss prevention. No output asserts health, readiness, provider
authenticity, configuration verification or deployment permission.

The operator role context map loads the finite static catalogue for both environments and
production alternatives through the existing occurrence-selected bridge. This cold-start
context delivery is separate from report selection and grants no authority to execute
embedded commands. Local observations never become reusable role context.

Keep progress receipts separate: `MERGED_REPO` needs a merge receipt, `MAIN_VERIFIED` needs
observed merged-main checks, `HOST_ACTIVATED` needs separately authorized host evidence,
and `ALERT_DELIVERY_TESTED` needs a separately authorized delivery test. OPS-01 implements
only the offline reference/report surface. OPS-02 DB lifecycle regression repair with a real-function reproducer and caller coverage,
OPS-03 minimal host/DB/service observability with tested human alert delivery, and OPS-04
measured storage/FinOps preserving recovery requirements remain separate backlog-governed lanes.

## One-shot staging runtime diagnostic (OPS-03A)

After the owning PR is merged and staging access is authenticated, run one
bounded read-only check from the operator machine:

```bash
SSH_HOST_STAGING=<authenticated-staging-address> \
  python scripts/ops/staging_runtime_diagnostics.py --environment staging --format json
```

The CLI uses the dedicated `pulseplate-ops` key and known-hosts record named
in `docs/deploy/STAGING.md`. The fixed SSH probe calls the installed full
`check_staging_security.py` on the selected all-profile Compose render, then
requires one running, non-one-off `app` and `postgres` under exact staging
Compose labels. The installed staging Compose source must match the exact
reviewed SHA-256, and a controlled process environment pins the backend and
Caddy references to the attested merge. This rejects a stale host `.env` image
reference without reading it as image authority. The probe keeps the bounded
resolved Compose JSON in memory, verifies its stdin roundtrip, and compares
resolved app/PostgreSQL hashes with the selected container labels. PostgreSQL
also requires native `config --hash` equality. For the app, the native hash may
differ because [docker/compose#14001](https://github.com/docker/compose/issues/14001)
omits service `env_file` values on affected versions; the exact pinned Compose
source witnesses that app-only exception. It compares container ID, image ID,
configured image and start time, then rerenders, roundtrips and recomputes all
four hashes after the app probe. Any source, model, hash or generation change
fails closed. From the selected app container it requests
`/health` and `/ready` separately with redirects and ambient proxies disabled
and opens a short-lived PostgreSQL read-only session with the existing CA and
passfile under `sslmode=verify-full`. Ambient libpq overrides fail closed before
connection. Only fixed queries observe database/role,
server version, recovery, own-session TLS and aggregate activity when visible.
Limited role visibility is `unknown`, never a fabricated zero.

The JSON schema is `pulseplate.staging-runtime-diagnostics.v1`: UTC
`observation_window.started_at` is captured immediately before SSH and
`observation_window.completed_at` immediately after its response. `observed_at`
equals completion; it does not imply every HTTP/DB fact was sampled at that
instant. The report also records `environment=staging`, bounded `scope`, a SHA-256 object
fingerprint, `status`, separate `http` and `database` facts, `unknowns` and
coded `errors`. `complete` means a complete observation, not service health;
`degraded` means an observed HTTP or DB failure; `partial` means visibility was
limited. Valid measured degradation exits 0. Invalid CLI input exits 2.
Transport, receipt, object selection, DB/role/TLS identity mismatch, malformed
native output or container generation drift exits 3 without a JSON success
report. No raw Compose environment, DSN, password, SQL, client address or
native stderr is published.

Store detailed sanitized evidence only in a separately permission-checked
owner-only archive. The shared INFRA plan/capsule and Execution Tracker may
carry sanitized outcome status and links, not the diagnostic archive: their
current sharing grants writer access to anyone with the link. A staging
observation does not establish alert delivery, production readiness, release
authority or completion of broader OPS-03/OPS-04 work.

## DB engine lifecycle (OPS-02)

`core.db` identifies a configured connection by its complete parsed SQLAlchemy URL,
including credentials and query parameters (`core/db.py:359`,
`tests/test_db_engine_reuse_diff_coverage.py:204`). The sync getter and `init_db()`
publish an engine with its bound factory as one generation (`core/db.py:359`,
`core/db.py:1050`). `init_db()` prepares the candidate schema before publication;
failure preserves the prior generation (`core/db.py:1050`,
`tests/test_db_engine_reuse_diff_coverage.py:744`).
An explicit `init_db(database_url=...)` selection remains current for session
factory acquisition until a later engine selection (`core/db.py:409`,
`tests/test_db_engine_reuse_diff_coverage.py:292`). The local/dev fallback
publishes its URL and generation under the same lifecycle lock for participating
accessors (`core/db_fallback.py:125`, `tests/test_app_db_fallback_97.py:229`);
independent reads of module globals or `os.environ` are not atomic snapshots.
Degraded markers follow the selected fallback generation (`core/db_fallback.py:340`,
`tests/test_app_db_fallback_97.py:294`). Ambient selectors are rechecked before
publishing a prepared engine (`core/db.py:1050`). Async acquisition returns one
engine/factory snapshot; cancellation waits for owned async disposal to finish
before it propagates (`core/db.py:690`, `core/db.py:775`). New async sessions
are constructed while the selected generation is validated (`core/db.py:873`,
`tests/test_core_db_comprehensive.py:16`). A fallback candidate must retain its
prior generation and both URL selectors and protect its ordinary SQLite file
through schema preparation and publication (`core/db_fallback.py:246`,
`core/db.py:335`, `tests/test_app_db_fallback_97.py:55`,
`tests/test_app_db_fallback_97.py:119`). Callers still
own already-issued sessions and checked-out connections; pool disposal does
not close them or assert safe live credential rotation. This repository-level
contract adds no host activation, pool policy, or deployment claim.

## Offline resource cost and recovery context (OPS-04A)

The standalone stdlib tool reconciles one supplied DigitalOcean invoice and
explicit resource bindings. It performs no API, Git, subprocess, host, backup,
restore or resource operation (`scripts/ops/resource_cost_report.py:1`).

```bash
VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
"$VENV_PYTHON" scripts/ops/resource_cost_report.py \
  --input-dir "$OWNED_PRIVATE_INPUT_DIR" \
  --invoice invoice-capture.json \
  --bindings resource-bindings.json \
  --format json
```

Select a canonical absolute private directory outside the checkout, mode
`0700`, owned by the invoking user. Select two canonical relative paths beneath
it; acquired files must be regular, single-link, owned by that user and have
permissions no broader than `0600`. At-rest metadata is admitted before leaf
open, and acquired descriptor device/inode must match that observed leaf. Symlinked ancestors/descendants, traversal,
secret-directory paths and nonregular objects fail closed. The tool does not
create output files; the operator owns private stdout redirection. This bounded
descriptor read does not guarantee permanent exclusion of another same-user
process or arbitrary-content secret detection.

The local capture envelope is `pulseplate.do-invoice-capture.v1`, with
`schema_version`, explicit `account_ref`, UTC `captured_at`, supplied
`invoice_kind=preview|final`, native `invoice` and ordered `pages`. Selected
header fields are `invoice_uuid`, `invoice_period=YYYY-MM` and fixed-point
`amount`; native `updated_at` is optional. Each page has `page`, `per_page`
(1–200), and the native `response` with required `invoice_items` and
`meta.total`. Native `links`, `links.pages` and each pagination direction are
optional. Completeness uses declared pages, counts and all supplied ordinals;
present URLs are checked against selected invoice/kind/page/per-page metadata.
Absent links provide no URL witness and imply neither authentication nor
atomicity. Preserve zero/negative and identical legal rows. Amounts are USD strings with at most two fractional digits; floats,
exponents and unsupported precision are refused without rounding. Explicit
non-USD currency on a selected header or row is refused; absence retains this
USD-only native contract without authenticating the supplied bill. Finite numeric optional metadata is decoded as Decimal and remains
uninterpreted; native non-money metadata never calculates prices. Valid escaped
controls in ignored native prose are omitted from output; selected identity,
path and reference fields reject control characters.

Optional `invoice_after` retains a separately acquired second native header.
Absent means `header_observation_status=not_supplied`; equal selected fields
mean `unchanged` only for those fields and optional update presence/value.
Observed valid differences mean `changed`/exit 1; malformed/partial after-header
means exit 2. Never copy the first header to fabricate an observation. Native
pages have no independent account/period/header. A valid but incorrect global
account or period without an independent witness remains undetectable offline.
Equal headers, final kind, hashes and totals do not prove atomicity or provider
authenticity. Legal tax intervals can extend beyond capture time.

The binding envelope is `pulseplate.resource-cost-bindings.v1`, with
`schema_version`, matching `account_ref`, and `bindings`. Each declaration has
`resource_kind`, generic opaque string `resource_id`, `environment`, `service`,
`owner_ref`, `evidence_ref`, `recovery_ref` and `utilization_ref`. Environments
are `production|staging|shared|unknown`; services are
`app|database|prometheus|packages|unknown`. Reference/owner fields are supplied
strings or null, never dereferenced. This does not change OPS-01 enums.

Exact recognized products bind Droplets/Droplet Backups to `droplet` via native
`resource_id`, Droplet Snapshots to `snapshot` via native `resource_id`, and
Volumes/Database Clusters to `volume`/`database_cluster` via native
`resource_uuid`. Binding
`resource_id` holds that kind's exact identifier, including database UUIDs.
Category, names and descriptions do not determine identity or snapshot parent.
Both populated native identity fields remain unresolved. Taxes, Uptime Health
Check and Container Registry Subscription are known non-resource charges only
when native identity is absent; other spellings remain unclassified. Native
product and identity fields are optional: absent/empty product stays
unclassified, absent IDs remain unknown and never become fake identifiers.
Present malformed optional fields are refused; amount remains mandatory. Conflicting
bindings retain their candidates and select no owner.

Four exclusive buckets conserve every supplied page/ordinal: allocated,
unallocated, non-resource and unclassified. Their exact Decimal sum is the
native row total; header minus row total is the explicit residual. Accounting
and allocation are separate: allocation uses row counts, so unbound free rows,
canceling charges or unknown products cannot manufacture completeness. Context
appears once per resource group; rows use short group references. Supplied
recovery is always `not_assessed`; missing utilization remains `unknown`.

Limits are 4 MiB per input, 20 pages, 4,000 rows, 512 bindings and JSON nesting
8. Duplicate keys, nonfinite numbers, malformed Unicode and excess inventories
are refusals, never truncated success. Errors and the fixed `operator_summary`
omit arbitrary supplied prose, identities, references and amounts. The full
machine JSON still contains private context and totals; it is not shareable
merely because provider descriptions were omitted.

Exit 0 means supplied accounting reconciles, even with partial allocation;
exit 1 means a well-read capture/count/header/account discrepancy; exit 2 means
unsafe or invalid input. Literal `authority=none`, `mutation_authority=false`
and `savings_verified=false` preserve the observation boundary. No resource
necessity, restore, health, savings, deployment or merge approval follows.

The single report defines asset type `resource_cost_report`, schema
`pulseplate.resource-cost-report.v1` and policy `resource-cost-policy.v1`.
`upstream_assets` is the ordered invoice-capture/resource-bindings raw SHA-256
pair. The idempotency key hashes the canonical JSON tuple
`[asset_type, schema_version, policy_version, invoice_hash, bindings_hash]`.
The report fingerprint hashes its canonical content excluding only its own
fingerprint field. Encoding is UTF-8, sorted keys, compact comma/colon
separators, ASCII escaping and no nonfinite numbers; the final newline is not
hashed. Identical admitted inputs replay deterministically under that policy;
there is no persistence, cache, deduplication or knowledge promotion. These
hashes do not bind changed implementations or authenticate evidence/ACL/owner.
External exact-material PR evidence owns code identity separately.

OPS-04B is the next separately admitted utilization/recovery evidence candidate.
Parent OPS-04 remains open; resource changes and verified savings require their
own approval and before/after evidence. Upload/readback failure is
`DRIVE_SYNC_PENDING`: preserve sole private originals, with no cleanup until
archive identity, full readback, hashes and extracted members are verified.

## Dated utilization and recovery evidence (OPS-04B)

The offline stdlib companion reads a preserved OPS-04A report and one finite
observations packet (`scripts/ops/resource_evidence_report.py:1`). Acquisition
uses existing separately admitted tools; this CLI performs no network, SSH,
SQL, subprocess, source-text execution or referenced-file reads.

```bash
VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
"$VENV_PYTHON" scripts/ops/resource_evidence_report.py \
  --input-dir "$OWNED_PRIVATE_INPUT_DIR" \
  --cost-report cost-report.json --observations observations.json --format json
```

Use the same owner-private, outside-checkout, mode-0700 root and single-link
regular mode-0600 inputs as OPS-04A. Stdout redirection remains operator-owned.
The unchanged original reader admits both parent walks before leaf reads and
binds acquired descriptors. This is bounded file admission, not permanent
same-user exclusion or arbitrary-content DLP.

### Closed observations grammar

Root keys are exactly `schema_version`, `policy_version`, `asset_type`,
`cost_report_sha256`, `cost_report_fingerprint`, `account_ref`, `assessment_at`,
`assessment_window`, `selected_resource`, `declarations`, `topology`,
`restore_expectations`, and `records`. Their fixed identities are
`pulseplate.resource-observations.v1`, `resource-evidence-policy.v1`, and
`resource_observations`. Both cost hashes are lowercase 64-character SHA-256;
the raw-byte hash and recomputed content fingerprint must independently match.
`selected_resource` contains `resource_kind=droplet` and opaque `resource_id`
and must match an actual cost group. Local `g1`, names, amounts and running
state do not select or associate a resource.

`declarations` uses the existing exact eight-field OPS-04A binding grammar.
Original candidates and reference-only conflicts remain preserved; new owner,
environment or service conflicts select no silent winner. `topology` contains
`epoch_ref`, `root_filesystem_ref`, `volume_ids`, `filesystem_volume_links`.
The first two are strings or null. Volume IDs are a duplicate-free list. Each
link has `filesystem_ref`, `volume_id`, `source_ref`, `source_sha256`; it is an
explicit supplied witness, never inferred from names, mount paths, size or a
sole attachment.

Each `restore_expectations` entry has exactly `target`, `artifact_sha256` and
`target_ref`. The source `target` identifies the Droplet/filesystem/Volume being
assessed; the required bounded literal `target_ref` independently names the
isolated restore destination. It must match receipt `data.target_ref`, and may
differ from source `target.ref`. A receipt cannot establish its own expectation.
Conflicting artifact/destination pairs for one source target select no winner;
identical pairs remain equivalent. A context conflict revokes every positive
association and receipt applicability while preserving raw receipt data/result.

All records have exactly `record_kind`, `account_ref`, `resource_kind`,
`resource_id`, `source_ref`, `source_sha256`, `acquisition_window`,
`observation_window`, `topology_ref`, `target`, `availability`, `reason_code`,
`data`. References are inert strings. Hashes bind supplied bytes, not provider
truth. `target` has `kind` and `ref`; kinds are `droplet`, `root_filesystem`,
`filesystem`, `volume`. A Droplet/Volume target matches its own record identity
before selected-resource association. Known CPU/memory/pressure families require
a Droplet target; filesystem metrics require a root/filesystem target, including
when their unit is unsupported. Other valid records remain unmatched.

Windows are `{started_at, completed_at}` or null for unrecorded acquisition or
observation timing. Observation timestamps use UTC `Z` with at most six fractional
digits; malformed types/timestamps are refused. Equal-time points are valid.
Ordered intervals and samples must not exceed assessment time; own-interval,
future or known topology conflicts remain readable conflicts. The explicit
`assessment_window` has positive duration ending no later than `assessment_at`.
There is no ambient clock, mtime freshness or hidden TTL. Original cost timestamp
and money/reference domains remain unchanged.

`availability=observed` requires typed data and null `reason_code`.
`unavailable|not_acquired` requires null data and one of `PERMISSION_DENIED`,
`HISTORY_NOT_ACQUIRED`, `RECEIPT_NOT_ACQUIRED`, `SOURCE_NOT_ACQUIRED`.
Observed/attempted sources have refs/hashes; a not-acquired source may have null
refs/hashes. An unavailable directory attempt proves no source absence and
cannot be called a confirmed provider-Volume backup source without that witness.

| Record kind | Exact data keys and meaning |
| --- | --- |
| `identity` | `root_filesystem_ref`, `volume_ids`, `backup_ids`; null means unknown, empty array means supplied empty, known conflicts remain visible. Ownership stays in declarations. |
| `metric` | `name`, `unit`, `cadence_seconds`, optional `samples`; absent, null, empty and measured zero remain distinct. Samples have `observed_at`, `value`. |
| `backup_policy` | Boolean `enabled`, `plan=weekly|daily|unknown`; policy configuration only. |
| `backup_object` | `object_kind=backup|snapshot`, `object_id`, `created_at`, `status=available|unavailable|unknown`, `membership_ids`; backup association needs the independent Droplet `identity.backup_ids`, not self-membership. Snapshot parent remains unestablished. |
| `archive_listing` | `artifact_sha256`, `listed_at`, nonnegative `entry_count`; supplied archive listing only. |
| `restore_receipt` | `artifact_sha256`, `target_ref`, `performed_at`, `result=succeeded|failed|unknown`, `checks`; existing scoped supplied operation result, never execution authentication. |

Metric values are nonnegative integers, bounded nonnegative fixed-point decimal
strings or null; bool, floating JSON numbers, exponents and nonfinite values are
refused. Supported counters/bytes/kB require integers; percent requires a decimal
string in 0–100. Cadence is null or a positive fixed-point seconds string.
Strictly ordered sample timestamps and internal cadence gaps remain explicit.
Wide metadata bounds or first/last samples do not prove uninterrupted history
or representative backup/update/build workloads. A current short observation
after the requested historical window remains observed with a history gap.

### Native units, recovery boundaries and limits

Aggregate `/proc/stat` CPU columns use `cpu.user`, `cpu.nice`, `cpu.system`,
`cpu.idle`, `cpu.iowait`, `cpu.irq`, `cpu.softirq`, `cpu.steal`, `cpu.guest`,
`cpu.guest_nice` and unit `USER_HZ`; counters stay unconverted. Do not infer
CPU percentage or reject every iowait decrease. `memory.available|total` use
native `MemAvailable|MemTotal` kB. `filesystem.available|free|size` retain
statvfs bytes and observed filesystem identity. The kernel documents CPU column
semantics and available memory as an estimate. [Linux proc documentation](https://www.kernel.org/doc/html/latest/filesystems/proc.html)

`pressure.<cpu|memory|io>.<some|full>.<avg10|avg60|avg300>` uses percent;
`.total` uses microseconds. Native trend windows remain distinct from acquisition.
System CPU full is undefined compatibility output; its values are preserved as
`unsupported` with `SYSTEM_CPU_FULL_UNDEFINED`, including measured zero.
Unknown metric names/units are unsupported without guessed conversions. [Linux PSI documentation](https://www.kernel.org/doc/html/latest/accounting/psi.html)

Root backup policy/object does not cover attached Volume. Listing does not
establish restore. Receipt `result` and `applicability` are separate: only a
matching current expected artifact and independently expected isolated restore
destination, known matching epoch, performed time within the explicit assessment
window, known acquisition and observation timing, and nonempty checks can yield
`compatible_supplied_scope`. This means supplied scope compatibility, not
validated recovery sufficiency or authentic execution. Missing link, epoch,
artifact, checks or timing stays a gap; historical receipt stays visible as
stale applicability. No aggregate recovery PASS or new restore operation.

Bounds: 4 MiB per input and nesting 8 through the existing reader/parser;
128 records, 512 declarations, 64 membership/link/expectation entries, 32 receipt
check refs, 4,000 samples per metric and across records, 512 characters for
observations packet strings and 64 characters for its decimal tokens. Every
record validates before filtering. Duplicate JSON keys, unsafe files,
unsupported schema versions and
excess inventories are refusals. Old cost money/references retain their original
domain. Complete OPS-04A cost report validation checks original row/group/ordinal
conservation, candidate/allocation rules, delegated counts/totals/status/summary
and source hash/idempotency/fingerprint relationships; it preserves the cost report without
rewriting it. When `INCOMPLETE_CAPTURE` is absent, nonzero rows cover every page
from 1 through `page_count`; nonfinal pages share a width from 1 through 200, and
the final width is from 1 through that width. A complete single page has at most
200 rows; a complete zero-row report has exactly one page. These predicates
recognize a possible complete producer shape; they do not authenticate provider
completeness. Genuine incomplete captures retain their original readable state.

Output asset/schema/policy are `resource_evidence_report`,
`pulseplate.resource-evidence-report.v1`, `resource-evidence-policy.v1`.
Ordered upstream assets bind the actual cost-report and observations raw hashes;
idempotency hashes their canonical asset/schema/policy tuple, and the output
fingerprint excludes only itself. Encoding follows OPS-04A canonical JSON and
newline convention. Identical bytes replay without writes or cache.

Exit 0 means processing with visible gaps, exit 1 a readable binding/context
conflict with no conflicting association, exit 2 constant `INVALID_INPUT`
refusal. Every output includes literal `authority=none`,
`mutation_authority=false`, `savings_verified=false`. Full JSON is private;
fixed operator summary/codes/counts omit identities, amounts, paths and source
prose. No source authenticity, resource necessity, rightsizing, savings,
production or merge authority follows. Rollback is stop invocation or reviewed
bounded revert; servers, data and monitoring are unchanged.

Existing OPS coverage measures all four tools in the same producer/XML/artifact
and existing 97% changed-line consumer. Missing or empty source inventory fails;
application total coverage and actual operational/lifecycle outcomes remain
separate. Keep parent OPS-04 open until its original outcome is proven.
