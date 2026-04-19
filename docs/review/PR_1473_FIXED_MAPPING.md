# PR #1473 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:58-60`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after lane setup per repo governance.
Record every new review or bot disposition here before resolving threads on
GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1473#issuecomment-4275082729
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md` (`P1: Fix invalid Dependabot assignee configuration warning`)
Reason: The invalid Dependabot assignee remains a live repo-wide config defect in `.github/dependabot.yml`, but fixing that global automation surface is intentionally deferred out of the narrow `#1473` sentence-transformers remediation lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1473#pullrequestreview-4135421237
Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1473`
Reason: cubic reported no actionable issues on the live PR review surface; any later bot actionables must be added below before thread resolution.

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
  - the intended dependency delta is `sentence-transformers 5.4.0 -> 5.4.1`
    on the optional RAG vector profile only
  - the source Dependabot head introduces unrelated `cuda-*`, `nvidia-*`, and
    `triton` churn in `requirements-rag-vector.txt`
  - the active emergency wheel manifest still points at
    `sentence-transformers==5.4.0`
  - governance-only failures remain expected until this artifact and the PR
    body mirror are synchronized
- Canonical lane packet:
  `docs/orchestration/DEPENDABOT_PR_1473_SENTENCE_TRANSFORMERS_REMEDIATION_PACKET_2026-04-19.md`
