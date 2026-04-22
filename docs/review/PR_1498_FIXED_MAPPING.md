# PR #1498 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 99157f43a
Evidence: `tests/test_python_supply_chain_controls.py:75-78`; `tests/test_python_supply_chain_controls.py:690-748`; `docs/review/PR_1498_FIXED_MAPPING.md:42-46`
Reason: The workflow-contract test now caches step-name lists once, asserts the docker-image hard-budget ordering explicitly, and the deferred provenance/Dagger follow-ups now point to concrete backlog anchors instead of an untracked umbrella note.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1498#pullrequestreview-4157683913 -> 99157f43a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1498#discussion_r3126676236 -> 99157f43a

Disposition: NOT-A-BUG
Evidence: `docs/orchestration/DOCKER_IMAGE_HARD_BUDGET_GATE_TASK_PACKET_2026-04-22.md:28-35`; `docs/orchestration/DOCKER_IMAGE_HARD_BUDGET_GATE_TASK_PACKET_2026-04-22.md:36-42`; `.github/workflows/build.yml:103-198`; `.github/workflows/docker-image.yml:90-136`; `.github/workflows/trivy.yml:102-163`
Reason: The suggestion to extract the three Docker hard-budget lanes into a shared composite action is maintainability advice, not a correctness bug. This slice intentionally keeps the enforcement blocks explicit inside the three canonical workflows named in the task packet so each lane preserves its own artifact naming, summary publication, and terminal fail-step semantics without widening scope into a reusable-actions refactor.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1498#pullrequestreview-4157673112

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Mandatory wait-window satisfied (final check pass completed, then waited >=1 review cycle after latest bot/review activity)
  Evidence: pending initial review and current-head CI cycle.
- [ ] Current-head CI is green for PR branch head
  Evidence: pending current-head GitHub checks after PR open.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head GitHub checks after PR open.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending initial review cycle.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: `docs/review/PR_1498_FIXED_MAPPING.md:17-28`
- [x] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed before commit `99157f43a`.
- [ ] `make verify` green on latest pushed head
  Evidence: not run for this lane; current-head GitHub checks remain the heavy signal by operator choice.

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md` line 540 (`P1: Shared Safety audit script after install-profile split`)
- provenance recovery follow-up
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#backlog-restore-signed-build-provenance`
- Dagger follow-up after the hard budget gate stabilizes
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-dagger-pilot-after-docker-baseline`
