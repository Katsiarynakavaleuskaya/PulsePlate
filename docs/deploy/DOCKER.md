# Docker Runtime And Telemetry Contract

This document is the operator-facing source of truth for the PulsePlate backend
Docker runtime contract.

## Current production contract

- Backend runtime image uses `PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt`.
- CI-only tooling stays in `requirements-ci-lite.txt`.
- Optional vector / ML dependencies stay in `requirements-rag-vector.txt`.
- Production target remains the split backend image that serves `app.main:app`.
- Production target removes Debian package-manager tooling (`apt`, `gpgv`) and
  `libgnutls30`; runtime-base and development stages keep package-manager
  tooling for non-production workflows.
- Staging currently extends `production`, so staging inherits the same
  package-manager removal unless a separate reviewed topology PR changes that.
- Frontend / Caddy topology remains separate and out of scope for this slice.
- Runtime slimming merged via `PR #1490` on April 22, 2026.
- Telemetry baseline landed via `PR #1492` on April 22, 2026.
- Hard-budget enforcement landed via `PR #1498` on April 22, 2026.
- Signed provenance and SPDX SBOM attestation verification landed via `PR #1503`.
- Shared Safety audit extraction landed via `PR #1515`.
- Duplicate production-image build-path consolidation landed via `PR #1526`.
- Post-consolidation Docker runtime dependency-profile slimming landed via
  `PR #1530`.
- The current Docker/CI/Security baseline keeps PR-time smoke validation on the
  canonical loaded-image build path where workflow boundaries allow
  deterministic reuse.

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
- production-only Debian package-manager / GnuTLS alert surface: `apt`,
  `gpgv`, `libgnutls30`

## Why the hard-budget slice exists

Runtime slimming removed CI-only tooling from the production backend image, but
the project still needs one canonical baseline so PR authors can see image-size
drift, largest layers, and build-context evidence before merge.

Telemetry and the hard-budget gate established deterministic image-size
evidence. Signed provenance restoration then restored deployable image trust on
pushed-image lanes only:

- keep the current hard-budget contract unchanged
- keep CD pushed-image BuildKit provenance capped at `provenance: mode=min`
  while Docker package-index inputs remain BuildKit secret envs
- keep `build.yml` publish as a scan-before-push lane: load the production image
  locally, fail closed on Trivy/SARIF, then push the same scanned tags
- emit GitHub-signed provenance and SPDX SBOM attestations on pushed images
- verify both provenance and SBOM by exact digest before staging, production
  deploy, or release-control-plane digest publication

With runtime, budget, provenance, Shared Safety, build-path consolidation, and
post-consolidation runtime slimming slices landed, `build.yml` now owns the
canonical PR-time production image validation path: runtime dependency surface,
telemetry, hard budget, container health, and OpenAPI compatibility smoke checks
run against the same loaded `target: production` image. The `main`/schedule/manual
`trivy.yml` lane remains out-of-band image-security evidence outside ordinary
PR merge truth, and pushed-image provenance/SBOM contracts remain isolated to
publish/deploy paths.

## Baseline source rule

Docker telemetry uses one canonical backend baseline:

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

CD generates GitHub-signed attestations before verification:

- provenance: `actions/attest-build-provenance`
- SBOM: `actions/attest` with `sbom-path`
- registry publication: `push-to-registry: true`

The verifier must fail closed unless both checks pass:

- provenance predicate: `https://slsa.dev/provenance/v1`
- SBOM predicate: `https://spdx.dev/Document/v2.3`

## Validation commands

Build the production target:

```bash
docker build \
  --target production \
  --secret id=pp_py_index,env=PULSEPLATE_PYTHON_INDEX_URL \
  --secret id=pp_py_host,env=PULSEPLATE_PYTHON_TRUSTED_HOST \
  --build-arg PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt \
  -t pulseplate:runtime-slim .
```

Validate runtime dependency surface:

```bash
python3 scripts/ci/check_docker_runtime_dependency_surface.py \
  --image pulseplate:runtime-slim \
  --blocked-debian-package apt \
  --blocked-debian-package gpgv \
  --blocked-debian-package libgnutls30 \
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

- Dagger or any alternate control-plane work
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-dagger-pilot-after-docker-baseline`
  Remove-by: 2026-07-15
  Rollback: keep the current GitHub Actions-based Docker control plane as the only supported path.
  Exit criteria: telemetry baseline, hard-budget, provenance, and build-path consolidation slices are closed and a separate evaluation packet re-approves any Dagger pilot.
- SBOM/VEX signed security-artifact maturity lane
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-sbom-vex-signed-security-artifacts`
  Remove-by: 2026-08-15
  Rollback: keep the landed GitHub-native provenance/SBOM attestation verification as the only blocking Docker security artifact gate.
  Exit criteria: release-truth blockers are closed and a dedicated packet approves SBOM/VEX/cosign/OPA rollout.
