# PR #1480 — Fixed in Commit Mapping (canonical)

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480
Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480`
Reason: At artifact initialization time the live PR surface had no actionable human or bot review threads yet; any later actionables must be appended here before thread resolution.

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

- Hotfix intent:
  - restore `mypy` from `1.20.1` to `1.20.0`
  - keep `ruff` at `0.15.11`
  - repair the immediate post-merge `main` failure in `Frontend CI`
- Main failure truth captured before this PR:
  - `Frontend CI #5596` failed on merge commit `6a6481ce0cb73029e20eb5ac745b599f8e2b84df`
  - failing step: `Install backend dependencies`
  - blocker: `mypy==1.20.1` had no matching distribution available for the runner environment
- Scope is intentionally narrow:
  - `requirements-dev.in`
  - `requirements-dev.txt`
  - `requirements-lock.txt`
- Live-session constraint:
  - local shell preflight / `make verify` could not be executed in this Codex thread because exec process creation is unavailable
