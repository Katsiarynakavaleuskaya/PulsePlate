# SKIPPED Tests Classification Audit (PR-728)

Date: 13 February 2026 (America/New_York)
Scope: Backend test files from the confirmed skip run (84 skipped tests)
Type: docs-only audit (no runtime changes)

Update: 13 February 2026 (America/New_York)
This document preserves the original PR-728 snapshot. The previous
"app import determinism skip fallback (4 skips)" is now resolved
(PR-729 merged on 13 February 2026), and ledger status is updated.

## 1) Objective

Classify current `SKIPPED` reasons into three architectural classes.
Promote only risky classes to immediate backlog work.

1. Intentional Feature Not In Scope
2. Drift / Contract Mismatch
3. Quality / Determinism / Guard Disabled

Policy basis:

- `AGENTS.md:58` (bad skip vs intentional skip policy)
- `AGENTS.md:64` (bad skips must be promoted to P0/P1)

## 2) Repo-Truth Evidence

Command used:

```bash
pytest -q -rs \
  tests/test_api.py \
  tests/test_app_coverage_unit_combined.py \
  tests/test_bayesian_test_analyzer.py \
  tests/test_coverage_final_boost.py \
  tests/test_database_apis_coverage.py \
  tests/test_direct_core_functions.py \
  tests/test_final_core_coverage.py \
  tests/test_final_coverage_97_boost.py \
  tests/test_food_apis_coverage_errors.py \
  tests/test_premium_targets_es_snapshots.py \
  tests/test_premium_week_app_coverage.py \
  tests/test_quick_coverage_boost.py \
  tests/test_remaining_modules.py \
  tests/test_repo_policy_guards.py \
  tests/test_shoplist_day_db_wiring.py \
  tests/test_targets_coverage_97.py \
  tests/test_update_manager_fixed.py \
  tests/test_zero_coverage_modules.py
```

Observed summary (grouped counts from `SKIPPED` lines):

- `57` -> module/symbol not available
- `5` -> test data precondition not met
- `4` -> app import determinism skip fallback (historical, now resolved)
- `4` -> async DB not configured
- `4` -> legacy negative tests marked skip
- `3` -> signature mismatch
- `2` -> no canonical equivalent yet
- `2` -> mocking complexity
- `1` -> guard skipped (`sys.modules`)
- `1` -> optional response field (`ui_labels`) not in contract
- `1` -> update manager path wrapper mismatch

Selected raw evidence anchors from current repo state:

- Import determinism guard (no skip fallback allowed): `tests/test_api.py:343`
- Import skip marker assertion: `tests/test_api.py:346`
- Disabled guard: `tests/test_repo_policy_guards.py:101`
- Async DB skip: `tests/test_shoplist_day_db_wiring.py:39`
- Canonical mismatch marker: `tests/test_app_coverage_unit_combined.py:83`
- `ui_labels` skip: `tests/test_premium_targets_es_snapshots.py:453`
- Signature mismatch skips: `tests/test_food_apis_coverage_errors.py:416`
- Signature mismatch skips: `tests/test_food_apis_coverage_errors.py:437`
- Current unified DB signature: `core/food_apis/unified_db.py:265`
- WHO targets contract (no `ui_labels`):
  `app/schemas/premium_contracts.py:109`

## 3) Classification Matrix

### 3.1 App import fallback skip (historical, resolved)

- Count: 4
- Class: Quality/Determinism
- Risk: Resolved
- Evidence: `tests/test_api.py:343`
- Action: Completed in PR-729.
  `tests/test_api.py` now enforces fail-not-skip policy and has a guard
  against reintroducing `pytest.skip("App import failed unexpectedly")`.

### 3.2 `sys.modules` guard disabled

- Count: 1
- Class: Quality/Guard
- Risk: High
- Evidence: `tests/test_repo_policy_guards.py:101`
- Action: Re-enable guard with controlled offender cleanup.

### 3.3 Async DB not configured

- Count: 4
- Class: Quality/Infra
- Risk: High
- Evidence: `tests/test_shoplist_day_db_wiring.py:39`
- Action: Add deterministic async DB matrix for tests or
  remove obsolete tests.

### 3.4 Data precondition skips

- Count: 5
- Class: Quality/Test design
- Risk: Medium
- Evidence: `tests/test_targets_coverage_97.py:61`
- Action: Replace precondition skip with deterministic fixtures.

### 3.5 Mocking complexity skips

- Count: 2
- Class: Quality/Test seam
- Risk: Medium
- Evidence: `tests/test_premium_week_app_coverage.py:41`
- Action: Use existing endpoint seam in `legacy_app.py`.

### 3.6 Legacy negative-injection skips

- Count: 4
- Class: Quality/Test validity
- Risk: Medium
- Evidence: `tests/test_food_apis_coverage_errors.py:303`
- Action: Rewrite to deterministic error-path assertions.

### 3.7 Signature mismatch skips

- Count: 3
- Class: Drift/Contract
- Risk: Medium
- Evidence: `tests/test_food_apis_coverage_errors.py:416`
- Action: Align tests to canonical signatures.

### 3.8 Module/symbol not available (broad)

- Count: 57
- Class: Drift (mixed with product scope)
- Risk: Medium
- Evidence: `tests/test_database_apis_coverage.py:62`
- Action: Split into canonical drift fixes and explicit
  product out-of-scope decisions.

### 3.9 Removed-without-equivalent

- Count: 2
- Class: Intentional/Decision pending
- Risk: Low
- Evidence: `tests/test_app_coverage_unit_combined.py:83`
- Action: Product decision, remove obsolete tests or restore
  canonical equivalent.

### 3.10 Optional response field (`ui_labels`)

- Count: 1
- Class: Intentional/Contract decision
- Risk: Low
- Evidence: `tests/test_premium_targets_es_snapshots.py:453`
- Action: Decide whether to add field to contract or remove
  obsolete assertion.

### 3.11 Path wrapper mismatch

- Count: 1
- Class: Drift/Test mismatch
- Risk: Low
- Evidence: `tests/test_update_manager_fixed.py:129`
- Action: Update test to `_PatchablePathWrapper` contract.

## 4) Priority Decision (Execution Order)

Execution order approved for next PRs:

1. P0: Import Determinism (closed in PR-729, merged 13 February 2026)
2. P1: Guard Re-enable (`sys.modules`)
3. P1: Async DB Wiring
4. P1+: Drift cleanup waves (after 2-3)
5. P2: Product decisions (intentional / out-of-scope features)

## 5) Ledger Promotion (PR-728 Output)

This audit promotes bad skips to P0/P1 immediately.
Intentional product-contract decisions stay separated.

Promoted now:

- P0: `App import failed unexpectedly` removal track (closed in PR-729)
- P1: `sys.modules` guard re-enable track
- P1: Async SQLAlchemy test wiring track
- P1: Drift cleanup wave after P0/P1 stabilization
- P2: Product decisions for removed or non-canonical fields:
  `interpret_group`, `estimate_level`, `ui_labels`

## 6) Out of Scope for PR-728

- No runtime code changes
- No API/schema modifications
- No test rewrites
- No feature delivery work

This PR is classification plus backlog promotion only.
