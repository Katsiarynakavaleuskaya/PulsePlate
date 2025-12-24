# PulsePlate — Agent Runbook (CI Failures)

## 0) Golden Rule

Before editing imports / `__init__` / sys.path / sys.modules:
**Run guard checks first.** If guards fail, fix the policy violation before anything else.

## 1) Fast Local Triage (run from repo root)

```bash
make lint
make test-fast
pytest -q tests/test_repo_policy_guards.py
```

## 2) If LINT Fails

### 2.1 Ruff / formatting

```bash
ruff check . --fix
black .
```

### 2.2 Explain-only (to see the real errors)

```bash
ruff check . -v
```

## 3) If TESTS Fail

### 3.1 Narrow first

```bash
pytest -q -k "<failing_test_name_or_keyword>"
pytest -q tests/<path_to_file>.py
```

### 3.2 Import hygiene suspects

```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" tests app core
git grep -n "sys\.path\.insert" tests
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" tests app core
```

### 3.3 ENV gating suspects (exports/vip)

```bash
git grep -n "EXPORTS_ENABLED|VIP_ENABLED|TESTING|DEBUG"
```

Ensure `TESTING=true` is set before importing `legacy_app`.

## 4) If DOCKER Build Fails

### 4.1 Common: missing renamed files

Search Dockerfile COPY lines vs repo tree.

```bash
ls -la
grep -n "COPY" Dockerfile
```

### 4.2 Validate entrypoint string

```bash
git grep -n "uvicorn" Makefile Dockerfile docker-compose.yaml
```

Expected: `app.main:app` (or whatever is current canonical entrypoint).

## 5) If COVERAGE Guard Fails

### 5.1 Identify uncovered lines

```bash
pytest --cov --cov-report=term-missing
```

Then add micro-tests for uncovered branches (avoid flaky tests).

## 6) If xdist Hangs / Mapper / Dual Base Symptoms

### 6.1 Confirm no dynamic loader

```bash
pytest -q tests/test_repo_policy_guards.py
```

### 6.2 Confirm single Base identity (if guard exists)

```bash
pytest -q -k "single_base or import_hygiene"
```

## 7) What NOT to Do (Hard Rules)

- Never mock `builtins.__import__` or `builtins.float`
- Never mutate `sys.modules` in tests
- Never reintroduce `exec_module` / dynamic import patterns
- No network calls in unit tests (use `providers/stub.py`)

## 8) Import Hygiene Checklist (Before Any PR)

See `AGENTS.md` for the full checklist. Quick version:

1. No dynamic imports (except whitelisted test files)
2. No `sys.path.insert` (except whitelisted test files)
3. No `sys.modules` mutations
4. Verify PEP 562 shim in `app/__init__.py`
5. `TESTING=true` set before app import
6. Guard tests pass
7. Export routes registered when feature-flagged

## 9) Common CI Failure Patterns

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

## 10) Emergency: Revert to Known Good State

```bash
# Check last green CI commit
git log --oneline -20

# Soft reset to that commit
git reset --soft <commit-sha>

# Review changes
git diff HEAD
```
