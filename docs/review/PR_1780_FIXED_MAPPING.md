# PR #1780 - Fixed in Commit Mapping

**PR:** test(food-data): stabilize PR17 coverage gates
**Branch:** `codex/food-data-pr17-main-coverage-stabilization`

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [x] Fixed in commit mapping initialized

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e4dac0c28
Evidence: Added deterministic PR16/PR17 food-source governance tests for malformed payloads, typed field rejection, expected reference drift, source-policy drift, missing regional handoff entries, candidate matrix drift, malformed artifact/report handling, and file-only CLI/report invariants. Local proof: focused pytest passed for `tests/test_food_source_preference_mapping_closeout.py` and `tests/test_food_source_regional_catalog_identity.py`; focused coverage for the two affected modules improved from `83.61%` to `95.32%`; `tests/test_repo_policy_guards.py` passed; CLI JSON smokes passed for both PR16 and PR17 gates.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1780 -> e4dac0c28

## Premortem Disposition

- FIXED: Coverage was restored with behavior-targeted negative tests for real validator/report branches, not empty coverage calls.
- FIXED: Fail-closed behavior is preserved by tests that reject unsafe flags, malformed inputs, source-policy drift, and provider/candidate authority promotion.
- NOT-A-BUG: No runtime, provider, OpenAPI, DB, cache, source authority, product display, or nutrition authority changes are required for this merged-main coverage fallout.
- DEFERRED: PR18 `regional_catalog_provider_terms_matrix` remains blocked until PR #1780 merges and current-head `main` is terminal green.

## Validation

- `python3 scripts/orchestration/check_preflight.py` - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_food_source_preference_mapping_closeout.py tests/test_food_source_regional_catalog_identity.py` - PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_food_source_preference_mapping_closeout.py tests/test_food_source_regional_catalog_identity.py tests/test_repo_policy_guards.py` - PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m scripts.food_source_preference_mapping_closeout --json` - PASS
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m scripts.food_source_regional_catalog_identity --json` - PASS
- `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python` - PASS; branch-diff selector reported no selected Python files, so focused pytest is the behavioral signal.
- `pre-commit run --all-files` - PASS after black hook reformat.
- Commit hook with root `.venv` activated - PASS.
- Pre-push hook - PASS, including pip-audit, backend tests, full-repo Bandit.

## Full Verify Deferral

Full local `make verify` is deferred for this narrow governance/test-only stabilization per operator instruction. Merge readiness requires PR current-head CI parity, including the coverage threshold that failed on merged `main`.

## Post-Open Review

- Post-open bootstrap packet: `artifacts/orchestration/task_packets/4b9a408e9c61.json` (local gitignored artifact).
- Mandatory post-open QA -> bug-hunter pass: pending.
- CodeRabbit pass: pending.
- Codex Security diff-scoped pass: pending.
- Current-head checks: pending.
- Review-thread disposition guard: pending.

## Experiment Runner

Not applicable. Experiment Runner did not materially contribute to this commit, so no co-author trailer is required.
