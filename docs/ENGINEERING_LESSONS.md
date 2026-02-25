# Engineering Lessons — PR-8b (VIP Shoplist PDF)

This document captures **project-level lessons** extracted from PR-8b.
Goal: prevent повторение классов проблем (test nondeterminism, CI portability, contract drift).

---

## 1) `sys.modules` mutations create dual-module state (CRITICAL)

### Problem
Mutating `sys.modules` in tests (e.g. `del sys.modules["app.routers.vip"]`) can create a **dual-module state**:
- imports resolve into different module objects
- `patch("...")` silently patches a different object than the one used by code-under-test

### Symptoms
- Patches "don't work" without obvious error
- flaky behavior depending on import order
- hard-to-debug nondeterminism

### Real incident (PR-8b)
CI flaked because:

`patch("app.routers.vip.get_available_regions", None)` sometimes did **not** affect the реально зарегистрированный handler for `/api/v1/vip/regions`.
In large test runners, this manifested as **success instead of error**.

**Fix (policy-compliant):**
- Find endpoint from `app.routes` by `(path, method)`
- Patch the callable used by the handler via:
  `endpoint.__globals__["get_available_regions"] = None` (via `monkeypatch`)
- No `sys.modules` mutations

### Rule
**Never mutate `sys.modules` in tests.**

**Repo status note:**
- Policy guard `pytest -q tests/test_repo_policy_sys_modules.py` is enforced for `tests/vip/**` only (legacy tests still contain sys.modules mutations).
- Policy uses AST-based detection (not regex) to avoid false positives on comments/strings.
- Policy tracks import aliases (`import sys as s`, `from sys import modules as m`) to catch all mutation patterns.

### Use instead
- `unittest.mock.patch(...)` (but see FAQ below)
- `monkeypatch.setattr(...)`
- `tests/_route_patch.patch_route_dependency(...)` for FastAPI endpoints

---

## FAQ: When `patch("module.symbol")` is not enough?

Sometimes the route handler used at runtime is not the same module object you think you're patching
(e.g., due to import aliasing, reload patterns, or dual-module state from prior tests).

**Robust approach (contract-safe):**
- Identify the actual registered endpoint (`app.routes`) by path+method
- Patch the function reference in `endpoint.__globals__` (or patch attribute on the actual callable)
- Prefer `monkeypatch` to keep test deterministic
- Use `tests/_route_patch.patch_route_dependency()` helper for FastAPI endpoints

---

## 2) Diff-coverage requires targeted tests for error paths

### Problem
Generic tests often don't execute specific branches (e.g. error lines 413/529), so diff-coverage fails.

### Rule
For each uncovered error path, add a **targeted test**.
Preferred pattern: `tests/**/test_*_diff_coverage.py`

---

## 3) Bash scripts must be portable (Bash 3.2+)

### Problem
macOS default Bash is 3.2; Bash-4-only features (e.g. `mapfile`) break local workflow.

### Rule
Scripts in `scripts/` must run on **Bash 3.2+**.
Prefer portable patterns: `while IFS= read -r ...`.

---

## 4) Shallow repos in CI require depth-aware git operations

### Problem
CI often uses shallow clones (`--depth=1`), so commands like `git diff HEAD~10 HEAD` can fail.

### Rule
Before using `HEAD~N`, verify actual depth:
- `git rev-list --count HEAD`
- fallback to merge-base or bounded depth

---

## 5) Always follow AGENTS.md before push

### Rule
Before pushing, follow the repo runbook.

**Quick checklist (example):**
- `pytest -q tests/test_repo_policy_guards.py`
- `make test-fast`
- `make cov-check`
- `make lint && make fmt-check`

---

## 6) PR description structure accelerates review

### Recommended sections
- `Review order (recommended)`
- `Why not split PR?`
- `Scope` split: core vs infrastructure
- `Risks / mitigations`
- `How to test`

---

## 7) Validate full error-envelope in tests

### Rule
Test contract, not just `status == "error"`:
- `status`
- `code`
- `error`
- `detail` (must match expectation)
- required fields present

---

## 8) Keyword-only args in test helpers

### Rule
For helpers with many parameters (5+), enforce keyword-only:

```python
def helper(*, a: int, b: str, c: str) -> None:
    ...
```

This prevents accidental argument-order bugs and improves readability.

---

## 9) Zero-decimal currencies must have explicit scope boundaries

### Rule

Document supported zero-decimal currencies (currently: **JPY/KRW**) and define the path to extend (e.g. VND/CLP/ISK).

---

## 10) Use builtin generics for typing (`tuple[...]` over `Tuple[...]`)

### Rule

Prefer modern typing syntax (Python 3.9+):

* `tuple[int, str]`
* `list[str]`
* `dict[str, int]`

### Type hints for test fixtures

- Prefer explicit typing for fixtures/helpers when patching internals:
  `monkeypatch: pytest.MonkeyPatch`

---

## 11) `@patch` decorator fails with `@contextmanager` under Python 3.12 + xdist (CRITICAL)

### Problem

`unittest.mock.patch` used as a **decorator** (`@patch("module._connect")`) does not
correctly intercept `@contextmanager`-decorated functions when running under
**Python 3.12 with pytest-xdist** (`-n 4 --dist=loadscope`).
The mock is applied but the real function executes, causing tests to hit the
real database and return unexpected results.

### Symptoms

- Tests pass locally (sequential, Python 3.13) but fail in CI (Python 3.12, xdist).
- Assertions like `assert len(result) == 1` fail because the mock was bypassed
  and the real DB returned all rows (e.g., 10 or 15 items).
- Only tests using `@patch` on `@contextmanager` targets are affected; plain
  function patches may still work.

### Real incidents (PR #896, PR #897)

- PR #896: 12 tests in `test_food_store_coverage.py` failed on Python 3.12 CI.
- PR #897: 8 tests in `test_food_store_coverage_boost.py` — same root cause,
  missed in PR #896 scope.

### Fix

Replace all `@patch(...)` decorators with `monkeypatch.setattr()`:

```python
# BEFORE (broken on 3.12 + xdist):
@patch("app.services.food_store._connect")
def test_search(self, mock_connect):
    mock_con = MagicMock()
    mock_connect.return_value = mock_con
    ...

# AFTER (works everywhere):
def test_search(self, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_con = _MockConnection(fetchall_result=[...])
    monkeypatch.setattr(food_store, "_connect", lambda: mock_con)
    ...
```

Also replace `os.environ` mutation in `setup_method()` with an autouse
`monkeypatch.setenv()` fixture for proper test isolation.

### Rule

**Prefer `monkeypatch.setattr()` over `@patch` decorator for all new tests.**
`monkeypatch` is pytest-native, version-safe, and properly scoped per test.

### Prevention

Before merging any PR that touches `food_store` tests (or any test using
`@patch` on `@contextmanager` targets), run:

```bash
# Scan for remaining @patch on food_store targets
git grep -n '@patch("app.services.food_store' -- tests/
```

If any matches remain, convert them to `monkeypatch.setattr()`.

---

## Repo Commands Reference

```bash
# Import hygiene / repo policy
pytest -q tests/test_repo_policy_guards.py

# VIP-only guard: forbid sys.modules mutations
pytest -q tests/test_repo_policy_sys_modules.py

# Smoke test
make test-fast

# Coverage
make cov-check

# Lint / format
make lint && make fmt-check

# Detect forbidden sys.modules mutations in tests (manual scan)
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- tests
```
