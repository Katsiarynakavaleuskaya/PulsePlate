# Agent instructions (scope: deploy/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `deploy/` and below.
- Key files: `deploy/Caddyfile`, `deploy/Caddyfile.production`, `deploy/docker-compose.staging.yaml`,
  `deploy/docker-compose.production.yaml`, `deploy/docker-compose.production.selfhosted.yaml`,
  `deploy/postgres-pgvector/Containerfile`, `deploy/postgres-pgvector/image-manifest.json`,
  `frontend/Dockerfile.caddy-spa`, root `Dockerfile`, root `docker-compose.yaml`.
- **METATRON offensive lab (out-of-band):** `deploy/metatron-lab/` — optional isolated-network
  stub only; see `deploy/metatron-lab/README.md:1` and ADR
  `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`.

## Production Caddy + SPA (apex)

- **Contract:** [`docs/deploy/SPA_APEX_ROUTING_CONTRACT.md`](../docs/deploy/SPA_APEX_ROUTING_CONTRACT.md) — path/method split (legacy POST/OPTIONS/GET vs SPA GET on `/bmi`), proxy prefixes, default `VITE_API_BASE=/api/v1` (same-origin). FastAPI legacy HTML surfaces under `/legacy*` are proxied via the `@api` matcher (`deploy/Caddyfile.production:42`) so they are not swallowed by SPA `try_files`.
- **Build Caddy image** (from repo root; compose uses `frontend/` as build context so root `.dockerignore` stays backend-focused):

```bash
docker compose -f deploy/docker-compose.production.yaml build caddy
```

- **Self-hosted Postgres lane** (colocated `postgres` + `app` + `caddy`): `deploy/docker-compose.production.selfhosted.yaml`. Build Caddy the same way with that file:

```bash
docker compose --project-directory deploy -f deploy/docker-compose.production.selfhosted.yaml build caddy
```

- **Override API base at image build time** (staging / alternate host):

```bash
VITE_API_BASE=https://staging.example.com/api/v1 docker compose -f deploy/docker-compose.production.yaml build caddy
```

- **`deploy/docker-compose.production.yaml`** references `env_file: .env` for the `app` service (path relative to `deploy/`). Create a local `deploy/.env` (gitignored) before `docker compose config` / up, or Compose will error if the file is missing.
- **Validate Caddyfile** with the repo-owned hardened image (requires Docker daemon + placeholder env for `{$PRODUCTION_DOMAIN}`):

```bash
docker build -f frontend/Dockerfile.caddy-spa -t pulseplate-caddy:contract frontend
PRODUCTION_DOMAIN=example.com STAGING_FALLBACK_DOMAIN=staging.example.com \
  docker run --rm -e PRODUCTION_DOMAIN -e STAGING_FALLBACK_DOMAIN \
  -v "$PWD/deploy/Caddyfile.production:/etc/caddy/Caddyfile:ro" \
  pulseplate-caddy:contract caddy validate --config /etc/caddy/Caddyfile
```

- Staging deploys accept only two distinct operator-supplied
  `ghcr.io/katsiarynakavaleuskaya/pulseplate@sha256:<digest>` references
  (backend and Caddy). PostgreSQL is not a third CLI argument: its sole identity
  comes from `deploy/postgres-pgvector/image-manifest.json` and the matching
  digest-pinned Compose service. Floating tags and `latest` are forbidden.
- `STAGING_ATTESTED_DIGEST_READY=true` may be enabled only after the server-local Compose, Caddyfile, deploy script, Postgres backup helper, root-owned contract marker, and current-commit hashes are synchronized. The staging `.env` must be a regular non-symlink file with mode `0600`; it is Compose data and must never be shell-sourced by the deploy path. Merge alone does not update `/srv/pulseplate-staging`.

## Commands (run from repo root)
- Build images: `make docker-build`, `make docker-build-dev`
- Run containers: `make docker-run`, `make docker-run-dev`
- Stop containers: `make docker-stop`

## Experiment Runner image

- `deploy/experiment-runner/Containerfile` is a local evidence image, not a
  production or devcontainer image.
- Keep its Python base tag pinned by OCI digest, install only locked
  `runtime-dev` requirements through BuildKit secrets, and keep the final user
  non-root.
- Image builds may use the approved private proxy. Experiment runs must use a
  prebuilt immutable `name@sha256:<digest>` reference and must not install
  dependencies or pull images after the strict backend probe.
- Post-build admission must inspect image history/config for private-proxy
  secret names and values. Apple runs use the exact inspected
  `name@sha256:<digest>`; Docker runs use the verified local digest with
  `--pull never` and re-check the name-to-digest binding before execution.
- Do not add Compose services, runtime sockets, host home/keychain mounts,
  `SYS_ADMIN`, or other broad capabilities for this image.

## Conventions
- Keep staging and production configs in sync with documented env vars.
- Avoid changes that alter runtime ports without updating clients and docs.

## Private Prometheus contour

- Canonical image and scrape contracts live only in
  `deploy/prometheus/image-manifest.json` and `deploy/prometheus/prometheus.yml`.
  All three Compose contours must keep one equivalent `prometheus` service:
  exact linux/amd64 manifest digest, user `65532:65532`, `cap_drop: ALL`,
  `no-new-privileges`, named `prometheus_data`, and the sole retention carrier
  `--storage.tsdb.retention.time=45d`.
- `observability` is an internal network. Only `app` and `prometheus` join it;
  Prometheus does not join `web`, publish port `9090`, or receive a Caddy route.
  Only `app` and `prometheus` receive the
  `pulseplate_metrics_scrape_key` Compose secret.
- Compose file secrets are bind mounts and do not remap file ownership or mode.
  The account running Compose owns a regular non-symlink `secrets/` directory
  with mode `0700` and a regular non-symlink
  `secrets/pulseplate_metrics_scrape_key` file with mode `0444`. Deploy tooling
  validates metadata but must never source, print, archive, or independently
  parse the value; semantic validation stays in
  `app/security/production_invariants.py`.
- Staging deploy contract version `4` cross-binds the deploy script, staging
  Compose, Prometheus config/image manifest, PostgreSQL image manifest,
  Caddyfile, and backup helper.
  Merge does not synchronize a host or enable
  `STAGING_ATTESTED_DIGEST_READY`; secret bootstrap and staging/production
  activation remain human actions. Follow
  `docs/deploy/OPERATIONAL_SIGNALS.md` for the operator sequence and rollback.

## Immutable PostgreSQL 15 plus pgvector contour

- The sole repository image record is
  `deploy/postgres-pgvector/image-manifest.json`. It binds the exact DHI
  PostgreSQL 15.19 Alpine 3.23 runtime/dev platform manifests, pgvector 0.8.6
  source commit/archive hash, exact APK build closure, reproducible build
  epoch, Containerfile hash, derived GHCR platform/config digests, and Trivy
  0.74 suppression-free scan contract.
- `deploy/postgres-pgvector/Containerfile` is a two-stage build. Source enters
  only as the preverified `pgvector-v0.8.6.tar.gz` context file; the file is not
  tracked. The builder must use
  `/usr/libexec/postgresql15/pg_config`, `make -j1`, empty `OPTFLAGS`, and the
  closed artifact inventory. Do not add curl, git, floating APK packages, a
  second source path, or a host build toolchain.
- The final image adds one and only one compatibility mountpoint layer:
  `/var/lib/postgresql/data` is an empty real directory, owner `70:70`, mode
  `0700`, copied from one verified empty builder directory. This lets the
  tested Docker engine seed a brand-new named-volume root for the inherited
  non-root UID 70 entrypoint. It does not repair, chown, migrate, or prove any
  existing volume. Final-stage `RUN`, `USER`, `ENV`, `VOLUME`, wrapper scripts,
  marker files, broad `/out/var` copies, Compose user overrides, and host-side
  ownership workarounds are forbidden.
- Only staging and `production.selfhosted` use the derived image. Both retain
  the named `postgres_data` mount at `/var/lib/postgresql/data`, explicitly set
  `PGDATA` to that legacy-compatible target, select `linux/amd64`, and publish
  no database port. Managed production remains external and has no Compose
  `postgres` service.
- Pull-request execution is DHI-secret-free and registry-write-free. Only an
  exact trusted push to `refs/heads/main` may read `DHI_USERNAME` and
  `DHI_ACCESS_TOKEN`, reproduce the frozen digest twice, scan exact bases,
  builder, and final image with Trivy 0.74 and an empty ignore file, publish to
  the existing GHCR PulsePlate package, and attach derived provenance/SBOM.
- DHI Community is the only admitted Docker entitlement. Docker documents its
  Community core as free to use, share, and build on under Apache 2.0. The
  existing `pulseplate` GHCR package was authenticated in the GitHub UI as
  `public` on 2026-08-27; workflow publication must require that exact existing
  owner/name/source/visibility before and after writes and must never create a
  package, change visibility, purchase a subscription, or claim Select,
  Enterprise, Docker support, official DHI, or mirror status.
- Treat the output only as a PulsePlate-owned incorporated deployment
  component built from DHI Community. Preserve inherited notices and upstream
  PostgreSQL/pgvector attribution. The bounded public-package disposition is
  tied to Docker's DHI Community docs and Terms observed on 2026-08-27; any
  terms, tier, source-image, package, or topology drift is `HOLD`.
- Install Docker Scout from the exact checksum-pinned official `v1.24.0`
  archive and require its exact binary build identity. Source-attestation
  verification must bind the two exact DHI linux/amd64 subjects. Docker's
  documented `--skip-tlog` path verifies the Docker signature without public
  Rekor/transparency proof; it is source-subject-only and never a scanner,
  VEX, derived-attestation, provenance, or security-gate suppression.
- Deploy scripts must validate the manifest and rendered Compose first, pull
  the exact PostgreSQL digest under temporary GHCR credentials, inspect its
  platform/config/labels, and remove credentials. An existing self-hosted
  transition then captures container/image/volume identity, quiesces worker,
  Caddy, and app, and requires the closed predecessor/current image identity,
  UID 70, exact PGDATA, PostgreSQL 15.19, stable runtime identity, and a
  mode-0600 custom dump accepted by `pg_restore --list` from the still-running
  old database before stopping it. Only then may the candidate use
  `--pull never`; orphan or ambiguous identities/volumes fail closed. Hosts
  never receive DHI credentials.
- The checked main workflow must prove the exact four-directory mountpoint
  layer inventory and then attach a uniquely named fresh empty volume with a
  non-initializing command. The mounted root must be empty `70:70:0700` before
  normal PostgreSQL initialization. This is bounded Docker-engine evidence,
  not universal runtime or existing-volume evidence.
- A fresh PostgreSQL transition must prove the rendered named volume absent
  twice: once before product quiesce and once immediately before the single
  no-pull Compose start. The second census is the declared fresh-volume
  handoff boundary; any appearance, malformed listing, or listing error leaves
  captured writers quiesced and returns `HOLD`. Do not add further same-step
  polling or rollback writes; concurrent manual Compose/Docker mutation is
  outside the admitted transition and requires a separate host-lock design.
- The `postgres-pgvector-publish` canonical-tag write is provisional until an
  immediate exact-main revalidation of the closed PostgreSQL material set
  gates `runtime_ref` output and admission. If that post-write check detects a
  superseding main commit, the publisher must fail without inspection output
  or downstream admission. Do not roll the tag back or add another write: the
  serialized replacement publisher is the sole repair owner, while consumers
  remain bound to the immutable digest. This post-write gate is the declared
  transaction boundary; stronger exclusivity requires a separate ownership
  and threat-model lane rather than additional same-job race checks.
- The PostgreSQL material classifier must cover the complete finite
  compatibility surface owned by the canonical CI `pgvector_compat` filter,
  plus the publication workflow itself. A main push that changes any migration,
  dependency, Compose, deploy, pgvector runtime, or compatibility-test owner
  must take the credential-free compatibility and publisher path; it must not
  fall through to reuse.
- Read-only PostgreSQL reuse has one terminal transaction boundary after scans,
  attestations, and runtime checks: a main run must refetch `main`, prove that
  the complete compatibility surface is unchanged from its exact run SHA, and
  all reuse events must recheck that the canonical tag still selects the frozen
  digest. This final check is read-only and single-pass. Do not add a polling
  loop or tag rollback; stronger exclusion requires a separate ownership/lock
  lane.
- The preceding `postgres-pgvector-ci-admission` compatibility job must remain
  credential-free even on its trusted main-only path. It may consume only the
  single-line, credential-free repository proxy variables; it must not receive
  `DEVPI_CI_*`, publication credentials, an environment-secret grant, or any
  other `secrets.*` expression. The protected `pgvector-publish` environment
  begins only at the publisher job after compatibility admission succeeds.
- Repository/image admission is not activation. Volume census, backup,
  deployment, restore, production release, volume deletion, and the Prometheus
  `T₀` remain separate human-authorized actions.

## Production tag gate
- Semver production tags stay build-only until all three deploy inputs agree: `PROD_DEPLOY_MODE`,
  `WEB_IOS_RELEASE_READY=true`, and `PRODUCTION_ENV_READY=true`.
- `PRODUCTION_ENV_READY=true` is infra-owned and can be set only after the target host already has
  the server-local runtime env file (`/srv/pulseplate-production/.env` or `$DEPLOY_DIR/.env`).
- If the default `github.token` cannot read production-scoped Actions variables, the bridge job may
  retry through `PRODUCTION_ENV_READ_TOKEN`; keep that secret aligned with the deploy runbook.

## Docker entrypoint invariants
Docker must run FastAPI as:
- `app.main:app`

Do not COPY missing legacy files (e.g., app.py) after refactors.

Verify with:
```bash
# Check for obsolete app.py copies
rg -n "COPY .*app\.py|COPY .*legacy_app\.py" Dockerfile

# Verify uvicorn entrypoint
rg -n "uvicorn\s+app(:|.main:app)|legacy_app" Dockerfile Makefile docker-compose.yaml -S

# Should use app.main:app
rg -n "app\.main:app" Dockerfile Makefile docker-compose.yaml -S
```
