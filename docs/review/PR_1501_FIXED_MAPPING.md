# PR #1501 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Mandatory wait-window satisfied (final check pass completed, then waited >=1 review cycle after latest bot/review activity)
  Evidence: pending initial review and current-head CI cycle for PR `#1501`.
- [ ] Current-head CI is green for PR branch head
  Evidence: pending first branch-head `CI` cycle for PR `#1501`.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending first branch-head `CI` cycle for PR `#1501`.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending initial review cycle.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: initial bot state only contains the draft-mode CodeRabbit skip notice; re-check after the first advisory review pass.
- [x] Pre-commit green on latest pushed head
  Evidence: commit `453660117cfe21abea760a6fe3b4ccbbe371d2a2` and the subsequent push both passed repo hooks, including frontend tests, backend tests, and security hooks.
- [x] `make verify` green on validated remediation head
  Evidence: `make verify` completed through `verify-env`, lint, mypy, and `test-fast`; the terminal session was then recovered by rerunning `make diff-cov`, which passed with `No lines with coverage information in this diff.` and no changed-line coverage failures.

## Notes

- Narrow remediation scope:
  - keep `CI` / `test-main (3.12, 60)` job identity unchanged
  - exclude `serial` tests from Python `3.12` xdist and run that cohort in a sequential tail inside the same job
  - keep Python `3.13` on its existing sequential fallback
  - remove the Storybook addon carrier for Dependabot alert `#117` without a `uuid@14` override or Storybook major migration
- Live evidence anchors:
  - `main` run `24771474555` / job `72483372336`
  - later late-zone failure run `24799632664` / job `72578492861`
  - green nightly comparator `24760590280`
- Canonical lane packet:
  `docs/orchestration/MAINLINE_CI_XDIST_ROOT_CAUSE_AND_UUID117_PACKET_2026-04-23.md`
