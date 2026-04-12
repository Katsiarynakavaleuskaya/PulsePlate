# PR 1405 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub only after mapping per `AGENTS.md`.

## Fixed in Commit Mapping
- No actionable review comments

## Merge Readiness
- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`

### Scope Notes
- This PR is draft and intentionally scoped to CI semantics only for feature/fix push lanes.
- Current live CI also shows an unrelated `build-and-test` locked-install failure on Python 3.13 package resolution (`cryptography` / `ruff`), which does not originate from this PR's workflow-routing changes.
- PR merge-truth remains unchanged: `test-pr` and `test-main` semantics are intentionally preserved in this lane.

### Local Verification
- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pytest -q tests/test_ci_risk_profile.py tests/test_ci_workflow_pr_size_governance_contract.py tests/test_current_head_pr_checks.py tests/test_python_supply_chain_controls.py`
- `VENV_PYTHON=.venv/bin/python make validate-min`
- `pre-commit run --all-files`
- `VENV_PYTHON=.venv/bin/python make verify`

## Deferred / Follow-ups
- `docs/roadmap/BACKLOG_LEDGER.md` keeps the follow-up items for `test-main (3.13)` optimization, canonical shard-map redesign, and install-profile slimming evaluation.
