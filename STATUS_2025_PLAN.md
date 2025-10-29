### 2025 Plan – What’s Implemented vs Not in Main

#### Sources scanned
- PR_CORRECTION_PLANS.md
- ci-cd-optimization-plan-updated.md
- docs/archive/2025-09-16/NEXT_SESSION_PLAN.md
- Detected code deltas since stable main (408c4f95)

---

### A) CI/CD and Security (planned vs implemented)

- Planned (from plans):
  - Fast PR tests, nightly full coverage runs, strict markers
  - Diff coverage check (>=85% on changed files)
  - Parallelization (xdist), dependency caching, workflow matrix
  - Docker hardening, staging + production CD with approval gates

- Implemented in repo but not consolidated to main:
  - .github/workflows/cd-test.yml (fast PR runner draft)
  - .github/workflows/cd.yml.disabled (old CD disabled)
  - .pre-commit-config.yaml (hooks configured)
  - scripts/validate-ci-environment.sh (env safety checks)
  - bandit-final.json (security scan output)
  - mypy.ini (type-check config)

- Missing to finalize:
  - pr-tests.yml and nightly-tests.yml as separate workflows
  - diff-cover integration script and wiring in CI
  - optimized-ci.yml (matrix, caching, durations)

---

### B) Multimodal LLM & RAG

- Planned:
  - Provider selection with safe fallbacks (stub), timeouts, structured errors
  - RAG baseline module

- Implemented (not fully merged):
  - llm.py (provider selection, timeout parsing helper, clearer fallbacks)
  - core/rag/simple_rag.py (baseline RAG)
  - Tests: tests/test_llm_comprehensive.py, tests/test_llm_import_coverage.py, tests/test_llm_simple_96.py

- Gaps:
  - Provider mocks standardization (AsyncMock where needed)
  - Finalizing import-failure tests without recursion

---

### C) Bayesian + Monte Carlo System

- Planned:
  - Bayesian analyzer for failed tests and business logic
  - Monte Carlo tests for health/performance

- Implemented (present in repo now):
  - core/nutrition_bayesian_analyzer.py, core/comprehensive_bayesian_analyzer.py,
    core/bayesian_test_analyzer.py, core/business_bayesian_analyzer.py,
    core/integrated_bayesian_analyzer.py, pytest_bayesian_plugin.py,
    monte_carlo_test_analysis.py
  - Tests: tests/test_bayesian_analyzer.py, tests/test_comprehensive_bayesian_analyzer.py,
    tests/test_health_monte_carlo.py, tests/test_performance_monte_carlo.py

- To finish:
  - Ensure analyzer fresh-run and JUnit parsing wired into pre-commit (skip loops)
  - Add marker registration in pyproject.toml and strict-markers in CI

---

### D) Database, Food APIs, and Coverage Work

- Implemented (new tests increasing coverage, not all in main):
  - Update Manager tests: tests/test_update_manager_*.py (8 files)
  - Shoplist tests: tests/test_shoplist_*.py (3 files)
  - Recipe synth tests: tests/test_recipe_synth_*.py (2 files)

- Notes:
  - These aim to raise coverage of core/food_apis/update_manager.py and related modules to ≥97%

---

### E) Weekly Plan / Frontend touchpoints

- Files present:
  - core/weekly_plan.py, core/weekly_plan_new.py
  - app/routers/plan_export.py
  - frontend/src/features/plan/WeeklyPlanViewer.tsx
  - frontend/src/api/premium/weekly-plan.ts
  - frontend/src/hooks/useWhoTargetsWithWeeklyPlan.ts
  - frontend/src/api/__tests__/weekly-plan-integration.test.ts

- Status:
  - Code exists in repo tree; ensure import paths align after main rollback/splitting PRs

---

### Proposed PR sequencing to merge safely (small themed PRs)

1) PR: CI/CD Foundations
   - Add pr-tests.yml and nightly-tests.yml
   - Register markers in pyproject.toml, enable strict-markers
   - Wire diff-cover check (scripts/check-diff-coverage.py)

2) PR: Security & Type Safety
   - Dockerfile hardening (if needed), bandit baseline kept out of CI diff
   - mypy.ini consolidation, pre-commit hook refinements

3) PR: Bayesian + Monte Carlo
   - Integrate analyzer in pre-commit (guarded by env vars), keep fast mode on PR
   - Ensure markers and skips to avoid hangs

4) PR: LLM & RAG Stabilization
   - llm.py helpers, tests cleanup (no recursion), simple_rag baseline

5) PR: Coverage – Update Manager & Shoplist
   - Land the focused tests and any minor fixes to reach ≥97%

---

### Immediate To-Do (actionable)

- Create .github/workflows/pr-tests.yml and nightly-tests.yml from PR_CORRECTION_PLANS.md
- Add pyproject.toml marker registration and strict markers
- Add scripts/check-diff-coverage.py and wire in CI
- Guard Bayesian analyzer in pre-commit via SKIP_BAYESIAN_PRECOMMIT

---

Updated: 29 Oct 2025

