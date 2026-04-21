# PR #1487 — Fixed in Commit Mapping (canonical)

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

- No actionable review comments

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending branch-head workflow results after draft PR open and manual
  nightly dispatch.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending `check_merge_ready.py --require-auth` pass after branch-head
  CI completes.
- [x] All review threads resolved on GitHub after disposition updates
  Evidence: GraphQL review-thread query on 21 April 2026 returned zero review
  threads for PR `#1487`.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: only non-actionable bot surface remains on 21 April 2026
  (`CodeRabbit review skipped`, `Sourcery` reviewer guide, and informational
  Codecov coverage report); no actionable bot thread is open or unmapped.
- [x] Pre-commit green on validated remediation head
  Evidence: local `pre-commit run --all-files` passed before pushing the
  code-bearing remediation head `2b6e65b77`; later heads are governance-only
  follow-through.
- [x] `make verify` green on validated remediation head
  Evidence: local `make verify` passed end-to-end on code-bearing remediation
  head `2b6e65b77`; later heads are governance-only follow-through.

## Notes

- Live failure references for this lane:
  - `Nightly Full Tests` run `24704500078` (`tests` job `72254565349`)
  - `Nightly Tests` run `24704528938` (`test (1)` job `72254656999`)
- Narrow remediation scope:
  - align `requirements-dev.in`, `requirements-dev.txt`, and
    `requirements-lock.txt` to `ruff 0.15.11`
  - keep workflow YAML unchanged unless branch-head validation proves the pin
    alignment is insufficient
- Local latest-head evidence already collected:
  - `python3 scripts/orchestration/check_preflight.py` passed
  - `python3 scripts/orchestration/check_agent_consistency.py` passed
  - `pytest -q tests/test_install_locked_python_requirements.py` passed
  - `pytest -q tests/test_python_supply_chain_controls.py` passed
  - runtime-dev approved-proxy preflight passed via
    `scripts/ci/install_locked_python_requirements.py --preflight-only`
  - `pre-commit run --all-files` passed
  - `make verify` passed end-to-end
- Canonical lane packet:
  `docs/orchestration/MAINLINE_NIGHTLY_RUFF_BOOTSTRAP_REMEDIATION_PACKET_2026-04-21.md`
