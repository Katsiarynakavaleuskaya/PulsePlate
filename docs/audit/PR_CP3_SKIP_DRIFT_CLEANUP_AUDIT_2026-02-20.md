# PR_CP3_SKIP_DRIFT_CLEANUP_AUDIT_2026-02-20

## Scope

- **IN:** CP3 follow-up on skip-heavy drift protocol in test
  infrastructure (`tests/feature_manifest.py`,
  `tests/test_feature_manifest_keys_used_guard.py`,
  `tests/test_cp3_skip_protocol_guard.py`,
  `tests/test_core_coverage_97_final.py`,
  `tests/test_missing_coverage_97_final.py`).
- **OUT:** Runtime/business logic, frontend/iOS, API behavior changes.

## Findings (Top causes of SKIP entropy)

1. Free-form `pytest.skip(...)` reasons are still widely present in
   legacy/high-noise suites (`tests/test_core_coverage_97_final.py`,
   `tests/test_simple_coverage_fixed.py`).
2. Existing protocol already had canonical helper
   (`require_feature(...)`), but lacked strict guard tests for reason
   format.
3. No direct regression test ensured
   `feature enabled + ImportError => FAIL` semantics.
4. CI signal could drift when helper semantics are changed without
   dedicated guard tests.
5. Skip evidence came from mixed suites; CP3 scope requires tightening
   only the feature-manifest protocol path.

## Free-form skip map (top-5 by match count)

1. `tests/test_core_coverage_97_final.py`: 20
2. `tests/test_bmi_visualization.py`: 16
3. `tests/test_simple_coverage_boost.py.backup`: 14
4. `tests/test_legacy_app_diff_coverage.py`: 11
5. `tests/test_plate_targets_micro_coverage.py`: 11

## Changes Applied

1. Added explicit protocol tests in
   `tests/test_feature_manifest_keys_used_guard.py`:
   - canonical skip reason prefix check,
   - `require_feature_or_raise` re-raise on enabled feature,
   - canonical skip on disabled feature.
2. Kept canonical helper category in `tests/feature_manifest.py` via constant:
   - `FEATURE_DISABLED_CATEGORY = "feature_disabled"`.
3. Added diff-based guard test:
   - `tests/test_cp3_skip_protocol_guard.py`
   - blocks newly added free-form `pytest.skip/xfail` in test diffs.
4. Migrated high-noise actionable suites from free-form skips to
   canonical helper flow:
   - `tests/test_core_coverage_97_final.py`
   - `tests/test_missing_coverage_97_final.py`

## Evidence

### Command 1

`pytest -q -rs | tee /tmp/pytest_rs_cp3.txt`

### Raw stdout excerpts 1

- `......................F................................................. [  4%]`
- `.............................................................ssssss.ss.. [ 71%]`
- `...............................FFF...................................... [ 72%]`

### Exit 1

- `exit_code: unknown` (process manually stopped at 85% to avoid
  long-running full-suite blocking during CP3 audit capture).

### Command 2

`rg -n "pytest\.skip|@pytest\.mark\.skip|@pytest\.mark\.skipif|skipif\(" tests`

### Raw stdout excerpts 2

- `tests/test_core_coverage_97_final.py:21: pytest.skip("core.exports_simple not available")`
- `tests/test_simple_coverage_fixed.py:186: pytest.skip("rag.simple_rag module not available")`
- `tests/test_openapi_determinism.py:29: pytest.skip("OpenAPI determinism test requires node/npm/make toolchain")`

### Exit 2

- `exit_code: 0`

### Command 3

`rg -n "require_feature\(|feature_disabled:" tests`

### Raw stdout excerpts 3

- `tests/feature_manifest.py:75: def require_feature(...) -> None:`
- `tests/feature_manifest.py:95: f"{FEATURE_DISABLED_CATEGORY}:{key} ..."`
- `tests/test_premium_week_app_coverage.py:42: require_feature("premium_week_router_mocking", reason=FEATURE_REASON)`

### Exit 3

- `exit_code: 0`

### Command 4

`pytest -q -rs ; echo "exit=$?"`

### Raw stdout excerpts 4

- `... [100%]`
- `FAILED tests/test_agent_docs_registry_guard.py::test_agent_specs_are_registered_in_index_and_context_map`
- `FAILED tests/test_realtime_ws_security.py::test_ws_rejects_unauthenticated_connection`
- `SKIPPED [20] tests/feature_manifest.py:97: feature_disabled:planner_engines ...`
- `exit=1`

### Exit 4

- `exit_code: 0` (shell command completed); embedded pytest status: `exit=1`.

## File:line Anchors

- `tests/feature_manifest.py:22`
- `tests/feature_manifest.py:75`
- `tests/feature_manifest.py:95`
- `tests/test_feature_manifest_keys_used_guard.py:29`
- `tests/test_feature_manifest_keys_used_guard.py:38`
- `tests/test_feature_manifest_keys_used_guard.py:48`
- `tests/test_cp3_skip_protocol_guard.py:1`
- `tests/test_core_coverage_97_final.py:5`
- `tests/test_missing_coverage_97_final.py:9`

## Decision Log

- Keep CP3 change minimal and protocol-focused (test infra only).
- Do not mass-convert all free-form skips in this PR to avoid scope creep.
- Enforce deterministic failure semantics where feature is enabled but
  import fails.

## DoD

- Canonical skip prefix is guarded by test.
- `feature enabled + ImportError => FAIL` is guarded by test.
- New CP3 audit evidence is recorded with command + raw output + exit
  status.
