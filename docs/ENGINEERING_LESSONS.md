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

- `tuple[int, str]`
- `list[str]`
- `dict[str, int]`

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
  missed in the scope of PR #896.

### Evidence (file:line)

- `tests/test_food_store_coverage_boost.py:126-170` (monkeypatch migration for `_connect` targets)
- `tests/test_food_store_coverage_boost.py:67-72` (autouse `monkeypatch.setenv` isolation)
- `tests/AGENTS.md:21-25` (policy update for `@patch` vs `monkeypatch.setattr`)

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

---

## 12) Feature-flag backend routing must have explicit priority + lock-safe lazy init

### Problem

When multiple search backends are feature-flagged (e.g., `semantic`, `compat`, `legacy`),
implicit fallback order creates drift and hard-to-reproduce behavior in CI/runtime.
Additionally, lazy backend creation can deadlock if helper code re-enters the same non-reentrant lock.

### Rule

- Declare backend precedence explicitly (example: `semantic > compat > legacy`).
- Keep default path fail-closed (`new feature flag = off` by default).
- In lazy init code guarded by `threading.Lock`, never call helper APIs that re-acquire the same lock.
  Assign guarded globals directly inside the lock section instead.

### Test contract

- Add deterministic tests for:
  - priority selection when multiple flags are on
  - fallback behavior when new adapter is missing
  - env guard parsing for candidate/window limits

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

## 13) API schema types must match persisted row types (barcode hit contract)

### Problem
Endpoint handlers that construct `FoodItem(**row)` can fail at runtime if DB columns store
string-encoded payloads for fields typed as structured types (example: `flags` expected as `List[str]`).

### Real incident (W2-C benchmark, 2026-02-25)
During latency benchmark for `/api/v1/foods/barcode/{barcode}`, hit-path requests raised
Pydantic validation errors because `app/schemas/food.py` defines:

- `flags: List[str]` (`app/schemas/food.py:40`)

but seeded DB rows may contain string values (e.g. `"[]"`), and router returns:

- `return FoodItem(**row)` (`app/routers/foods.py:105`)

### Rule
Before exposing DB rows directly through strict Pydantic models:

1. Normalize row payload types in repository/service layer
2. Add deterministic tests for hit/miss/malformed paths
3. Treat benchmark "scenario disabled" as tracked debt in `BACKLOG_LEDGER.md`

### Use instead
- Parse/normalize structured columns (`flags`) before model construction
- Keep migration/seed contracts aligned with API schema types
- Verify with endpoint-level tests, not only unit repository tests

## 14) After merge, never continue work on the same PR branch

### Problem
Continuing commits on a branch after PR merge creates ambiguity:
- new commits are not part of merged `main` state
- bot/check noise appears for already-merged scope
- reviewers see stale comments against a closed delivery

### Rule
Once PR state is `MERGED`:
1. stop edits on that branch immediately
2. create a new worktree + new branch from `origin/main`
3. continue only as a new PR with a new scope

### Verification
- `gh pr view <N> --json state,mergeCommit,mergedAt`
- if `state=MERGED`, do not push further commits to that branch

## 15) Local-first ingest scripts must fail-closed on empty normalized payload

### Problem
CSV ingestion can report "success" even when alias mapping drops required fields,
resulting in zero imported rows and empty API results.

### Rule
For operational import scripts (MenuStat-style and similar):
1. normalize column aliases to canonical contract keys
2. require non-empty mandatory keys (`chain_name`, `item_name`) per row
3. fail with non-zero exit code when no valid rows remain after normalization
4. keep a deterministic sample CSV + end-to-end script test in-repo

## 16) Subprocess-backed determinism tests must expose failure diagnostics

### Problem
When tests call shell pipelines (for example `make openapi`) and fully suppress
`stdout/stderr`, CI failures become opaque (`CalledProcessError` only), which blocks
fast triage and encourages blind reruns.

### Real incident (main CI, 2026-02-25)
`tests/test_openapi_determinism.py` failed in `test-main (3.12)` with
`Command '['make', 'openapi']' returned non-zero exit status 2`, but no actionable
stderr was available in job logs because both streams were redirected to `DEVNULL`.

### Rule
For subprocess-based deterministic tests:
1. capture subprocess output (`capture_output=True`, `text=True`)
2. on failure, emit bounded `stdout/stderr` tails in pytest failure message
3. allow a single retry for transient toolchain/network hiccups, then fail-closed

### Use instead
- helper wrappers that centralize retry + bounded log tail emission
- clear failure messages with command, exit code, and log tails
- deterministic assertions remain strict after command succeeds

---

## 17) Verify merged state before cherry-picking long-lived branches (conflict prevention)

### Problem
Cherry-picking older feature branch commits after partial upstream merges can create avoidable
conflicts and duplicate logic.

### Rule
Before cherry-picking:
1. check if commits are already merged via `git log origin/main..feature_branch`
2. inspect file history (`git log -- <file>`) for equivalent merged PRs
3. if upstream already contains the runtime path, continue with the next unimplemented DoD item
   instead of replaying stale commits

### Use instead
- prefer fresh branch from `origin/main`
- implement only remaining acceptance gaps (benchmark/report/tests/rollback notes)
- avoid replaying historical commits that represent already-merged behavior

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
