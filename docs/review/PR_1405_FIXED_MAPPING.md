# PR 1405 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub only after mapping per `AGENTS.md`.

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#issuecomment-4231850181 -> 4cd8a3465
Disposition: FIXED
Commit: 4cd8a3465
Evidence: `.github/workflows/ci.yml` widened iOS push predicates to include `refs/heads/feature/`; `tests/test_ci_workflow_pr_size_governance_contract.py` added alias guard.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#pullrequestreview-4095309985 -> 1d59be0ae
Disposition: FIXED
Commit: 1d59be0ae
Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` now uses parsed workflow branches + membership assertions; `scripts/ci/install_locked_python_requirements.py` stages exact constraint pins once per staging pass; `tests/test_install_locked_python_requirements.py` covers the single-read path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069803570 -> 0883a87e5
Disposition: FIXED
Commit: 0883a87e5
Evidence: `.github/workflows/ci.yml` now runs unit tests inside `ios-tests`; `ios-ui-smoke` remains UI-only; `tests/test_ci_workflow_pr_size_governance_contract.py` guards the split.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069803573 -> 20e5127a2
Disposition: FIXED
Commit: 20e5127a2
Evidence: `docs/review/PR_1405_FIXED_MAPPING.md` now records internal review and bot fixes explicitly; merge-readiness bot-mapping checkbox remains unchecked until the final pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#pullrequestreview-4095329850
Disposition: NOT-A-BUG
Evidence: This summary review does not introduce independent work beyond `discussion_r3069803570`, `discussion_r3069803573`, and the already-fixed nit-level follow-ups landed in `1d59be0ae`.
Reason: The actionable parts of this summary review are already mapped as separate inline review comments, so the review summary itself does not require an additional code change.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069811515 -> a4a3f8ddf
Disposition: FIXED
Commit: a4a3f8ddf
Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` now asserts full push-event routing tokens for `test-feature` and `coverage-feature`, plus smoke/contract/coverage step wiring.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069811517 -> a4a3f8ddf
Disposition: FIXED
Commit: a4a3f8ddf
Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` now asserts `pull_request`, `feat/`, `fix/`, `feature/`, and `main` tokens for both `ios-tests` and `ios-ui-smoke`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#pullrequestreview-4095339675 -> a4a3f8ddf
Disposition: FIXED
Commit: a4a3f8ddf
Evidence: The summary review's two actionable findings are both closed by the strengthened workflow-contract assertions landed in `a4a3f8ddf`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069786949 -> a4a3f8ddf
Disposition: FIXED
Commit: a4a3f8ddf
Evidence: `tests/test_ci_workflow_pr_size_governance_contract.py` asserts parsed YAML branch membership via `_load_ci_workflow()` and `issubset(...)`, so workflow formatting changes no longer make the test brittle.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069786946
Disposition: NOT-A-BUG
Evidence: Coverage merge truth is still enforced by the canonical PR lane `diff-coverage` job in `.github/workflows/ci.yml` plus the repo hard gate in `AGENTS.md`; the feature-push fast-feedback lane only publishes coverage artifacts and is intentionally not the merge blocker.
Reason: This comment assumes the feature-push fast-feedback job is itself the merge gate, but in this repository merge readiness is decided by the canonical PR lane and `diff-coverage`, not by the non-blocking feature-branch push lane.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#discussion_r3069834607
Disposition: FIXED
Commit: PENDING
Evidence: `.github/workflows/ci.yml` now fails closed when `../scripts/ios_test_targets.sh` returns an empty `ONLY_TESTING` list, and `tests/test_ci_workflow_pr_size_governance_contract.py` asserts the new error guard.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1405#pullrequestreview-4095368028
Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-ci-contract-risk-helper-extraction`
Evidence: The inline correctness bug from this review is fixed separately in `discussion_r3069834607`; the remaining suite-map centralization request is intentionally tracked as follow-up refactor work.

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
