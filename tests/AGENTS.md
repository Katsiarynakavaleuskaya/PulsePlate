# Agent instructions (scope: tests/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `tests/` and below.
- Key directories: `tests/` (pytest suite), `conftest.py` (shared fixtures).

## Commands (run from repo root)
- Test: `make test`, `make test-fast`
- Coverage: `make cov`, `make cov-check`
- Targeted: `pytest tests/<path> -q`, `pytest -k "<pattern>" -q`

## Conventions
- Use pytest fixtures from `conftest.py`; keep tests isolated.
- Maintain >=97% total coverage; add tests for new branches.
- Never mock `builtins.__import__` or `builtins.float`.
- Preserve xdist DB isolation: each worker gets its own SQLite path.
- Prefer `monkeypatch` over global mutations; avoid real sleeps.

## Coverage / diff-cover (process invariant)
- CI uses diff coverage as a hard gate: PR-touched lines must reach 100% diff coverage (prefer small, targeted tests).
- If CI reports diff-cover gaps, add focused `*_diff_coverage.py` tests rather than weakening production checks.

## PDF export tests (PR-8b)

### Test structure
- Unit tests for data preparation: test `build_pdf_lines()` without PDF rendering (no reportlab dependency).
- API tests for PDF bytes: verify `%PDF` header and non-empty content (no snapshot comparisons).
- ImportError → 501 tests: verify that missing reportlab raises 501 with frozen error contract.

### Key test files
- `tests/vip/test_pdf_export_pr8b.py`: PR-8b specific tests (deterministic ordering, grouping, totals).
- `tests/vip/test_pdf_export_diff_coverage.py`: diff-cover targeted tests.

### Test invariants
- Do NOT compare PDF bytes directly (non-deterministic due to timestamps/metadata).
- Test data preparation (`PdfLine` objects) for determinism and correctness.
- Test PDF generation only for basic validity (header + length).
- Use `monkeypatch` to simulate `ImportError` for 501 tests (target `_lazy_reportlab`).

## Type hints policy (tests)

### Hard rules
- ❌ Never "fix" a failing test by loosening type hints (e.g., `Optional[T]` → `Any`)
- ❌ Never change production type hints to satisfy mocks
- ❌ Never add `# type: ignore` unless:
  - exact error code is specified (`# type: ignore[arg-type]`)
  - and comment explains why

### Allowed in tests
- `Any` **only** in fake/stub objects
- `Protocol` or `Callable[..., T]` preferred over `Any`
- `cast(T, value)` allowed **only at test boundary**
- `Optional[T]` only if production code can actually return `None`

### SQLAlchemy / Pydantic specifics
- Never change `Mapped[T]` / `nullable` in models to satisfy tests
- If relationship breaks typing → fix import order/model registration, not hints
- Pydantic v2: prefer real validators over `# type: ignore`

### Smell checklist
If tempted to:
- add `Optional` "just to make mypy shut up"
- replace concrete type with `Any`
- add multiple `# type: ignore` in a row

⛔ STOP — the test or mock is wrong, not the type hint.

## Import hygiene (hard rules)

- Do NOT use `importlib.util.spec_from_file_location`,
  `module_from_spec`, or `exec_module` in tests
  (exceptions are explicitly whitelisted in guard tests).
- Do NOT mutate `sys.modules` in tests.
- `sys.path.insert` is only allowed in `conftest.py`
  and `test_test_pro_access_coverage.py`.
- `TESTING=true` must be set before importing `app`
  (handled centrally in `pytest_configure`).
- If a test imports symbols from `app`,
  a guard-test must assert their presence.

## PDF export tests (hard rules)

- ❌ No snapshot tests of raw PDF bytes (metadata/ordering/timezone/renderer variance is inherently flaky).
- ✅ Prefer testing prepared “render rows” / data-model output for determinism and content.
- ✅ If rendering is exercised, assert only coarse properties:
  - `bytes` is non-empty (and optionally above a small minimum length)
  - expected key strings are present (via text extraction or by validating prepared rows)
- ✅ Required regression: missing optional PDF dependency (`ImportError(reportlab)`) returns HTTP `501`
  and preserves the established error contract shape.

## No namespace duplication in tests (xdist stability)

### Forbidden in tests
- Dynamic module loading:
  - `spec_from_file_location`, `module_from_spec`, `exec_module`
- Path hacks:
  - `sys.path.insert`
- Module injection:
  - `sys.modules[...] = ...`, `del sys.modules[...]`

### Allowed exceptions (must be whitelisted)
- `tests/conftest.py`
- `tests/test_test_pro_access_coverage.py`
- `tests/test_ensure_database_versions.py`

### Required import pattern
- Import production modules by package path:
  - ✅ `import app.services.recipe_store as recipe_store`
  - ✅ `from app import app`
  - ❌ never load `app/services/X.py` by file path

### Import hygiene exceptions (intentional)
Dynamic imports allowed only for script-style tests:
- `tests/test_test_pro_access_coverage.py`
- `tests/test_ensure_database_versions.py`
- `tests/conftest.py` (xdist/db + env bootstrap)

sys.path.insert allowed only in:
- `tests/conftest.py`
- `tests/test_test_pro_access_coverage.py`

### Pre-commit verification
```bash
# 1. No dynamic imports (except whitelisted)
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" tests \
  | grep -vE "test_test_pro_access_coverage\.py|test_ensure_database_versions\.py|conftest\.py"

# 2. No sys.path.insert (except allowed)
git grep -n "sys\.path\.insert" tests \
  | grep -vE "test_test_pro_access_coverage\.py|conftest\.py"

# 3. No sys.modules mutations
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" tests

# All should return empty or only whitelisted files
```

### Find violators (excluding guard tests)
```bash
# Dynamic imports
git grep -n "sys\.path\.insert" tests \
  | grep -vE "conftest\.py|test_test_pro_access_coverage\.py|test_import_hygiene_guard\.py|test_repo_policy_guards\.py"

# Recipe store anti-pattern
rg -n "sys\.modules\.get\(\"recipe_store\"\)|recipe_store.*spec_from_file_location" tests
```
