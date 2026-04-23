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
- Telemetry baseline landed via `PR #1492` on April 22, 2026.
- Hard-budget enforcement landed via `PR #1498` on April 22, 2026.
- The current Docker/CI slice restores signed provenance and SPDX SBOM
  attestations on pushed-image lanes and verifies both before deploy.

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

## Why the hard-budget slice exists

Runtime slimming removed CI-only tooling from the production backend image, but
the project still needs one canonical baseline so PR authors can see image-size
drift, largest layers, and build-context evidence before merge.

Telemetry and the hard-budget gate established deterministic image-size
evidence, but deployable image trust still depended on the temporary CD
workaround that kept pushed-image attestations disabled.

This wave restores signed provenance on pushed-image lanes only:

- keep the current hard-budget contract unchanged
- restore `provenance: mode=max` on pushed-image lanes in `build.yml` and `cd.yml`
- emit SPDX SBOM attestations on the same pushed-image lanes
- verify both provenance and SBOM by exact digest before staging or production deploy
- Dagger and Shared Safety remain deferred

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
- `docker-image-budget-check.json`
- `docker-image-budget-check.md`
- `GITHUB_STEP_SUMMARY` entry

Evidence must include:

- image size
- baseline source: `main-artifact` or `repo-seed-fallback`
- baseline reference metadata when available
- delta vs baseline against the blocking hard-budget policy
- largest layers
- build-context evidence

Hard budget enforcement must fail when either of these are true:

- `image_size_bytes > 470000000`
- `baseline.size_delta_bytes > 20000000`

## Attestation verification contract

Staging and production deploy flow must verify the exact pushed digest with
GitHub-native attestation verification before any deploy step continues.

Helper:

- `scripts/ci/check_docker_provenance_attestation.py`

Inputs:

- registry image name without a tag
- exact pushed digest from `docker/build-push-action`
- GitHub repo identity
- signer workflow path
- source ref for the current run

Outputs:

- `docker-provenance-attestation-check.json`
- `docker-provenance-attestation-check.md`
- `GITHUB_STEP_SUMMARY` entry in `cd.yml`

The verifier must fail closed unless both checks pass:

- provenance predicate: `https://slsa.dev/provenance/v1`
- SBOM predicate: `https://spdx.dev/Document/v2.3`

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

Resolve the canonical baseline and generate telemetry evidence:

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

python3 scripts/ci/check_docker_image_budget.py \
  --telemetry-json artifacts/docker/docker-image-telemetry.json \
  --budget-json docs/telemetry/docker_image_budget.production.json \
  --json-out artifacts/docker/docker-image-budget-check.json \
  --markdown-out artifacts/docker/docker-image-budget-check.md

python3 scripts/ci/check_docker_provenance_attestation.py \
  --image-name ghcr.io/katsiarynakavaleuskaya/pulseplate \
  --digest sha256:example \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --signer-workflow Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml \
  --source-ref refs/heads/main \
  --json-out artifacts/docker/docker-provenance-attestation-check.json \
  --markdown-out artifacts/docker/docker-provenance-attestation-check.md
```

## Rollback

If pushed-image provenance verification fails after this slice:

1. keep `load: true` jobs unchanged on `provenance: false`
2. revert pushed-image provenance/SBOM restoration only on the failing lane
3. keep attestation evidence artifacts in the PR and record the follow-up in
   `docs/roadmap/BACKLOG_LEDGER.md`

Do not widen this rollback into Shared Safety, Dagger, or frontend/Caddy changes.

## Deferred follow-ups

Explicitly deferred after this PR:

- `P1: Shared Safety audit script after install-profile split`
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-safety-audit-shared-script-after-pr1479`
  Remove-by: 2026-06-15
  Rollback: keep Safety invocation duplicated in the existing workflows until the shared extraction lands.
  Exit criteria: a follow-up PR extracts the shared Safety invocation/reporting path without reopening install-profile split scope.
- Dagger or any alternate control-plane work
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-dagger-pilot-after-docker-baseline`
  Remove-by: 2026-07-15
  Rollback: keep the current GitHub Actions-based Docker control plane as the only supported path.
  Exit criteria: telemetry baseline, hard-budget, and provenance slices are closed and a separate evaluation packet re-approves any Dagger pilot.
