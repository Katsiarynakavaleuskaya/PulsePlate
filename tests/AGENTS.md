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

### Module purge / reload invariant (xdist stability)

Some tests intentionally purge/reload modules (e.g., via `module_purge.purge_modules(...)` or
`importlib.reload(...)`) to validate import-time wiring. Under xdist, this can create **stale**
module references and CI-only flakes if a test patches a module object captured before the purge.

**Hard rules:**

- If a test (directly or indirectly) purges/reloads modules (including `module_purge.purge_modules(...)`
  or `importlib.reload(...)`), it **MUST** resolve modules at runtime before patching/using them
  (preferred: `importlib.import_module("legacy_app")`).
- Avoid `from pkg.mod import name` in purge/reload-sensitive code paths: imported symbols can become
  stale after module re-import, breaking `monkeypatch.setattr()` and causing order-dependent flakes.
  This usually manifests as “patch applied but request path still uses real code”.

### SQLite test bootstrap rule (xdist / nightly)

Any test touching DB must ensure full schema initialization (`import models` + `Base.metadata.create_all`) before execution. Teardown must be idempotent and tolerate missing tables (e.g. catch `OperationalError` and rollback instead of failing). This prevents "no such table" and thread-safety issues under `pytest -n auto`.

- Schema-missing failures must use `pytest.fail()` (not `RuntimeError`).
- Expected schema must be derived from SoT (`Base.metadata` or shared constant), never hardcoded in fixtures.
- When using `Base.metadata` as schema SoT, ensure all ORM models are imported before `create_all()` / table checks.

### SQLite threading and engine SoT (xdist)

**Hard rules for SQLite in tests:**

1. **File-based SQLite only** under xdist (no `:memory:` — each worker needs isolated DB file).
2. **Per-worker DB path** must include `PYTEST_XDIST_WORKER` env var (e.g., `test_db_gw0.sqlite3`).
3. **NullPool required** for file-based SQLite to prevent connection reuse across threads.
4. **`check_same_thread=False`** must be set in `connect_args` (TestClient + anyio may use threads).
5. **Single-engine SoT**: app code must use the same engine/URL as test fixture (no dual-engine topology).

**Troubleshooting:**

- `sqlite3.ProgrammingError: SQLite objects created in a thread...` → verify `NullPool` + `check_same_thread=False`.
- `no such table: <table>` → check engine URL consistency (fixture vs app) via `test_sqlite_engine_sot.py` guard.
- `Database locked` errors → verify per-worker isolation (each worker has unique DB file path).

**Guard test:** `tests/test_sqlite_engine_sot.py` enforces engine/URL consistency and per-worker isolation.

- **RU:** Любой тест, меняющий `DATABASE_URL`, обязан вызывать reset `_RAW_ENGINE` до и после (и возвращать env).
- **EN:** Any test mutating `DATABASE_URL` must reset `_RAW_ENGINE` before and after (and restore env).
- **RU:** Fixture `configure_sqlite_database` — source of truth и всегда делает hard-reset `_RAW_ENGINE`.
- **EN:** `configure_sqlite_database` fixture is SoT and always hard-resets `_RAW_ENGINE`.

## Coverage / diff-cover (process invariant)

- CI uses diff coverage as a hard gate: PR-touched lines must reach 100% diff coverage (prefer small, targeted tests).
- If CI reports diff-cover gaps, add focused `*_diff_coverage.py` tests rather than weakening production checks.
  Preferred placement: `tests/vip/test_<feature>_diff_coverage.py` for VIP features, or `tests/test_<feature>_diff_coverage.py` alongside the related unit tests.
  Example: `tests/vip/test_pdf_export_diff_coverage.py`.

### ❌ Anti-pattern: testing dead code for coverage

**Rule**: If diff-cover shows uncovered code that has **zero call sites** → **delete it**, don't write tests.

Tests must protect **behavior**, not "lines that exist". Writing tests for unused helpers:

- Legitimizes dead code
- Creates maintenance debt
- Masks architectural drift

**Before adding a test**, verify the code is actually used:

```bash
git grep -n "function_name" -- app core
```

If no call sites → delete the code, not cover it.

### Diff-cover file visibility rule

**Problem**: CI runs all tests, but `diff-cover` attributes coverage only to **changed files** in the PR diff.
A standalone new test file may not be included in diff-cover's comparison, causing "missing coverage" even when tests pass.

**Rule**: When adding tests to cover lines in a **modified source file**, prefer adding them to an **already-modified test file** in the PR (or ensure the new test file is explicitly included in the diff).

- ✅ **Preferred**: Add coverage-tail tests to `tests/test_<feature>.py` if that file is already modified in the PR.
- ⚠️ **Alternative**: If creating a new test file, verify it appears in `git diff --name-only origin/main...HEAD` and that diff-cover includes it in the comparison.

**Example (PR-490B)**: Coverage-tail tests for `core/bmi/engine.py` were moved from a standalone file into `tests/test_bmi_visualization_spec.py` (already modified in the PR) to ensure diff-cover correctly detects coverage.

### Reliable local diff-cover check (prevents phantom gaps)

**Problem**: diff-cover may show "missing lines" if coverage.xml is stale or from wrong test session.

**Reliable ritual** (run from repo root):

```bash
# 1. Update main and ensure clean working tree
git fetch origin main
git status --short

# 2. Rebuild coverage from scratch in correct environment
rm -f .coverage coverage.xml
make cov
# Or equivalent:
# . .venv/bin/activate && coverage erase && coverage run -m pytest -q && coverage xml

# 3. Run diff-cover against actual base
diff-cover coverage.xml --compare-branch=origin/main --fail-under=97
```

**Sanity check** (if diff-cover still shows missing lines):

```bash
# Verify coverage.xml matches current code
ls -la coverage.xml
grep "pipeline.py" coverage.xml | head
```

**Why this works**:

- Fresh coverage.xml ensures no stale data
- `origin/main` comparison ensures correct baseline
- Clean working tree prevents diff-cover from seeing uncommitted changes

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

## Optional dependencies testing rule (hard)

CI may have optional deps installed (e.g. prometheus_client, reportlab).
Therefore tests MUST NOT assume optional deps are missing.

### Required pattern

To test fallback paths for optional deps:

- Use `monkeypatch` to force failure (preferred):
  - patch `prometheus_client.generate_latest` to raise
  - patch lazy import helper to raise ImportError
- Do NOT rely on `response.json()` unless you have asserted JSON Content-Type.

### Forbidden

- Relying on ImportError in CI without monkeypatch
- Using sys.modules purge / import hacks unless explicitly allowed by contract

## Patchability rule for optional deps (enforced)

When production code uses optional dependencies (e.g. prometheus_client, reportlab),
imports MUST remain patchable for tests.

### Required pattern (patchable)

- `import prometheus_client`
- use `prometheus_client.generate_latest()` and `prometheus_client.CONTENT_TYPE_LATEST`

### Forbidden pattern (breaks monkeypatch)

- `from prometheus_client import generate_latest, CONTENT_TYPE_LATEST`

**Why:** Direct imports break `monkeypatch.setattr()` because the symbol is already bound at module import time.

**Monkeypatch target rule:**
- Monkeypatch target must match the symbol used by production code.
- If production uses `import prometheus_client` → patch `prometheus_client.generate_latest`.
- If production uses `from X import Y` → patch at use-site: `app.middleware.metrics.Y` (if needed).
- Always verify patch target matches production call site.

**Prefer conftest fixtures:**
- Don't define local `TestClient` fixture if repo already has canonical `app`/`client` fixture in `conftest.py`.
- Local fixtures may bypass important test setup (environment variables, middleware, etc.).

**Avoid flaky parsing:**
- When asserting a metric series exists, prefer `_metric_value()` with exact labels over regex that matches "first POST/200".
- Regex-based parsing can be fragile if metrics order changes or multiple series exist.

## Metrics endpoint testing contract (hard)

### `/metrics` has two valid response modes

1) **Happy path**: Prometheus exposition format
   - `Content-Type` starts with `text/plain`
   - Response body is bytes/text (NOT JSON)

2) **Fallback**: JSON error envelope (when exporter fails at runtime)
   - `Content-Type` starts with `application/json`
   - Response body is JSON with `"error"` key (and optional `"detail"`)

### Hard test rule

Tests MUST NOT assume that `/metrics` returns JSON by default.

If a test expects JSON from `/metrics`, it MUST force exporter failure explicitly via `monkeypatch`,
e.g. patch `prometheus_client.generate_latest` to raise.

### Required snippet (copy/paste)

```python
import prometheus_client

def _boom() -> bytes:
    raise RuntimeError("boom")

monkeypatch.setattr(prometheus_client, "generate_latest", _boom)

resp = client.get("/metrics")
assert resp.status_code == 200
assert resp.headers["content-type"].startswith("application/json")
data = resp.json()
assert "error" in data
```

### Forbidden

- Calling `response.json()` on `/metrics` without asserting JSON `Content-Type` first
- "Fixing" a red CI by changing `/metrics` to always return JSON

## Metrics fallback tests (must be deterministic)

If a test expects JSON from `/metrics`, it MUST follow this exact order:

1. **Force exporter failure via monkeypatch** (before making request)
2. **Make request** to `/metrics`
3. **Assert status_code == 200**
4. **Assert Content-Type starts with `application/json`** (prevents JSONDecodeError)
5. **Call `response.json()`** and assert error keys

**Required pattern:**
```python
import prometheus_client

def _boom() -> bytes:
    raise RuntimeError("Prometheus exporter unavailable")

monkeypatch.setattr(prometheus_client, "generate_latest", _boom)

response = client.get("/metrics")
assert response.status_code == 200
assert response.headers["content-type"].startswith("application/json")
data = response.json()
assert "error" in data
```

**Why this order matters:**
- Monkeypatch must happen before request (otherwise exporter succeeds)
- Content-Type check prevents JSONDecodeError if fallback didn't trigger
- Never assume optional deps are missing in CI

## Route template tests (breaking change policy)

Tests that assert exact route template paths (e.g., `/api/v1/bmi/calculate`) are **intentional contract tests**.

**Changing a route template is a breaking change for metrics label contract.**

If you change a route template:
- Update the test assertion in the same PR
- Update `app/AGENTS.md` if the route label policy changes
- Document the breaking change in PR description

**Example:** If `/api/v1/bmi/calculate` becomes `/api/v2/bmi/calculate`, update:
- `tests/test_metrics.py::test_metrics_includes_route_template` (assertion)
- Any other tests that hardcode the route path
- `app/AGENTS.md` if metrics contract changes

## Content-Type assertions

- For Prometheus responses: assert `Content-Type` starts with `text/plain`
  (do not assert exact version/charset).
- For JSON error envelopes: assert `Content-Type` starts with `application/json`
  before calling `response.json()`.
- Never call `response.json()` unless `Content-Type` starts with `application/json`
  (prevents JSONDecodeError on text/plain endpoints like `/metrics`).

**Forbidden:**
- ❌ `assert response.headers["content-type"] == CONTENT_TYPE_LATEST` (exact equality)
- ❌ `assert response.headers["content-type"] == "text/plain; version=0.0.4"` (version pinning)

**Allowed:**
- ✅ `assert response.headers["content-type"].startswith("text/plain")`
- ✅ `assert response.headers["content-type"].startswith("application/json")`

## Forbidden in tests

- Do not mutate `sys.modules` (no `del sys.modules[...]`, no `sys.modules[...] = ...`).
  Use `patch()` / `monkeypatch.setattr()` instead.
  For FastAPI endpoints, prefer `tests/_route_patch.patch_route_dependency()`.

To verify:

- `pytest -q tests/test_repo_policy_sys_modules.py`

## CI red rule (enforced)

If CI is red:

- ❌ Do NOT push additional unrelated refactors.
- ❌ Do NOT claim "tests are wrong" or "CI issue" without committing the fixing patch.
- ❌ Do NOT label failures as "test problem" — submit the patch in the same PR.
- ✅ Required steps:
  1) Identify failing test(s) and reproduce locally.
  2) Fix code or tests in the same PR.
  3) Update AGENTS.md if the fix changes/clarifies a contract.
  4) Re-run: `make test-fast` and `make cov-check`.
- **No green, no merge, no exceptions.**

**Red CI means unfinished work. You either fix it in this PR or you don't push. "Tests are wrong" is only acceptable with a patch that updates the tests + documents the contract change.**

## Workflow rules (global)

Global workflow rules (CI recovery, Definition of Done, canonical commands) live in root `AGENTS.md`.
Use: `make verify`, `make cov-check`, and `git push` as described there (force push is forbidden).

This file (`tests/AGENTS.md`) contains ONLY test-specific rules (diff coverage, mocking constraints, forbidden patterns).

## Guard tests (docs registry)

The repo uses deterministic, repo-local “guard tests” to prevent instruction drift.

- **Agent registry guard**: `tests/test_agent_docs_registry_guard.py`
  - **What it enforces**:
    - `.cursor/agents/*.md` entries with YAML frontmatter `name:` must be registered in:
      - `docs/agents/index.md` (the **"## Available Agents"** table only)
      - `docs/orchestration/AGENT_CONTEXT_MAP.md`
    - Canonical protocol references must not be accidentally removed from:
      - `AGENTS.md`
      - `docs/orchestration/workflow.md`
  - **How to run**:

```bash
pytest -q tests/test_agent_docs_registry_guard.py
```

  - **How to fix failures**:
    - If an agent spec is added/renamed in `.cursor/agents/`, update the index and context map in the same PR.
    - Keep the agent table under the `## Available Agents` heading in `docs/agents/index.md`.

## Guard tests (repo policy scanner stability)

- **Repo policy guard**: `tests/test_repo_policy_guards.py`
  - **What it enforces**:
    - Import hygiene and architecture guardrails across `app/`, `core/`, and `tests/`.
    - Forbidden patterns (`sys.modules` poisoning, dynamic imports in protected scopes, etc.).
  - **Stability contract**:
    - Scanner reads must tolerate transient helper files under xdist (FileNotFound between glob and read).
    - Missing-at-read-time transient files are skipped, not treated as policy violations.
  - **How to run**:

```bash
pytest -q tests/test_repo_policy_guards.py
```

- **Dependency vulnerability floor guard**: `tests/test_dependency_security_guard.py`
  - **What it enforces**:
    - `cryptography` must stay at or above the non-vulnerable floor (`46.0.5`) in:
      - `requirements.txt`
      - `requirements-dev.txt`
      - `requirements-lock.txt`
      - `requirements.in`
      - `constraints.txt`
    - All `cryptography` declarations in each file are checked (not only the first match).
    - Requirement parsing must tolerate environment markers and inline comments where possible.
  - **How to run**:
    ```bash
    pytest -q tests/test_dependency_security_guard.py
    ```

  - **How to fix failures**:
    - Bump `cryptography` floor/version in the affected requirements files.
    - Regenerate lock files if needed, then re-run pre-commit + guard tests.

- **Docs Phase1 gates guard**: `tests/test_docs_phase1_gates.py`
  - **What it enforces**:
    - `docs/audit/*.md` changed in PRs must not contain unresolved `PR: TBD`.
    - Changed docs under `docs/audit/` and `docs/security/` must include at least one `file:line` evidence anchor.
  - **How to run**:
    ```bash
    pytest -q tests/test_docs_phase1_gates.py
    python scripts/ci/check_docs_phase1_gates.py --files docs/audit/your_audit.md docs/security/your_security_doc.md
    ```
  - **How to fix failures**:
    - Replace `PR: TBD` with final PR number or commit SHA in audit docs.
    - Add explicit evidence anchors like `path/to/file.py:123`.
    - Fix markdown style issues reported by `markdownlint-cli2` on changed `.md` files.

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
- `cast(T, value)` allowed at test boundaries
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
