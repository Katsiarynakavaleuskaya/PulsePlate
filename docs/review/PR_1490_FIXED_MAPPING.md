# PR #1490 — Fixed in Commit Mapping (canonical)

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
Commit: a36bf3747
Evidence: `scripts/ci/check_docker_runtime_dependency_surface.py:86-109`; `scripts/ci/check_docker_runtime_dependency_surface.py:159-168`; `tests/test_docker_runtime_dependency_surface.py:12-56`; `tests/test_docker_runtime_dependency_surface.py:111-164`
Reason: The Docker runtime dependency-surface guard now merges custom `--blocked-prefix` values with the default denylist instead of replacing it, reports a clearer Docker-enabled-environment failure when the CLI is unavailable, wraps non-timeout Docker command failures with bounded diagnostics, and locks those contracts with focused tests for subprocess kwargs, missing-binary behavior, failure-mode stdout/stderr separation, and default-prefix extension.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#pullrequestreview-4150757800 -> a36bf3747
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#discussion_r3120292588 -> a36bf3747
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#discussion_r3120292597 -> a36bf3747
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#discussion_r3120292608 -> a36bf3747
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#discussion_r3120292611 -> a36bf3747
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#discussion_r3120302253 -> a36bf3747

Disposition: FIXED
Commit: 6d06df396
Evidence: `docs/DEPENDENCY_MANAGEMENT.md:125-128`; `docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md:55-69`; `scripts/ci/check_docker_runtime_dependency_surface.py:159-161`
Reason: The docs now match the actual Docker runtime lock regeneration command and the current `min_versions` enforcement surfaces, while the runtime guard keeps the default-prefix merge explicit in code for the duplicate CodeRabbit policy finding.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#pullrequestreview-4150780636 -> 6d06df396
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#discussion_r3120312859 -> 6d06df396
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#discussion_r3120312866 -> 6d06df396
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1490#discussion_r3120312869 -> 6d06df396

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: `docs/review/PR_1490_FIXED_MAPPING.md:12-29`
- [ ] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed locally before PR open.
- [ ] `make verify` green on latest pushed head
  Evidence: local run reached `diff-cov` and ended with `make: *** [diff-cov] Terminated: 15`; rerun still required on the latest head.

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md` line 641 (`P1: Docker image budget and telemetry baseline`)
- `docs/roadmap/BACKLOG_LEDGER.md` line 540 (`P1: Shared Safety audit script after install-profile split`)
