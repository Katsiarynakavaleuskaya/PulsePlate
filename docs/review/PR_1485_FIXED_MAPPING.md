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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#pullrequestreview-4139907864
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-dependency-fallback-artifact-dedup`
Reason: Sourcery identified maintainability drift in duplicated fallback version tuples and brittle line-range evidence. That follow-up is valid but intentionally deferred out of the narrow blocker-fix lane for `#1485`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#pullrequestreview-4139931770 -> e1ad74fec
Disposition: FIXED
Evidence: `docs/orchestration/DEPENDABOT_PR_1474_TRANSFORMERS_REMEDIATION_PACKET_2026-04-20.md:15-18`
Reason: cubic found a valid portability issue: the packet embedded a machine-specific absolute worktree path. The canonical packet now uses a portable local worktree slug instead of an absolute filesystem path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#discussion_r3110616657 -> e1ad74fec
Disposition: FIXED
Evidence: `docs/orchestration/DEPENDABOT_PR_1474_TRANSFORMERS_REMEDIATION_PACKET_2026-04-20.md:15-18`
Reason: cubic found the actionable inline review comment for the same packet portability issue; fixed in the same docs-only follow-up commit as the review summary above.

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
- current-head `build-and-test` exposed a locked-install fallback drift for
  `ruff==0.15.11` from `requirements-dev.txt`, inherited from `origin/main`;
  on `20 April 2026` the user explicitly approved fixing that manifest parity
  blocker inside this replacement PR as a narrow follow-up
- Canonical lane packet:
  `docs/orchestration/DEPENDABOT_PR_1474_TRANSFORMERS_REMEDIATION_PACKET_2026-04-20.md`
