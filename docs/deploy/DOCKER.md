# Docker Runtime Contract

This document is the operator-facing source of truth for the PulsePlate backend
Docker runtime contract.

## Current production contract

- Backend runtime image uses `PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt`.
- CI-only tooling stays in `requirements-ci-lite.txt`.
- Optional vector / ML dependencies stay in `requirements-rag-vector.txt`.
- Production target remains the split backend image that serves `app.main:app`.
- Frontend / Caddy topology remains separate and out of scope for this slice.

## Why this slice exists

The install-profile split removed heavy ML / GPU packages from the generic CI
surface, but some production-target Docker workflows were still building the
backend image with `requirements-ci-lite.txt`.

That left CI-only tooling inside the runtime image:

- `pre-commit`
- `bandit`
- `diff-cover`
- `pytest`

This PR standardizes production-target Docker builds on a dedicated runtime
manifest so the backend image does not carry CI-only tooling.

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

## Rollback

If the runtime image fails to build or boot after this slice:

1. restore the previous Docker build arg usage in production-target workflows
2. switch `PULSEPLATE_REQUIREMENTS_FILE` back to the prior manifest for the
   affected workflow
3. keep the runtime-surface findings as evidence in the PR and record the
   follow-up in `docs/roadmap/BACKLOG_LEDGER.md`

Do not widen this rollback into image-budget telemetry, provenance, or
frontend/Caddy changes.

## Deferred follow-ups

Explicitly deferred from this PR:

- `P1: Docker image budget and telemetry baseline`
- `P1: Shared Safety audit script after install-profile split`
- provenance / attestation recovery
- Dagger or any alternate control-plane work
