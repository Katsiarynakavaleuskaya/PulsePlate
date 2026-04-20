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

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1474#issuecomment-4275090332
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md` (`P1: Fix invalid Dependabot assignee configuration warning`)
Reason: The invalid Dependabot assignee remains a live repo-wide config defect in `.github/dependabot.yml`, but fixing that global automation surface is intentionally deferred out of the narrow `#1474` transformers remediation lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1474#pullrequestreview-4135424346
Disposition: NOT-A-BUG
Evidence: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`
Reason: The canonical governance contract allows a NOT-A-BUG disposition when a review leaves no actionable defect and the source PR surface itself contains no inline or parent-thread fix request to implement in the replacement lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#pullrequestreview-4139907864
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-dependency-fallback-artifact-dedup`
Reason: Sourcery identified maintainability drift in duplicated fallback version tuples and brittle line-range evidence. That follow-up is valid but intentionally deferred out of the narrow blocker-fix lane for `#1485`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#pullrequestreview-4139931770
Disposition: FIXED
Commit: e1ad74fec
Evidence: `docs/orchestration/DEPENDABOT_PR_1474_TRANSFORMERS_REMEDIATION_PACKET_2026-04-20.md:15-18`
Reason: cubic found a valid portability issue: the packet embedded a machine-specific absolute worktree path. The canonical packet now uses a portable local worktree slug instead of an absolute filesystem path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#discussion_r3110616657
Disposition: FIXED
Commit: e1ad74fec
Evidence: `docs/orchestration/DEPENDABOT_PR_1474_TRANSFORMERS_REMEDIATION_PACKET_2026-04-20.md:15-18`
Reason: cubic found the actionable inline review comment for the same packet portability issue; fixed in the same docs-only follow-up commit as the review summary above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#pullrequestreview-4140030022
Disposition: FIXED
Commit: ff6bdcb81
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:3649-3667`
Reason: CodeRabbit identified a valid governance issue: the new dependency follow-up remained in the `### P1` section despite `Priority: P2`. The backlog item now lives under the canonical `### P2` section.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#discussion_r3110693031
Disposition: FIXED
Commit: ff6bdcb81
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:3649-3667`
Reason: CodeRabbit identified the actionable inline version of the same placement issue; fixed by moving the backlog item into the `### P2` section.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#pullrequestreview-4140058144
Disposition: FIXED
Commit: ff6bdcb81
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:3649-3667`
Reason: cubic found the same priority-ordering defect in the backlog ledger. The new follow-up item is now placed under `### P2`, matching its declared priority.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#discussion_r3110715555
Disposition: FIXED
Commit: ff6bdcb81
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:3649-3667`
Reason: cubic identified the actionable inline version of the same ledger ordering issue; fixed in the same commit that moved the entry into the `### P2` section.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#pullrequestreview-4140209667
Disposition: FIXED
Commit: 1780f9c6a
Evidence: `docs/review/PR_1485_FIXED_MAPPING.md:16-26`
Reason: CodeRabbit identified two valid governance-format issues in the canonical mapping artifact: the heading level needed to match the mirror contract exactly, and the earlier NOT-A-BUG evidence needed a concrete contract reference instead of a bare PR URL.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1485#discussion_r3110836357
Disposition: FIXED
Commit: 1780f9c6a
Evidence: `docs/review/PR_1485_FIXED_MAPPING.md:23-26`
Reason: CodeRabbit identified the actionable inline proof-format issue for the NOT-A-BUG entry; the evidence now points to a concrete contract range instead of a bare PR URL.

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
