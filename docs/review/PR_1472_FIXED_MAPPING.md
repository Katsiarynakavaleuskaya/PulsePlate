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
Commit: 1e9cf765e
Evidence: `requirements.txt:39-41`, `requirements-lock.txt:244`, `requirements-lock.txt:480`
Reason: The corrective remediation removes the stray runtime CUDA / Triton churn from `requirements.txt`, restores `requirements-lock.txt` to the repo's combined-lock contract, and preserves the intended `mypy` / `ruff` version bump only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1472#discussion_r3106217704 -> 1e9cf765e
Disposition: FIXED
Commit: 1e9cf765e
Evidence: `requirements.txt:39-41`, `requirements-lock.txt:244`, `requirements-lock.txt:480`
Reason: The inline cubic issue is resolved by removing the unintended runtime GPU dependency drift from `requirements.txt` while keeping the PR scoped to the quality lockfile bump represented in `requirements-lock.txt`.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [x] Current-head CI is green for PR branch head
  Evidence: `gh pr checks 1472` on head `a3a2f5e58` shows current-head `coverage-pr`, `diff-coverage`, `lint`, `security`, `smoke`, `test-pr (3.13)`, governance lanes, and advisory review bots as passing.
- [x] Required checks complete (no pending jobs)
  Evidence: `GH_TOKEN="$(gh auth token)" GITHUB_TOKEN="$(gh auth token)" python3 scripts/orchestration/check_merge_ready.py --pr-number 1472 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth` passed and reported no pending current-head blockers.
- [x] All review threads resolved on GitHub after disposition updates
  Evidence: `gh api graphql` reports cubic thread `PRRT_kwDOPi-pts57_SvJ` as `isResolved=true`.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: strict merge wrapper passed `review-threads-disposition` with `OK: All 1 resolved review threads have Disposition + proof and commit-after-comment.`
- [x] Pre-commit green on latest pushed head
  Evidence: local `pre-commit run --all-files` passed before pushing head `a3a2f5e58`.
- [x] `make verify` green on latest pushed head
  Evidence: local `make verify` passed end-to-end on the corrective remediation head before the final push sequence.

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
