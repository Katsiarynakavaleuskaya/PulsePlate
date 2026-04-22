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

Disposition: FIXED
Commit: 4ac7cc218
Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py:51-63`, `tests/test_ci_workflow_pr_size_governance_contract.py:222-248`
Reason: The workflow contract test now extracts each `if/elif/else` shell branch and proves the interpreter-specific xdist mapping directly instead of only checking for string presence anywhere in the job.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1494#discussion_r3123721053 -> 4ac7cc218

Disposition: FIXED
Commit: 4ac7cc218
Evidence: `docs/orchestration/MAINLINE_CI_XDIST_WORKER_STABILITY_PACKET_2026-04-22.md:29`
Reason: The packet wording now states that the nightly run completed with status `success`, removing the awkward phrasing without widening lane scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1494#discussion_r3123721058 -> 4ac7cc218

Disposition: NOT-A-BUG
Evidence: `AGENTS.md:371-382`; `docs/orchestration/MAINLINE_CI_XDIST_WORKER_STABILITY_PACKET_2026-04-22.md:38-56`
Reason: Coordinator-owned lane packets define the mandatory executable role order for that lane. This packet intentionally preserves the user-approved `dev-operator` evidence pass before the architecture/backend/security sequence, and the canonical post-open `qa-engineer-agent -> bug-hunter` review pass remains intact.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1494#discussion_r3123721937

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
