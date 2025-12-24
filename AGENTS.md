# Agent instructions (scope: repo root and subdirectories)

## If you feel lost
Run: `pytest -q tests/test_repo_policy_guards.py` and follow RUNBOOK_AGENT.md section "PR Specific Checks".

## One-command smoke checks (run from repo root)

### 0) Quick status
```bash
git status
git log -1 --oneline
```

### 1) Guard policies (import hygiene)
```bash
pytest -q tests/test_repo_policy_guards.py
```

### 2) Fast tests (cheap signal)
```bash
make test-fast
```

### 3) Coverage gate (only when preparing merge)
```bash
make cov-check
```

### 4) Lint/format
```bash
make lint
make fmt-check
```

## Canonical navigation
Start here: AGENTS.md → RUNBOOK_AGENT.md → module AGENTS.
- RUNBOOK_AGENT.md: greps + CI failure triage
- tests/test_repo_policy_guards.py: enforced architecture rules

## Fast triage (run these first when things break)

```bash
# 1. Guard policies (catch import hygiene violations)
pytest -q tests/test_repo_policy_guards.py

# 2. Fast test smoke (cheap signal, ~10-30s)
make test-fast

# 3. Lint/format check
make lint

# 4. First-fail triage (stop after 20 failures to see patterns)
pytest -q --maxfail=20

# 5. Docker entrypoint sanity
rg -n "COPY .*app\.py" Dockerfile
```

## PR #403 specific invariants (Import Hygiene)

### Entrypoint
- Docker/uvicorn MUST use: `app.main:app`
- Verify: `rg -n "uvicorn\s+app(:|.main:app)" Dockerfile Makefile docker-compose.yaml`

### Forbidden patterns
- No dynamic imports in tests/app/core/providers (except whitelisted test files)
- No sys.path.insert in tests (except conftest.py, test_test_pro_access_coverage.py)
- No sys.modules mutation anywhere

### ENV-gating order
- `TESTING=true` MUST be set BEFORE importing app/legacy_app
- Handled in tests/conftest.py pytest_configure

### Model registration
- `app/models/__init__.py` MUST export all model classes
- Verify: `rg -n "from .*\.plans import|__all__" app/models/__init__.py`
- Both `WeeklyPlan` and `DayPlan` must be in `__all__`

### Public surface contract
- `app/__init__.py` uses PEP 562 forwarding to `legacy_app`
- Required symbols: `resolve_attr`, `make_weekly_menu`, `build_nutrition_targets`, `get_update_scheduler`
- Verify: `python -c "import app; needed=['resolve_attr','make_weekly_menu','build_nutrition_targets','get_update_scheduler']; print('missing:', [n for n in needed if not hasattr(app, n)])"`

### See RUNBOOK_AGENT.md for detailed grep commands

## Scope and layout
- This AGENTS.md applies to: repo root and below.
- Project shape: single project with subfolders; backend is primary product, frontend/ios are clients.
- Key directories: `app/`, `core/`, `frontend/`, `ios/`, `deploy/`, `providers/`, `tests/`, `alembic/`,
  `scripts/`, `docs/`.

## Modules / subprojects

Backend spans `app/` + `core/` (unified API + domain logic).

| Module | Type | Path | What it owns | How to run | Tests | Docs | AGENTS |
|--------|------|------|--------------|------------|-------|------|--------|
| backend-app | fastapi | `app/` | FastAPI routers, middleware, schemas | `make dev` | `make test` | `docs/` | `app/AGENTS.md` |
| backend-core | python | `core/` | Domain logic, analyzers, DB helpers | Used by backend | `make test` | `docs/` | `core/AGENTS.md` |
| frontend | react/vite | `frontend/` | Web client | `npm run dev` | `npm run test` | `frontend/README.md` | `frontend/AGENTS.md` |
| ios | swift | `ios/` | iOS client | Xcode | Xcode tests | `ios/README.md` | `ios/AGENTS.md` |
| deploy | infra | `deploy/` | Docker/Caddy configs | `make docker-run` | - | `DEPLOYMENT_*.md` | `deploy/AGENTS.md` |
| migrations | alembic | `alembic/` | DB migration scripts | Alembic CLI (see `alembic.ini`) | - | `DEPLOYMENT_*.md` | `alembic/AGENTS.md` |
| scripts | utilities | `scripts/` | Repo automation scripts | Run from repo root | - | - | `scripts/AGENTS.md` |
| providers | python | `providers/` | External provider adapters | Used by backend | `make test` | - | `providers/AGENTS.md` |
| tests | pytest | `tests/` | Test suite | `make test` | `make test` | - | `tests/AGENTS.md` |

## Cross-domain workflows
- Frontend -> backend: REST `/api/v1/*` endpoints with API key + session auth; contracts derive from
  Pydantic models in `app/schemas/` and FastAPI OpenAPI output.
- iOS -> backend: same REST endpoints and auth; mobile flows mirror web API behavior.
- DB migrations: Alembic in `alembic/` targets SQLite/Postgres; keep migrations in sync with
  SQLAlchemy models.
- Shared schemas: `app/schemas/` are the source of truth; coordinate breaking changes with clients.
- Auth and tiers: API key + user sessions; VIP/Pro tier routing enforced in middleware.

## Verification (preferred approach)
- Run quiet first; re-run narrowed failures with verbose logs only when debugging.
- Use module AGENTS.md for exact commands and setup.

## Docs usage
- Do not open/read `docs/` unless the user asks or the task requires it.

## Global conventions and hard rules
- Never mock `builtins.__import__` or `builtins.float` (xdist timeouts).
- CI requires >=97% coverage; keep tests updated.
- Never push to `main`; use feature branches.
- Test DB isolation: each xdist worker uses a unique SQLite path.
- Require Marshmallow >=4.1.2 (CVE fix).
- Formatting: Black line-length=100; keep PEP 8; ruff linting enforced.
- Pre-commit hooks run tests on changed files; keep changes minimal and focused.
- Use Pydantic v2 APIs and FastAPI best practices for backend changes.

## Known pitfalls
- Dual Base issue: Fixed in PR #403. `app/__init__.py` now uses PEP 562 forwarding to `legacy_app`.
  Import hygiene guards prevent regression.

## Import Hygiene Checklist (must-run before PR / after rebase)

### Goal
Prevent regressions to dynamic imports / sys.path hacks / sys.modules patching that cause xdist hangs,
dual-namespace imports, and missing legacy exports.

### Allowed exceptions
Dynamic import / sys.path.insert is allowed ONLY for standalone script tests:
- `tests/test_test_pro_access_coverage.py`
- `tests/test_ensure_database_versions.py`

### 1) No dynamic import patterns in tests (except allowed)
```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- tests \
  | grep -vE "test_test_pro_access_coverage\.py|test_ensure_database_versions\.py|conftest\.py" || true
```

### 2) No sys.path.insert in tests (except allowed)
```bash
git grep -n "sys\.path\.insert" -- tests \
  | grep -vE "test_test_pro_access_coverage\.py" || true
```

### 3) No sys.modules mutation in tests
```bash
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- tests || true
```

### 4) Verify app shim contract (PEP 562 shim)
`import app` must be a stable facade for legacy surface.
```bash
git grep -nE "import legacy_app|app\s*=\s*_legacy\.app|def __getattr__|def __dir__" -- app/__init__.py
```

### 5) Verify TESTING env set before imports in conftest
```bash
git grep -nE "TESTING" -- tests/conftest.py
git grep -nE "import app|import legacy_app|from app import|from legacy_app import" -- tests/conftest.py
```
Ensure `TESTING=true` is set BEFORE importing app/legacy_app.

### 6) Guard tests must pass
```bash
pytest -q tests/test_import_hygiene_guard.py tests/test_env_guards.py -q
```

### 7) Export route smoke (only if exports are feature-flagged)
```bash
python - <<'PY'
import os
os.environ["TESTING"] = "true"
import app
paths = {r.path for r in app.app.routes}
assert "/api/v1/export/pdf" in paths
print("OK: export route registered")
PY
```

### Notes
- Never reintroduce `spec.loader.exec_module` in `app/__init__.py`.
- Prefer package imports: `import app.services.X as X`, not file loading.
- Do not move sys.path hacks into conftest; localize any script-only needs to the specific test file.

### 8) Scripts must not use dynamic imports for app internals
```bash
git grep -nE "spec_from_file_location|exec_module|sys\.modules\[" -- scripts || true
```
- `scripts/` may use `sys.path.insert` for standalone CLI only
- Scripts must NOT create `Base` or manipulate SQLAlchemy metadata
- Direct imports from `core`/`app` are allowed if using standard package imports

## Links to module instructions
- `app/AGENTS.md`
- `core/AGENTS.md`
- `frontend/AGENTS.md`
- `ios/AGENTS.md`
- `deploy/AGENTS.md`
- `providers/AGENTS.md`
- `tests/AGENTS.md`
