# Docker Image Budget And Telemetry Task Packet — 2026-04-22

Status: Active PR-5 slice in the Docker / CI discipline series

## Summary

After runtime slimming merged via `PR #1490` on April 22, 2026, this slice
establishes the first canonical backend-image telemetry baseline for Docker
lanes. The baseline stays warning-only in this wave: CI must surface image size,
largest layers, build-context evidence, and delta vs baseline without turning
that signal into a hard budget gate yet.

## Branch / worktree

- Branch: `codex/docker-image-budget-telemetry-baseline`
- Worktree: `worktrees/docker-image-budget-telemetry-pr5`

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

- add a checked-in backend-image seed baseline
- fetch the latest successful `main` Docker telemetry artifact when available
- normalize baseline-source metadata into PR-visible telemetry evidence
- wire baseline comparison into `build.yml`, `docker-image.yml`, and `trivy.yml`
- update docs and backlog for the telemetry-baseline slice

## Non-goals

- no hard image-size budget cap
- no Shared Safety audit script extraction
- no provenance / attestation recovery
- no Dagger or alternate control plane
- no frontend/Caddy topology changes
- no runtime dependency-contract widening

## Acceptance criteria

- Docker workflows resolve one canonical backend baseline before telemetry collection
- telemetry reports baseline source as `main-artifact` or `repo-seed-fallback`
- delta vs baseline remains warning-only and PR-visible
- largest-layer and build-context evidence stay in the same JSON/Markdown payload
- docs and backlog explicitly keep Shared Safety and provenance/Dagger follow-ups deferred
