# PR #1472 — Fixed in Commit Mapping (canonical)

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1472#issuecomment-4275078933
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md` (`P1: Fix invalid Dependabot assignee configuration warning`)
Reason: The invalid Dependabot assignee remains a live repo-wide config defect in `.github/dependabot.yml`, but fixing that global automation surface is intentionally deferred out of the narrow `#1472` quality remediation lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1472#pullrequestreview-4135421139 -> 1e9cf765e
Disposition: FIXED
Evidence: `requirements.txt:39-41`, `requirements-lock.txt:244`, `requirements-lock.txt:480`
Reason: The corrective remediation removes the stray runtime CUDA / Triton churn from `requirements.txt`, restores `requirements-lock.txt` to the repo's combined-lock contract, and preserves the intended `mypy` / `ruff` version bump only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1472#discussion_r3106217704 -> 1e9cf765e
Disposition: FIXED
Evidence: `requirements.txt:39-41`, `requirements-lock.txt:244`, `requirements-lock.txt:480`
Reason: The inline cubic issue is resolved by removing the unintended runtime GPU dependency drift from `requirements.txt` while keeping the PR scoped to the quality lockfile bump represented in `requirements-lock.txt`.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head

## Notes

- Initial lane entry truth:
  - the quality bump itself is `mypy 1.20.0 -> 1.20.1` and `ruff 0.15.10 -> 0.15.11`
  - live cubic review identifies unconditional CUDA pins in `requirements.txt`
    as the active portability defect
  - governance-only failures remain expected until this artifact and the PR
    body mirror are synchronized
- Local latest-head evidence already collected:
  - `pre-commit run --all-files` passed
  - `make verify` passed end-to-end on the remediation head
- Current review-thread status on the latest pushed head:
  - `gh api graphql` reports the cubic review thread
    (`PRRT_kwDOPi-pts57_SvJ`) as `isResolved=true`
- Canonical lane packet:
  `docs/orchestration/DEPENDABOT_PR_1472_QUALITY_GROUP_REMEDIATION_PACKET_2026-04-19.md`
