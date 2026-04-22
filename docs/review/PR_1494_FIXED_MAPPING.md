# PR #1494 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:58-60`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after PR open per repo governance. Record
every new human or bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending first branch-head `CI` cycle for PR `#1494`.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending first branch-head `CI` cycle for PR `#1494`.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: no review threads yet; re-evaluate after first review/bot cycle.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: no actionable bot comments are mapped yet.
- [x] Pre-commit green on validated remediation head
  Evidence: `pre-commit run --all-files` passed before opening PR `#1494`.
- [ ] `make verify` green on validated remediation head
  Evidence: not run yet on this draft remediation head.

## Notes

- Narrow remediation scope:
  - keep `test-main` job identity unchanged
  - reduce Python `3.12` from `-n 4` to `-n 2` with `--dist=loadscope`
  - keep Python `3.13` on its existing `-p no:xdist` fallback
- Live evidence anchors:
  - user-reported signature: `[gw1] node down: Not properly terminated`
  - `main` run `24771474555`
  - `test-main (3.12, 60)` job `72483372336`
  - `test-main (3.11, 60)` job `72483386535`
  - green nightly reference `24760590280`
- Local validation already collected:
  - `python3 scripts/orchestration/check_preflight.py --path ...` passed
  - `python3 scripts/orchestration/check_agent_consistency.py` passed
  - `./.venv/bin/pytest -q tests/test_ci_workflow_pr_size_governance_contract.py tests/test_python_supply_chain_controls.py tests/test_current_head_pr_checks.py` passed
  - `make validate-changed` passed
  - `pre-commit run --all-files` passed
- Canonical lane packet:
  `docs/orchestration/MAINLINE_CI_XDIST_WORKER_STABILITY_PACKET_2026-04-22.md`
