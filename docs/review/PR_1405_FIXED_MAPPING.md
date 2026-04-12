# PR 1405 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub only after mapping per `AGENTS.md`.

## Fixed in Commit Mapping
- Internal review lane: feature/* push did not widen iOS push gates
  - Disposition: FIXED
  - Commit: `4cd8a3465`
  - Evidence: `.github/workflows/ci.yml` widened iOS push predicates to include `refs/heads/feature/`; `tests/test_ci_workflow_pr_size_governance_contract.py` added alias guard.
  - Thread URL: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#issuecomment-4231850181`
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#pullrequestreview-4095309985` -> `1d59be0ae`
  - Disposition: FIXED
  - Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` now uses parsed workflow branches + membership assertions; `scripts/ci/install_locked_python_requirements.py` stages exact constraint pins once per staging pass; `tests/test_install_locked_python_requirements.py` covers the single-read path.
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069803570` -> `0883a87e5`
  - Disposition: FIXED
  - Evidence: `.github/workflows/ci.yml` now runs unit tests inside `ios-tests`; `ios-ui-smoke` remains UI-only; `tests/test_ci_workflow_pr_size_governance_contract.py` guards the split.
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069803573` -> `20e5127a2`
  - Disposition: FIXED
  - Evidence: `docs/review/PR_1405_FIXED_MAPPING.md` now records internal review and bot fixes explicitly; merge-readiness bot-mapping checkbox remains unchecked until the final pass.
- `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#pullrequestreview-4095329850`
  - Disposition: NOT-A-BUG
  - Evidence: This summary review does not introduce independent work beyond `discussion_r3069803570`, `discussion_r3069803573`, and the already-fixed nit-level follow-ups landed in `1d59be0ae`.

## Merge Readiness
- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`

### Scope Notes
- This PR is intentionally scoped to CI semantics only for feature/fix push lanes plus follow-up review fixes that preserve that scope.
- Post-review follow-up commits `1d59be0ae` and `0883a87e5` close workflow-contract brittleness and restore the intended blocking/non-blocking iOS split.
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
