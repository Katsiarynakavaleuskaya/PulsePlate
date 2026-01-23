# PulsePlate — Agent Runbook (CI Failures)

**Last updated:** 2025-12-24 (PR #403 Import Hygiene)

**What this is:** Quick reference for diagnosing CI failures and import hygiene regressions.
**When to use:** CI fails, tests hang, import errors, SQLAlchemy mapper issues.
**Related:** See root `AGENTS.md` for fast triage commands, `tests/test_repo_policy_guards.py` for enforced rules.

## Agent Coordination (Automatic)

**When creating any task, the agent-coordinator should be automatically invoked.**

**Canonical workflow:** See `docs/orchestration/workflow.md`

**Templates (copy-paste ready):**
- Task Analysis: `docs/orchestration/task_analysis.template.md`
- Work Review: `docs/orchestration/work_review.template.md`
- Synthesis: `docs/orchestration/synthesis.template.md`
- DoD: `docs/orchestration/dod.template.md`

The coordinator will:
1. **Analyze the task** and identify which domain(s) it touches
2. **Route to appropriate agent(s)** based on capabilities:
   - `ai-innovation-specialist`: AI/ML, RAG, computer vision, research
   - `architecture-specialist`: Code structure, patterns, invariants
   - `bug-hunter`: Bugs, tests, quality gates, coverage
   - `creative-designer`: UI/UX, brand assets, visuals
   - `marketing-strategist`: ASO, growth, conversion, strategy
   - `security-auditor`: Vulnerabilities, penetration testing
3. **Coordinate multi-agent workflows** when tasks span domains
4. **Synthesize outputs** from multiple agents into coherent solutions
5. **Provide quality assurance** and final conclusions
6. **Generate brainstorming tasks** for scientific and creative innovation

**Usage:**
```text
Use the agent-coordinator subagent to [task description]
```

The coordinator will automatically delegate to specialized agents and synthesize their work.

**Starting a new task:**
1. Use coordinator for Task Analysis (template: `docs/orchestration/task_analysis.template.md`)
2. Coordinator assigns agent(s) and routes work
3. After work completes, coordinator reviews (template: `docs/orchestration/work_review.template.md`)
4. For multi-agent tasks, coordinator synthesizes (template: `docs/orchestration/synthesis.template.md`)
5. Before PR merge, verify DoD (template: `docs/orchestration/dod.template.md`)

**Postponed items:** Always record in `docs/roadmap/BACKLOG_LEDGER.md` immediately.

## 0) Golden Rule

Before editing imports / `__init__` / sys.path / sys.modules:
**Run guard checks first.** If guards fail, fix the policy violation before anything else.

## 1) Fast Local Triage (run from repo root)

```bash
make lint
make test-fast
pytest -q tests/test_repo_policy_guards.py
```

## 2) PR #403 Specific Checks (Import Hygiene)

### 2.0 SQLAlchemy Model Registration (WeeklyPlan/DayPlan not found)

**Problem:** `expression 'WeeklyPlan' failed to locate a name` → model not registered in ORM.

**A. Where classes are declared:**

```bash
rg -n "class WeeklyPlan\b|class DayPlan\b" app/models -S
```

**B. Where DayPlan references WeeklyPlan:**

```bash
rg -n "relationship\(\s*[\"']WeeklyPlan[\"']" app/models -S
rg -n "Mapped\[[\"']WeeklyPlan" app/models -S
```

**C. Model exports (CRITICAL - must export both classes):**

```bash
rg -n "from app\.models\.plans import|from \.plans import" app/models -S
sed -n '1,200p' app/models/__init__.py 2>/dev/null || true
```

**D. Who imports models at startup:**

```bash
rg -n "import app\.models|from app\.models import|import models" app legacy_app.py app/main.py core -S
```

**Fix pattern:**
- Keep `WeeklyPlan` and `DayPlan` in same module with `WeeklyPlan` declared **before** `DayPlan`
- Export both from `app/models/__init__.py`:
  ```python
  from .plans import WeeklyPlan, DayPlan  # noqa: F401
  __all__ = [..., "WeeklyPlan", "DayPlan"]
  ```
- Ensure startup imports `app.models` package (not individual modules)

### 2.1 Import hygiene regressions (dynamic import / exec_module)

**Problem:** `spec_from_file_location / exec_module` returns → Dual Base + Pydantic TypeAdapter issues.

```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- app core tests
```

**Offender list (excluding whitelisted script tests):**

```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- tests \
  | grep -vE "test_test_pro_access_coverage\.py|test_ensure_database_versions\.py|conftest\.py"
```

### 2.2 sys.path.insert in tests (masks import path bugs)

**Problem:** Breaks xdist isolation, hides real import errors.

```bash
git grep -n "sys\.path\.insert" -- tests
```

**Exclude allowlist (conftest + guards):**

```bash
git grep -n "sys\.path\.insert" -- tests \
  | grep -vE "tests/conftest\.py|tests/test_test_pro_access_coverage\.py|tests/test_import_hygiene_guard\.py|tests/test_repo_policy_guards\.py"
```

### 2.3 sys.modules mutation (main source of Dual Base)

**Problem:** `sys.modules["x"]=...` and `del sys.modules["x"]` create separate namespaces.

```bash
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- .
```

**Only in tests:**

```bash
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- tests
```

### 2.4 Public surface app package (missing attributes)

**Problem:** Tests fail with:
- `module 'app' has no attribute build_nutrition_targets`
- `... get_update_scheduler`
- `... resolve_attr`

**Check what tests expect from app:**

```bash
git grep -nE "from app import |app\.(resolve_attr|build_nutrition_targets|get_update_scheduler|make_weekly_menu)" -- tests
```

**Verify what's actually exported:**

```bash
sed -n '1,200p' app/__init__.py
```

**Run surface guard tests:**

```bash
pytest -q tests/test_app_public_surface.py
pytest -q -k "public_surface or env_guards or import_hygiene"
```

### 2.5 ENV gating / порядок установки TESTING

**Problem:** `EXPORTS_ENABLED`/`VIP` computed at import time, env set later → tests get 404/422.

```bash
git grep -nE "EXPORTS_ENABLED|VIP_ENABLED|TESTING|DEBUG" -- app legacy_app.py core tests
```

**Check pytest_configure:**

```bash
git grep -n "os\.environ\[" -- tests/conftest.py
git grep -n "pytest_configure" -- tests/conftest.py
```

### 2.6 Recipe store tests (_con missing)

**Problem:** `module 'recipe_store' has no attribute '_con'` - symptom of wrong module import path.

**Anti-pattern check:**

```bash
git grep -n "sys\.modules\.get\(\"recipe_store\"\)" tests
git grep -nE "spec_from_file_location\(\"recipe_store\"" tests
```

**Correct pattern:**
- ❌ Don't: `sys.modules.get("recipe_store")`
- ✅ Do: `import app.services.recipe_store as rs`

**Verify import works:**

```bash
python -c "import app.services.recipe_store as rs; print(hasattr(rs,'_con'), rs._con)"
```

### 2.7 VIP router 422 vs 404

**Problem:** Router registered but disabled by logic → 422/401 instead of 404.

```bash
git grep -nE "include_router\(.*vip|VIP|vip_router" app
git grep -nE "VIP_ENABLED|VIP_MODULE_ENABLED|FEATURE_VIP" app core legacy_app.py
```

### 2.8 Docker build (COPY app.py not found / entrypoint drift)

**Problem:** Dockerfile copies `app.py` but file was renamed/moved.

```bash
rg -n "COPY .*app\.py|COPY .*legacy_app\.py" Dockerfile
rg -n "uvicorn\s+app(:|\.main:app)|legacy_app" Dockerfile Makefile docker-compose.yaml -S
```

**Check entrypoint matches canonical:**

```bash
rg -n "app\.main:app" Dockerfile Makefile docker-compose.yaml -S
```

**Expected:** `app.main:app` (current canonical entrypoint, not `legacy_app:app`).

### 2.9 Fast triage - top failure patterns

**When CI shows many failures, extract first 50:**

```bash
pytest -q --maxfail=50
```

**Build error frequency histogram:**

```bash
pytest -q --maxfail=200 2>&1 | rg -o "E\s+[A-Za-z_]+Error|sqlalchemy\.[A-Za-z_]+" | sort | uniq -c | sort -nr | head -30
```

This reveals patterns like:
- `NoForeignKeysError` → model relationship issue
- `InvalidRequestError: Table already defined` → duplicate model registration
- `AttributeError: module 'app' has no attribute` → missing public surface export

---

## 3) If LINT Fails

### 3.1 Ruff / formatting

```bash
ruff check . --fix
black .
```

### 3.2 Explain-only (to see the real errors)

```bash
ruff check . -v
```

## 4) If TESTS Fail

### 4.1 Narrow first

```bash
pytest -q -k "<failing_test_name_or_keyword>"
pytest -q tests/<path_to_file>.py
```

### 4.2 Import hygiene suspects

See section 2 (PR #403 Specific Checks) above for detailed grep commands.

### 4.3 ENV gating suspects (exports/vip)

```bash
git grep -n "EXPORTS_ENABLED|VIP_ENABLED|TESTING|DEBUG"
```

Ensure `TESTING=true` is set before importing `legacy_app`.

## 5) If DOCKER Build Fails

See section 2.8 above for Docker-specific checks.

## 6) If COVERAGE Guard Fails

### 6.1 Identify uncovered lines

```bash
pytest --cov --cov-report=term-missing
```

Then add micro-tests for uncovered branches (avoid flaky tests).

## 7) If xdist Hangs / Mapper / Dual Base Symptoms

### 7.1 Confirm no dynamic loader

```bash
pytest -q tests/test_repo_policy_guards.py
```

### 7.2 Confirm single Base identity (if guard exists)

```bash
pytest -q -k "single_base or import_hygiene"
```

## 8) What NOT to Do (Hard Rules)

- Never mock `builtins.__import__` or `builtins.float`
- Never mutate `sys.modules` in tests
- Never reintroduce `exec_module` / dynamic import patterns
- No network calls in unit tests (use `providers/stub.py`)

## 9) Import Hygiene Checklist (Before Any PR)

See `AGENTS.md` for the full checklist. Quick version:

1. No dynamic imports (except whitelisted test files)
2. No `sys.path.insert` (except whitelisted test files)
3. No `sys.modules` mutations
4. Verify PEP 562 shim in `app/__init__.py`
5. `TESTING=true` set before app import
6. Guard tests pass
7. Export routes registered when feature-flagged

## 10) Common CI Failure Patterns

### Pattern: "ModuleNotFoundError: No module named 'app'"

**Cause**: Import path broken, likely due to `sys.path` manipulation or missing `__init__.py`.

**Fix**:
```bash
# Check package structure
find app core -name "__init__.py"

# Verify imports use package paths
git grep -n "from app import" tests
```

### Pattern: "Multiple mapper registry conflicts"

**Cause**: Dual Base - models importing different `Base` instances.

**Fix**:
```bash
# Run Dual Base guard
pytest -q -k "single_base"

# Check all models import from core.db
git grep -n "from core.db import Base" app/models core
```

### Pattern: "pytest hangs on teardown"

**Cause**: Background threads/processes not cleaned up (common in coverage-smoke tests).

**Fix**: Exclude heavy import tests from xdist:
```python
# In conftest.py or pyproject.toml
# Mark tests: @pytest.mark.no_xdist
```

## 11) Emergency: Revert to Known Good State

```bash
# Check last green CI commit
git log --oneline -20

# Soft reset to that commit
git reset --soft <commit-sha>

# Review changes
git diff HEAD
```
