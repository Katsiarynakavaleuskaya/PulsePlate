# PR #1490 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

No review threads are mapped yet. Add every actionable human/bot thread here with
its disposition before resolving it on GitHub.

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
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending.
- [ ] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed locally before PR open.
- [ ] `make verify` green on latest pushed head
  Evidence: local run reached `diff-cov` and ended with `make: *** [diff-cov] Terminated: 15`; rerun still required on the latest head.

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-docker-image-budget-telemetry`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock`
