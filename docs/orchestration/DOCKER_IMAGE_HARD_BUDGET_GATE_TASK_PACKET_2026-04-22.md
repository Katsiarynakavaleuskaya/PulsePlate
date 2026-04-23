# Docker Image Hard Budget Gate Task Packet — 2026-04-22

Status: Active PR-6 slice in the Docker / CI discipline series

## Summary

After telemetry baseline merged via `PR #1492`, this slice promotes the
production backend image from warning-only regression reporting to a
deterministic hard budget gate.

## Branch / worktree

- Branch: `codex/docker-image-hard-budget-gate`
- Worktree: `worktrees/docker-image-hard-budget-gate-pr6`

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

- add one checked-in hard-budget policy for the production backend image
- add a dedicated budget-check helper under `scripts/ci/`
- wire the hard gate into `build.yml`, `docker-image.yml`, and `trivy.yml`
- keep baseline fetch and telemetry generation as separate seams
- update docs and backlog for the hard-budget slice

## Non-goals

- no Shared Safety extraction
- no provenance / attestation recovery
- no Dagger or alternate control plane
- no frontend/Caddy topology change
- no runtime dependency-contract widening

## Acceptance criteria

- all three Docker lanes use the same checked-in budget policy
- image-size cap and positive-delta cap fail the lane deterministically
- telemetry artifacts and budget-check artifacts stay PR-visible even on failure
- telemetry/budget reporting stays scoped to the production backend image
- docs and backlog keep Shared Safety and provenance/Dagger explicitly deferred
