# Test Suite Review — 13 March 2026

**Date:** 13 March 2026
**Scope:** `tests/` on `main`
**Timezone reference:** `America/New_York`
**Purpose:** establish the canonical kickoff artifact for the 2026-03-13 test-hygiene remediation wave.

## Summary

- `make test-fast` was the baseline success signal for the review scope before cleanup planning; the suite currently exposes broad hygiene debt concentrated in test isolation and import determinism.
- Highest-risk themes are:
  - direct `sys.modules` mutation in tests
  - `TestClient` lifecycle leaks and stale resource cleanup
  - direct `os.environ[...]` mutation without guaranteed restore
  - forbidden `builtins.__import__` monkeypatching
  - real `time.sleep()` / `asyncio.sleep()` in deterministic tests
- Canonical policy sources for this review:
  - `AGENTS.md`
  - `tests/AGENTS.md`
  - `docs/ENGINEERING_LESSONS.md`

## Theme Matrix

| Theme | Priority | Signal | Why it matters |
|---|---|---:|---|
| TestClient lifecycle leaks | P0 | 650 `TestClient(` matches in `tests/` | Open clients can leak resources, bypass lifespan cleanup, and create xdist flakes. |
| `sys.modules` mutation | P0 | 146 mutation-style matches in `tests/` | Breaks import determinism and can create dual-module state. |
| `os.environ` mutation | P1 | 367 `os.environ[` matches in `tests/` | Pollutes workers and creates order-dependent failures. |
| `builtins.__import__` patching | P1 | 11 direct matches in `tests/` | Violates test policy and creates broad import-side effects. |
| real sleeps | P0/P2 | 15 `time.sleep` / `asyncio.sleep` matches in `tests/` | Makes tests timing-sensitive under load and xdist. |

## Findings

### 1. TestClient lifecycle and resource cleanup

- `tests/test_app_faker_realistic.py:32`
- `tests/test_app_faker_realistic.py:201`
- `tests/test_coverage_boost_simple_97.py:26`
- `tests/test_recipes_router_coverage_97.py:19`
- `tests/test_coverage_97_final_push.py:20`
- `tests/test_plate_targets_micros_hypothesis.py:28`
- `tests/test_openfoodfacts_client.py:18`
- `tests/test_missing_coverage.py:39`
- `tests/test_vip_shoplist_router_hardening.py:265`

**Assessment:** multiple tests still instantiate `TestClient(...)` without `with ...` or explicit `close()`. Some setup/teardown flows also leave closeable OFF/test resources unmanaged.

**Remediation direction:** migrate high-risk files toward canonical context-managed client usage via shared fixtures or explicit `with TestClient(...)`.

### 2. `sys.modules` mutation in tests

- `tests/conftest.py:412`
- `tests/conftest.py:425`
- `tests/test_conftest_specific_lines.py:16`
- `tests/test_conftest_keyerror_trigger.py:22`
- `tests/test_conftest_97_coverage.py:22`
- `tests/test_remaining_coverage_simple.py:101`
- `tests/test_vip_coverage_comprehensive.py:35`
- `tests/test_vip_coverage_precise.py:35`
- `tests/test_app_vip_comprehensive_97.py:18`
- `tests/test_rag_simple.py:22`
- `tests/test_app_critical_lines_97.py:57`
- `tests/test_final_97_coverage.py:47`
- `tests/test_vip_coverage_fixed.py:37`
- `tests/test_core_db_async_optional.py:17`
- `tests/test_additional_core_coverage.py:129`
- `tests/test_core_utils_branches.py:20`

**Allowed exceptions already recognized by policy:** `tests/conftest.py`, `tests/test_ensure_database_versions.py`, `tests/helpers/test_fast_update_stubs.py`.

**Assessment:** import determinism debt remains wide, while the incremental guard currently enforces only `tests/vip/**/*.py`, `tests/test_llm_extras.py`, and now the first remediated non-VIP slice.

**Remediation direction:** replace direct mutation with `monkeypatch.delitem(sys.modules, ..., raising=False)` / `monkeypatch.setitem(...)`, then widen the guard incrementally.

### 3. Direct `os.environ` mutation without guaranteed restore

- `tests/test_coverage_boost.py:21`
- `tests/test_recommendations_coverage.py:34`
- `tests/test_targets_coverage.py:23`
- `tests/test_scheduler_final_coverage.py:17`
- `tests/test_scheduler_missing_coverage.py:22`
- `tests/test_core_schemas_coverage.py:27`
- `tests/test_core_units_coverage.py:16`
- `tests/test_daily_plate_comprehensive.py:27`
- `tests/test_rag_simple.py:20`
- `tests/test_aliases_coverage_96.py:20`
- `tests/test_vip_coverage_fixed.py:19`

**Assessment:** many `setup_method()` patterns still set env directly and either rely on partial teardown or on comments claiming conftest cleanup.

**Remediation direction:** move to `monkeypatch.setenv()` or dedicated autouse env fixtures, grouped by shared pattern.

### 4. Forbidden builtins monkeypatching

- `tests/test_llm_import_coverage.py:42`
- `tests/test_llm_import_coverage.py:78`
- `tests/test_llm_import_coverage.py:100`
- `tests/test_business_bayesian_analyzer.py:663`
- `tests/test_business_bayesian_analyzer.py:670`
- `tests/edges/test_unified_db_small_edges.py:34`
- `tests/edges/test_core_edge_branches.py:222`
- `tests/disabled_hypothesis/test_llm_import_coverage.py:56`

**Assessment:** these tests patch `builtins.__import__` or similar broad seams instead of using patchable module-level helpers.

**Remediation direction:** expose narrow import helpers in production modules where needed and patch those helpers or `importlib.import_module` instead.

### 5. Real sleeps

- `tests/test_unified_db_coverage.py:351`
- `tests/test_scheduler_additional_coverage.py:113`
- `tests/test_scheduler_missing_coverage.py:82`
- `tests/test_food_apis_comprehensive_coverage.py:97`
- `tests/test_scheduler_coverage.py:87`

**Assessment:** real sleeps are still present in deterministic tests and should be replaced with controlled timestamps, monkeypatched clocks, or explicit mocked awaits.

**Remediation direction:** use stable file timestamps, helper seams, or mocked async boundaries.

## Existing Related History

- `docs/ENGINEERING_LESSONS.md:7` documents `sys.modules` mutation as a critical determinism issue.
- `docs/ENGINEERING_LESSONS.md:113` documents the Python 3.12 + xdist `@patch` issue and recommends `monkeypatch.setattr()`.
- `tests/test_repo_policy_sys_modules.py:17` defines the incremental test-only guard scope.
- `docs/roadmap/BACKLOG_LEDGER.md:634` tracks TestClient/runtime compatibility drift as a broader CI contract item.
- `docs/roadmap/BACKLOG_LEDGER.md:3423` records a prior leaked-TestClient cleanup in the nutrition-log bootstrap work.
- `docs/roadmap/BACKLOG_LEDGER.md:4256` records the re-enabled repository `sys.modules` mutation guard.
- `docs/roadmap/BACKLOG_LEDGER.md:4437` and `docs/roadmap/BACKLOG_LEDGER.md:4476` already encode a no-`sleep()` deterministic testing rule for websocket work.

## Verification Commands

```bash
# sys.modules violations
git grep -nE "sys\\.modules\\[[^]]+\\]\\s*=|del\\s+sys\\.modules\\[" tests \
  | grep -vE "conftest\\.py|test_repo_policy|test_ensure_database|test_fast_update_stubs|\\.bak"

# os.environ direct mutation
git grep -n "os\\.environ\\[" tests | grep -v conftest.py

# real sleep usage
git grep -n "time\\.sleep" tests | grep -v "patch\\|monkeypatch"

# policy guards
pytest -q tests/test_repo_policy_guards.py tests/test_repo_policy_sys_modules.py
```

## Next Actions

1. Record the remediation wave in `docs/roadmap/BACKLOG_LEDGER.md` with one umbrella item and linked execution items.
2. Start the risk-first slice with `sys.modules` / `builtins` / `sleep` cleanup on a bounded set of files.
3. Follow with TestClient/session isolation, then env cleanup, then final guard-scope expansion.
