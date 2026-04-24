# Docker Signed Build Provenance Task Packet — 2026-04-23

Status: Active PR-7 slice in the Docker / CI discipline series

## Summary

After telemetry baseline and the hard-budget gate landed on April 22, 2026 via
`PR #1492` and `PR #1498`, this slice restores signed build provenance on
push-to-registry Docker lanes and verifies both provenance and SPDX SBOM
attestations before any staging or production deploy continues.

## Branch / worktree

- Branch: `codex/docker-restore-signed-build-provenance`
- Worktree: `worktrees/docker-signed-provenance-pr7`

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

- restore `provenance: mode=max` on pushed-image steps in `build.yml` and `cd.yml`
- emit SBOM attestations on the same pushed-image steps
- add one GitHub-native verifier helper under `scripts/ci/`
- gate staging and production deploy flow on exact-digest attestation verification
- reconcile backlog/docs/ADR text so provenance becomes the active next slice

## Non-goals

- no provenance enablement on `load: true` jobs
- no Shared Safety audit extraction
- no Dagger or alternate control plane
- no frontend/Caddy topology changes
- no multi-arch restore

## Acceptance criteria

- `build.yml` publish and `cd.yml` push lanes use `provenance: mode=max`
- pushed-image steps emit SBOM attestations alongside provenance
- CD creates GitHub-signed provenance/SBOM attestations and verifies both by digest before deploy
- CI publishes deterministic JSON/Markdown evidence for attestation verification
- docs and backlog keep Shared Safety as a separate follow-up and Dagger deferred
