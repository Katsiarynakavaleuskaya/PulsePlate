# Docker / CI Discipline PR Series Packet (2026-04-16)

Date: 2026-04-16
Status: Active governance wave

## Purpose

This packet defines the canonical coordinator-led execution lane for the Docker /
CI discipline epic. The lane keeps Docker, deploy-shape, and image-budget work
as a deterministic PR train instead of reopening the repo to ad hoc infra churn
or a second CI/CD control plane.

## Scope

This packet applies to Docker/deploy governance slices only:

- clean-start bootstrap from synced `origin/main`
- CI install profile split cross-linked to approved dependency-governance
  anchors
- deploy contract reconciliation for backend image + separate frontend/Caddy
  image topology
- runtime slimming after install-profile split
- image size / largest-layer / build-context telemetry and regression reporting

Out of scope for this lane:

- Dagger, Jenkins, GitLab CI, Tekton, Argo Workflows, Flux, or other new
  control-plane introductions
- signed provenance / attestation re-enablement while the documented buildx/GHA
  cache seam still requires `provenance: false`
  (`.github/workflows/build.yml:42-56`;
  `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md:47-60`;
  `docs/roadmap/BACKLOG_LEDGER.md:629-643`)
- broad runtime feature work unrelated to Docker/build/install discipline
- monolithic backend+frontend image redesign

## Canonical References

- [`AGENTS.md`](../../AGENTS.md)
- [`RUNBOOK_AGENT.md`](../../RUNBOOK_AGENT.md)
- [`docs/orchestration/AGENTS.md`](./AGENTS.md)
- [`docs/orchestration/workflow.md`](./workflow.md)
- [`docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md`](./PR_MERGE_WORKFLOW_MATRIX.md)
- [`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`](./PR_ORCHESTRATION_CONTRACT_MATRIX.md)
- [`docs/roadmap/BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md)
- [`docs/roadmap/DEPLOY_WEB_DIAGNOSIS_AND_FIX.md`](../roadmap/DEPLOY_WEB_DIAGNOSIS_AND_FIX.md)
- [`docs/deploy/PRODUCTION.md`](../deploy/PRODUCTION.md)
- [`deploy/docker-compose.production.yaml`](../../deploy/docker-compose.production.yaml)
- [`deploy/docker-compose.production.selfhosted.yaml`](../../deploy/docker-compose.production.selfhosted.yaml)
- [`deploy/docker-compose.staging.yaml`](../../deploy/docker-compose.staging.yaml)
- [`Dockerfile`](../../Dockerfile)
- [`frontend/Dockerfile.caddy-spa`](../../frontend/Dockerfile.caddy-spa)
- [`../../.dockerignore`](../../.dockerignore)
- [`../../frontend/.dockerignore`](../../frontend/.dockerignore)
- [`../../.github/workflows/build.yml`](../../.github/workflows/build.yml)
- [`../../.github/workflows/docker-image.yml`](../../.github/workflows/docker-image.yml)
- [`../../.github/workflows/trivy.yml`](../../.github/workflows/trivy.yml)
- [`../../.github/workflows/cd.yml`](../../.github/workflows/cd.yml)
- [`../../.github/actions/python-setup/action.yml`](../../.github/actions/python-setup/action.yml)

## Repo-Truth Invariants

- Root `.dockerignore` already exists and is a strict allowlist for the backend
  Docker build context (`.dockerignore:1-42`). This lane may audit or narrow it
  further, but must not replace it with a broad default-include context.
- Production topology is already split:
  - backend runtime image is pinned via `IMAGE_REF`
    (`deploy/docker-compose.production.yaml:11-27`)
  - frontend/Caddy shell is built separately from
    `frontend/Dockerfile.caddy-spa`
    (`deploy/docker-compose.production.yaml:41-46`;
    `frontend/Dockerfile.caddy-spa:1-25`)
- Signed provenance remains intentionally deferred while buildx/GHA cache
  stability still requires `provenance: false`
  (`.github/workflows/build.yml:42-56`;
  `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md:47-60`;
  `docs/roadmap/BACKLOG_LEDGER.md:629-643`).
- Neighboring governance slices already have their own canonical review
  artifacts (`docs/review/PR_1432_FIXED_MAPPING.md:1-35`;
  `docs/review/PR_1433_FIXED_MAPPING.md:1-39`). If another overlapping PR
  appears, rebase the active slice onto refreshed `origin/main` instead of
  widening scope.

## Mandatory Role Order

For every PR in this series, the lane uses coordinator-first orchestration and
the declared packet/runbook order only.

`docs/orchestration/AGENTS.md` stays a pointer-only summary for this lane; this
packet is the canonical field-level contract and the role order below is the
SoT that the scoped AGENTS summary must mirror.

- Primary: `agent-coordinator`
- Core execution path:
  - `architecture-specialist`
  - `security-auditor`
  - `backend-engineer`
  - `dev-operator`
- Mandatory post-open lane:
  - `qa-engineer-agent`
  - `bug-hunter`

No ad hoc role stack may replace this order.

## Bootstrap Contract Before PR-1

Every slice in this wave starts from a clean synced branch, not from local dirty
state:

1. Preserve unrelated uncommitted work via stash or dedicated side branch.
2. `git checkout main`
3. `git fetch --prune origin`
4. `git merge --ff-only origin/main`
5. Confirm `git status --short` is clean.
6. Create the slice branch from that synced base.

This rule exists to keep the Docker epic isolated from the separate
dependency-governance line and any unrelated local artifacts.

## PR Series Contract

### PR-1: Governance Packet + Backlog Reconciliation

Files:

- `docs/orchestration/DOCKER_CI_DISCIPLINE_PR_SERIES_PACKET_2026-04-16.md`
- `docs/orchestration/AGENTS.md`
- `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

Outcome:

- canonical Docker/CI discipline packet exists
- role order, merge loop, cleanup loop, and deferred-lane boundaries are explicit
- remaining train slices are recorded in backlog instead of implied informally

### PR-2: CI Install Profile Split

Files:

- `.github/actions/python-setup/action.yml`
- `.github/workflows/ci.yml`
- Docker/CI workflows only when they truly need explicit profile selection
- `scripts/ci/install_locked_python_requirements.py`
- requirement/constraint surfaces only where the profile split contract requires it

Outcome:

- generic backend/shared CI avoids the heavy ML/GPU install surface
- ML-heavy jobs request that profile explicitly
- approved proxy / emergency wheel manifest / fail-closed installer semantics stay intact

Cross-linked backlog anchors:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock`
- `docs/roadmap/BACKLOG_LEDGER.md#backlog-restore-signed-build-provenance`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-compose-v2-migration`

### PR-3: Deploy Contract Reconciliation

Files:

- `deploy/docker-compose.production.yaml`
- `deploy/docker-compose.production.selfhosted.yaml`
- `deploy/docker-compose.staging.yaml`
- `docs/deploy/*`
- `deploy/WORKFLOW.md`
- CD artifact staging logic, if required by the operator contract

Outcome:

- evidence anchors for the target contract already live at
  `deploy/docker-compose.production.yaml:11-27`,
  `deploy/docker-compose.production.yaml:41-46`, and
  `frontend/Dockerfile.caddy-spa:1-25`
- docs and compose agree on the split backend-image + separate frontend/Caddy
  shell topology
- stale `frontend_dist` / copy-into-backend assumptions are removed
- `docker compose` v2 wording is canonical across touched docs

### PR-4: Runtime Slimming After Profile Split

Files:

- `Dockerfile`
- `frontend/Dockerfile.caddy-spa` only if build/runtime evidence requires it
- supporting docs/tests only where the contract changes

Outcome:

- no builder-only tooling leaks into runtime image
- no accidental widening of the Docker `COPY` surface
- runtime keeps serving `app.main:app`

### PR-5: Image Budget and Telemetry Gate

Files:

- `.github/workflows/build.yml`
- `.github/workflows/docker-image.yml`
- `.github/workflows/trivy.yml`
- helper scripts/tests under `scripts/ci/` and `tests/` if needed

Outcome:

- evidence anchors for the telemetry baseline already live at
  `docs/roadmap/BACKLOG_LEDGER.md:532-552`,
  `.github/workflows/build.yml:42-56`, and
  `docs/orchestration/AGENTS.md:43-50`
- CI emits deterministic image size and largest-layer evidence
- build-context evidence is visible in PR-time reporting
- regression-only gating exists before any future Dagger discussion

## Dagger / Alternate Control Plane Policy

Do not introduce Dagger or any alternate CI/CD control plane in this wave.

A future Dagger pilot may be considered only after all of the following are true:

- PR-2 install-profile split is landed and stable
- PR-3 deploy contract reconciliation is landed
- PR-5 image-budget telemetry is landed and producing deterministic evidence
  (`docs/roadmap/BACKLOG_LEDGER.md:532-552`)
- signed provenance remains explicitly tracked as a separate deferred lane rather
  than mixed into the pilot
  (`docs/roadmap/BACKLOG_LEDGER.md:629-643`;
  `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md:47-60`)

## Mandatory PR Loop

For every PR slice in this series:

1. run preflight + agent consistency checks
2. freeze role order from this packet
3. open as draft and create `docs/review/PR_<N>_FIXED_MAPPING.md`
4. run mandatory post-open `qa-engineer-agent -> bug-hunter`
5. before each push: `pre-commit run --all-files` + touched-scope gates
6. after each review event: fix code/docs first, artifact mapping second, PR body mirror third
7. before merge claim: `make verify`
8. final merge gate only via
   `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo <owner/name> --require-auth`
9. after merge: sync local `main`, prune the finished lane, remove only lane-local
   gitignored artifacts

## Evidence and Disposition

- Review disposition proof remains artifact-first in `docs/review/PR_<N>_FIXED_MAPPING.md`
- Any deferred follow-up is recorded immediately in `docs/roadmap/BACKLOG_LEDGER.md`
- No PR in this series is merge-ready without the mandatory post-open bug-hunter pass
