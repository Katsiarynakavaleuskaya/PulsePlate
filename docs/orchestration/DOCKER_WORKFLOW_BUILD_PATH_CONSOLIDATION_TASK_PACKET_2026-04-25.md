# Docker Workflow Build-Path Consolidation Task Packet - 2026-04-25

Status: Active PR-9 slice in the Docker / CI / Security discipline series

## Summary

After Docker runtime slimming, telemetry, hard-budget enforcement, signed
provenance, and Shared Safety extraction landed, this slice reduces CI cost and
drift by consolidating duplicate production-image build paths and reusing exact
image references or digests where the GitHub Actions workflow boundaries allow
safe reuse.

The first implementation target is the duplicated `target: production` backend
image build across `build.yml`, `docker-image.yml`, `trivy.yml`, and
`docker-openapi-smoke.yml`. The lane must preserve the existing runtime,
security, budget, and attestation contracts while removing redundant work.

## Branch / worktree

- Branch: `codex/docker-build-path-consolidation`
- Worktree: `worktrees/docker-build-path-consolidation-pr9`
- Draft PR: `#1526`

## Mandatory role order

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `backend-engineer`
5. `dev-operator`
6. post-open `qa-engineer-agent`
7. post-open `bug-hunter`

No ad hoc role stack may replace this order.

## Scope

- reconcile backlog/docs drift after `PR #1503` and `PR #1515`
- keep the active slice on Docker workflow build-path consolidation / digest reuse
- consolidate duplicate production-image build work without changing runtime
  dependency profiles
- preserve Docker telemetry and hard-budget evidence contracts
- preserve pushed-image provenance/SBOM attestation contracts
- prefer exact image digest reuse over rebuilding where GitHub Actions
  boundaries make that deterministic

## Non-goals

- no Docker base-image change
- no requirements-profile split
- no API-core worker/report image split
- no Dagger or alternate control plane
- no SBOM/VEX signed security-artifact maturity lane
- no provenance changes beyond preserving the landed contract
- no frontend/Caddy topology changes

## Acceptance criteria

- `build.yml` remains the canonical production-image build/publish path
- follow-on Docker validation lanes reuse the produced image reference or digest
  where feasible instead of rebuilding an equivalent `target: production` image
- telemetry, hard-budget, Trivy, and OpenAPI smoke evidence remain available to
  PR authors and operators
- workflow-contract tests document the promoted build/reuse contract
- docs keep Dagger deferred and SBOM/VEX blocked by release-truth criteria

## Validation plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- targeted workflow-contract tests for Docker build/reuse behavior
- targeted helper tests for any new or changed CI helper
- `pre-commit run --all-files`
- current-head GitHub checks for the draft PR
- strict `check_merge_ready.py --require-auth` before any merge claim

Operator-approved machine-heavy exception applies to this lane: do not run full
local `make verify` by default. Use PR-scoped local gates plus current-head
GitHub CI as the heavy signal.

## Follow-ups

- Docker base-image and API-core dependency-profile slimming remain separate
  candidates after this lane.
- Dagger remains deferred until the GitHub Actions Docker baseline is stable.
- SBOM/VEX signed security artifacts remain blocked by release-truth criteria.
