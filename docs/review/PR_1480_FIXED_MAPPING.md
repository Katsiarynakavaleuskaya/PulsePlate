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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#pullrequestreview-4136381333 -> f8cfa3a999787e161caeadb9bd8d5378e705f970
Disposition: FIXED
Evidence: `requirements-dev.in:29`
Reason: Sourcery requested a stricter mypy constraint so future lock refreshes cannot drift back to the broken `1.20.1` patch; the exact pin landed in commit `f8cfa3a999787e161caeadb9bd8d5378e705f970`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#pullrequestreview-4136383224 -> f8cfa3a999787e161caeadb9bd8d5378e705f970
Disposition: FIXED
Evidence: `requirements-dev.in:29`
Reason: cubic identified that `~=1.20.0` still permits `1.20.1`; the exact pin landed in commit `f8cfa3a999787e161caeadb9bd8d5378e705f970`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#discussion_r3107311707 -> f8cfa3a999787e161caeadb9bd8d5378e705f970
Disposition: FIXED
Evidence: `requirements-dev.in:29`
Reason: cubic inline review requested `mypy==1.20.0`; the exact pin landed in commit `f8cfa3a999787e161caeadb9bd8d5378e705f970`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480#discussion_r3107312193 -> f8cfa3a999787e161caeadb9bd8d5378e705f970
Disposition: FIXED
Evidence: `requirements-dev.in:29`
Reason: Codex inline review raised the same recurrence risk; the exact pin landed in commit `f8cfa3a999787e161caeadb9bd8d5378e705f970`.

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

- Current PR metadata snapshot captured before the exact-pin remediation:
  - PR URL: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1480`
  - PR head branch: `codex/hotfix-mypy-1.20.0-main`
  - Current head SHA before the packet / fix commit:
    `2ca096a1354990976f450da9d32d27ea15b11147`
  - Current pushed head after local remediation and mapping refresh:
    `7b9151b17e3925ed825cc0300eb9866a121de161`
- Current-head CI truth must ignore superseded cancelled runs and use only the
  latest head run for `7b9151b17e3925ed825cc0300eb9866a121de161`.
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
- Exact-pin evidence:
  - `requirements-dev.in:29` -> `mypy==1.20.0`
  - `requirements-dev.txt:110` -> `mypy==1.20.0`
  - `requirements-lock.txt:227` -> `mypy==1.20.0`
- Coordinator packet:
  - `docs/orchestration/DEPENDABOT_PR_1480_FRONTEND_CI_MYPY_HOTFIX_PACKET_2026-04-19.md`
- Live-session local evidence available in this thread:
  - `python3 scripts/orchestration/check_preflight.py` passed
  - `python3 scripts/orchestration/check_agent_consistency.py` passed
  - `pre-commit run --all-files` passed before and after the exact-pin remediation
  - `make verify` passed on the pushed head `7b9151b17e3925ed825cc0300eb9866a121de161`
  - PR body mirror was refreshed on the pushed head `7b9151b17e3925ed825cc0300eb9866a121de161`
