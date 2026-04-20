# PR #1485 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:58-60`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after replacement-PR creation.
Record every new review or bot disposition here before resolving threads on
GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1474#issuecomment-4275090332
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md` (`P1: Fix invalid Dependabot assignee configuration warning`)
Reason: The invalid Dependabot assignee remains a live repo-wide config defect in `.github/dependabot.yml`, but fixing that global automation surface is intentionally deferred out of the narrow `#1474` transformers remediation lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1474#pullrequestreview-4135424346
Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1474`
Reason: cubic identified no actionable issues on the live source PR review surface; any later bot or reviewer actionables on the replacement PR must be added below before thread resolution.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending
- [ ] Required checks complete (no pending jobs)
  Evidence: pending
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending
- [ ] Pre-commit green on latest pushed head
  Evidence: pending
- [ ] `make verify` green on latest pushed head
  Evidence: pending

## Notes

- Initial lane entry truth:
  - the intended dependency delta is `transformers 5.5.3 -> 5.5.4` on the optional RAG vector profile only
  - the source Dependabot head introduces unrelated `cuda-*`, `nvidia-*`, and `triton` churn in `requirements-rag-vector.txt`
  - the active emergency wheel manifest still points at `transformers==5.5.3`
  - governance-only failures remain expected until this artifact and the PR body mirror are synchronized
- Canonical lane packet:
  `docs/orchestration/DEPENDABOT_PR_1474_TRANSFORMERS_REMEDIATION_PACKET_2026-04-20.md`
