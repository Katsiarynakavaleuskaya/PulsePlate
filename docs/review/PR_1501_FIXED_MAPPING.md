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

Disposition: FIXED
Commit: 8ec8db3a1efb7f0b2bfbd9bcc8d945b20162740c
Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py:245-251`; `frontend/.storybook/main.ts:7-8`
Reason: The follow-up commit tightens the workflow contract so the serial-only JUnit path is unique to the Python `3.12` serial shard and adds an inline Storybook note that explains why the addon-actions carrier stays excluded for Dependabot alert `#117`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1501#pullrequestreview-4158647897 -> 8ec8db3a1efb7f0b2bfbd9bcc8d945b20162740c

Disposition: FIXED
Commit: 8ec8db3a1efb7f0b2bfbd9bcc8d945b20162740c
Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py:248-251`
Reason: The contract test now proves that `tests/results-serial.xml` appears only once and is not reused in the Python `3.13` or default lanes, closing the inline Sourcery suggestion about report-path collisions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1501#discussion_r3127545479 -> 8ec8db3a1efb7f0b2bfbd9bcc8d945b20162740c

Disposition: FIXED
Commit: 8ec8db3a1efb7f0b2bfbd9bcc8d945b20162740c
Evidence: `.github/workflows/ci.yml:1158-1165`
Reason: The JUnit artifact upload step now publishes both `tests/results.xml` and `tests/results-serial.xml`, so the Python `3.12` serial shard is no longer omitted from uploaded reports.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1501#discussion_r3127548278 -> 8ec8db3a1efb7f0b2bfbd9bcc8d945b20162740c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1501#pullrequestreview-4158652006 -> 8ec8db3a1efb7f0b2bfbd9bcc8d945b20162740c

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
  Evidence: pending resolution of the Sourcery and Codex / CodeRabbit threads after this mapping update lands on current head.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: CodeRabbit is still processing the latest head; re-check after the current advisory review cycle finishes.
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
