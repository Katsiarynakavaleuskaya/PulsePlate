# Docker Runtime Slimming Task Packet — 2026-04-21

Status: Active PR-4 slice in the Docker / CI discipline series

## Summary

After the install-profile split and the merged deploy-contract reconciliation
lane (`PR #1488` on April 21, 2026), this slice standardizes production-target
Docker builds on `requirements-docker-runtime.txt` and adds deterministic
evidence that CI-only tooling and optional heavy/vector packages do not leak
into the backend runtime image.

## Branch / worktree

- Branch: `codex/docker-runtime-slimming-after-profile-split`
- Worktree: `worktrees/docker-runtime-slimming-pr4`

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

- add `requirements-docker-runtime.in` / `requirements-docker-runtime.txt`
- wire production-target Docker workflows to the Docker runtime manifest
- keep backend build context narrow in `Dockerfile` and `.dockerignore`
- add deterministic runtime dependency-surface guard + tests
- update deploy docs and backlog status for the runtime-slimming slice

## Non-goals

- no image budget enforcement
- no telemetry baseline promotion
- no Shared Safety audit script extraction
- no provenance / attestation recovery
- no Dagger or alternate control plane
- no frontend/Caddy topology changes

## Acceptance criteria

- production-target Docker workflows no longer use `requirements-ci-lite.txt`
- backend production image excludes CI-only tooling and optional heavy/vector packages
- runtime still serves `app.main:app`
- approved proxy, constraints, and emergency-wheel manifest contract stay intact
- docs and backlog explicitly defer the next Docker/CI follow-ups
