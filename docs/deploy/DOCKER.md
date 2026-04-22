# Docker Runtime And Telemetry Contract

This document is the operator-facing source of truth for the PulsePlate backend
Docker runtime contract.

## Current production contract

- Backend runtime image uses `PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt`.
- CI-only tooling stays in `requirements-ci-lite.txt`.
- Optional vector / ML dependencies stay in `requirements-rag-vector.txt`.
- Production target remains the split backend image that serves `app.main:app`.
- Frontend / Caddy topology remains separate and out of scope for this slice.
- Runtime slimming merged via `PR #1490` on April 22, 2026.
- The current Docker/CI slice establishes the first canonical backend-image
  telemetry baseline for warning-only regression reporting.

## Runtime manifest policy

`requirements-docker-runtime.txt` is the Docker production dependency surface.

Rules:

- keep only dependencies required for `app.main` imports and current production
  backend endpoints
- do not add CI-only tooling
- do not add the optional vector / ML stack
- keep the install path on the approved private proxy + constraints +
  emergency-wheel manifest contract

Blocked package classes for the default backend runtime:

- CI / dev tooling: `pytest`, `pre-commit`, `bandit`, `diff-cover`
- optional vector / ML stack: `sentence-transformers`, `transformers`, `torch`,
  `pgvector`
- GPU / CUDA packages: `nvidia-*`, `cuda-*`, `triton`

## Why the telemetry slice exists

Runtime slimming removed CI-only tooling from the production backend image, but
the project still needs one canonical baseline so PR authors can see image-size
drift, largest layers, and build-context evidence before merge.

This wave keeps that signal warning-only:

- no absolute image-size cap
- no hard failure threshold for positive delta vs baseline
- no provenance / Dagger reopening until the baseline exists

## Baseline source rule

All three Docker telemetry lanes use one canonical backend baseline:

1. latest successful `main` artifact from `build.yml`
2. checked-in seed fallback at `docs/telemetry/docker_image_baseline.production.json`

`scripts/ci/fetch_docker_image_baseline.py` resolves the baseline before
telemetry collection. If GitHub lookup/download fails, the workflow falls back
to the checked-in seed and still publishes advisory evidence.

## Telemetry evidence contract

`scripts/ci/docker_image_telemetry.py` remains local-image-only. It does not
talk to GitHub; it only renders PR-visible evidence from the built image and
the resolved baseline JSON.

Each Docker lane publishes:

- `docker-image-telemetry.json`
- `docker-image-telemetry.md`
- `GITHUB_STEP_SUMMARY` entry

Evidence must include:

- image size
- baseline source: `main-artifact` or `repo-seed-fallback`
- baseline reference metadata when available
- delta vs baseline in warning-only mode
- largest layers
- build-context evidence

## Validation commands

Build the production target:

```bash
docker build \
  --target production \
  --build-arg PULSEPLATE_PYTHON_INDEX_URL="$PULSEPLATE_PYTHON_INDEX_URL" \
  --build-arg PULSEPLATE_PYTHON_TRUSTED_HOST="${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" \
  --build-arg PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt \
  -t pulseplate:runtime-slim .
```

Validate runtime dependency surface:

```bash
python3 scripts/ci/check_docker_runtime_dependency_surface.py \
  --image pulseplate:runtime-slim \
  --output-json artifacts/docker/runtime_dependency_surface.json
```

Basic import smoke:

```bash
docker run --rm pulseplate:runtime-slim \
  python -c "import app.main; print('app.main import ok')"
```

Resolve the canonical baseline and generate advisory telemetry:

```bash
python3 scripts/ci/fetch_docker_image_baseline.py \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --fallback-json docs/telemetry/docker_image_baseline.production.json \
  --output artifacts/docker/docker-image-baseline.json

python3 scripts/ci/docker_image_telemetry.py \
  --image-ref pulseplate:runtime-slim \
  --baseline-json artifacts/docker/docker-image-baseline.json \
  --json-out artifacts/docker/docker-image-telemetry.json \
  --markdown-out artifacts/docker/docker-image-telemetry.md
```

## Rollback

If the runtime image fails to build or boot after this slice:

1. restore the previous Docker build arg usage in production-target workflows
2. switch `PULSEPLATE_REQUIREMENTS_FILE` back to the prior manifest for the
   affected workflow
3. keep the runtime-surface findings as evidence in the PR and record the
   follow-up in `docs/roadmap/BACKLOG_LEDGER.md`

Do not widen this rollback into hard image-budget enforcement, provenance, or
frontend/Caddy changes.

## Deferred follow-ups

Explicitly deferred after this PR:

- hard image-budget cap / failure threshold
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-image-hard-budget-gate`
  Remove-by: 2026-05-31
  Rollback: keep telemetry advisory-only and remove any premature hard-stop threshold from Docker lanes.
  Exit criteria: a dedicated follow-up PR lands a deterministic hard-fail threshold for the production backend image after the warning-only baseline stabilizes on `main`.
- `P1: Shared Safety audit script after install-profile split`
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-safety-audit-shared-script-after-pr1479`
  Remove-by: 2026-06-15
  Rollback: keep Safety invocation duplicated in the existing workflows until the shared extraction lands.
  Exit criteria: a follow-up PR extracts the shared Safety invocation/reporting path without reopening install-profile split scope.
- provenance / attestation recovery
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#backlog-restore-signed-build-provenance`
  Remove-by: 2026-06-30
  Rollback: keep signed provenance disabled on the known cache/buildx seam and preserve the documented workaround.
  Exit criteria: signed provenance and downstream verification return to the canonical image workflow without destabilizing the release path.
- Dagger or any alternate control-plane work
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-dagger-pilot-after-docker-baseline`
  Remove-by: 2026-07-15
  Rollback: keep the current GitHub Actions-based Docker control plane as the only supported path.
  Exit criteria: telemetry baseline and provenance follow-ups are closed and a separate evaluation packet re-approves any Dagger pilot.
