# SKIPPED Tests Classification Audit (PR-728)

Date: 13 February 2026 (America/New_York)
Scope: backend test files from the confirmed skip run (84 skipped tests)
Type: docs-only audit (no runtime changes)

## 1) Objective

Classify current `SKIPPED` reasons into three architectural classes and promote only risky classes to immediate backlog work:

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

- `57` -> module/symbol not available (`Drift`, mixed with feature scope decisions)
- `5` -> test data precondition not met
- `4` -> app import determinism skip fallback
- `4` -> async DB not configured
- `4` -> legacy negative tests marked skip (robust handling / mock seams)
- `3` -> signature mismatch
- `2` -> no canonical equivalent yet
- `2` -> mocking complexity
- `1` -> guard skipped (`sys.modules`)
- `1` -> optional response field (`ui_labels`) not in contract
- `1` -> update manager path wrapper mismatch

Selected raw evidence anchors from current repo state:

- Import determinism skip fallback: `tests/test_api.py:35`
- Disabled guard: `tests/test_repo_policy_guards.py:101`
- Async DB skip: `tests/test_shoplist_day_db_wiring.py:39`
- Canonical mismatch marker: `tests/test_app_coverage_unit_combined.py:83`
- `ui_labels` skip: `tests/test_premium_targets_es_snapshots.py:453`
- Signature mismatch skips: `tests/test_food_apis_coverage_errors.py:416`, `tests/test_food_apis_coverage_errors.py:437`
- Current unified DB signature: `core/food_apis/unified_db.py:265`
- Current WHO targets contract (no `ui_labels`): `app/schemas/premium_contracts.py:109`

## 3) Classification Matrix

| Bucket | Count | Class | Risk | Evidence | Action |
|---|---:|---|---|---|---|
| App import fallback skip | 4 | Quality/Determinism | Critical | `tests/test_api.py:35` | Remove skip wrapper; deterministic import seams; fail instead of skip |
| `sys.modules` guard disabled | 1 | Quality/Guard | High | `tests/test_repo_policy_guards.py:101` | Re-enable guard with controlled offender cleanup plan |
| Async DB not configured | 4 | Quality/Infra | High | `tests/test_shoplist_day_db_wiring.py:39` | Deterministic async DB matrix for tests or remove obsolete tests |
| Data precondition skips | 5 | Quality/Test design | Medium | `tests/test_targets_coverage_97.py:61` | Replace precondition skip with deterministic fixtures |
| Mocking complexity skips | 2 | Quality/Test seam | Medium | `tests/test_premium_week_app_coverage.py:41` | Use existing endpoint seam in `legacy_app.py` |
| Legacy negative-injection skips | 4 | Quality/Test validity | Medium | `tests/test_food_apis_coverage_errors.py:303` | Rewrite to deterministic error-path assertions |
| Signature mismatch skips | 3 | Drift/Contract | Medium | `tests/test_food_apis_coverage_errors.py:416` | Align tests to canonical signatures |
| Module/symbol not available (broad) | 57 | Drift (mixed with product scope) | Medium | `tests/test_database_apis_coverage.py:62` | Split into (a) canonical drift fixes and (b) product out-of-scope decisions |
| Removed-without-equivalent | 2 | Intentional/Decision pending | Low | `tests/test_app_coverage_unit_combined.py:83` | Product decision: remove obsolete tests or restore canonical equivalent |
| Optional response field (`ui_labels`) | 1 | Intentional/Contract decision | Low | `tests/test_premium_targets_es_snapshots.py:453` | Decide: add field to contract or remove obsolete assertion |
| Path wrapper mismatch | 1 | Drift/Test mismatch | Low | `tests/test_update_manager_fixed.py:129` | Update test to `_PatchablePathWrapper` contract |

## 4) Priority Decision (Execution Order)

Execution order approved for next PRs:

1. P0: Import Determinism
2. P1: Guard Re-enable (`sys.modules`)
3. P1: Async DB Wiring
4. P1+: Drift cleanup waves (after 1-3)
5. P2: Product decisions (intentional / out-of-scope features)

## 5) Ledger Promotion (PR-728 Output)

This audit promotes bad skips to P0/P1 immediately and keeps intentional/product-contract decisions separated.

Promoted now:

- P0: `App import failed unexpectedly` removal track
- P1: `sys.modules` guard re-enable track
- P1: Async SQLAlchemy test wiring track
- P1: Drift cleanup wave (post-stabilization, blocked by P0/P1 foundation)
- P2: Product decisions for removed/non-canonical fields (`interpret_group`, `estimate_level`, `ui_labels`)

## 6) Out of Scope for PR-728

- No runtime code changes
- No API/schema modifications
- No test rewrites
- No feature delivery work

This PR is classification + backlog promotion only.
