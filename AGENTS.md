# Agent instructions (scope: repo root and subdirectories)

## 🚫 Hard Gates (Non-negotiable)

An agent MUST NOT claim a PR is "green", "ready", or "mergeable" unless ALL pass locally:

```bash
make verify   # runs: lint → typecheck → test-fast → diff-cov (≥97%)
```

Or individually:
- `make lint` — ruff/flake8 checks
- `make typecheck` — mypy with no cache (`--no-incremental --cache-dir=/dev/null`)
- `make test-fast` — pytest quick run
- `make diff-cov` — diff-cover ≥97% against origin/main

**If ANY command fails:**
1. Paste raw output lines showing the failure
2. Provide `file:line:error` pointers
3. Do NOT write "готово", "green", "mergeable"
4. Fix the issue first, then re-run `make verify`

**❌ Forbidden:**
- Saying "all checks pass" without showing command outputs
- Using `|| true`, `continue-on-error`, or ignoring failures
- Adding `# type: ignore` without explicit user approval
- Testing dead code instead of deleting it

**Dead code policy:**
If diff-cover shows uncovered helpers that have zero call sites → **delete them**, don't write tests for unused code.

---

## REQUIRED READING (before any change)
1) `docs/ENGINEERING_LESSONS.md` (project-level lessons and hard-won invariants)
2) `RUNBOOK_AGENT.md` (CI/debug playbook)
3) The nearest scoped `AGENTS.md` for the files you touch (e.g. `tests/AGENTS.md`, `scripts/AGENTS.md`)

If your change conflicts with these docs, you must explain why and how risks are mitigated.

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

## Engineering lessons
See: `docs/ENGINEERING_LESSONS.md` (derived from PR-8b).
Captures project-level lessons: test determinism, diff-coverage, portability, error contracts, sys.modules policy.

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

## CI PR scope guard (scripts/ci/pr_scope_guard.sh)

A repository-wide guard that runs early in CI to prevent PR bloat and mixed concerns.

**When it runs**
- In CI for PRs/MRs (GitHub Actions / GitLab).
- Can be run locally: compares `origin/<base>` vs `HEAD` (base defaults to `main`, override via `PR_SCOPE_BASE_REF`).

**Exit codes**
- `0` — OK / skipped (e.g., cannot fetch base ref locally)
- `1` — BLOCK (scope violation)
- `128` — hard failure (base ref resolution/checkout misconfigured in CI)

**Enforced checks**
1. **Always BLOCK:** any `*.py` under `docs/pr/`
2. **Runtime PRs only:** block planning docs in `docs/pr/`:
   `PR_<n>_(READY|ROADMAP|HANDOFF|AUDIT_REPORT|REVIEW_CHECKLIST).md`
3. **Warnings (non-blocking):**
   - file count > ~15 (info), > ~30 (warning)
   - runtime PRs with >2 markdown files (mixed-concern signal)

**How to pass**
- Put tests in `tests/`, never under `docs/pr/`.
- Keep runtime PRs focused: aim for `<15 files`, and limit docs to 1–2 contract/spec markdown files.
- If you need planning docs, move them to a separate docs-only PR.
- For full rules and CI setup, see:
  - `docs/policy/PR_SCOPE_GUARD_CI_SETUP.md`
  - `docs/policy/PR_SCOPE_RULES.md`

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
- Pre-push backend tests are diff-based; see `scripts/AGENTS.md` for details.
- Use Pydantic v2 APIs and FastAPI best practices for backend changes.

### 🛑 Docs-only PR Rule (Mandatory)

**Docs-only PR** — это PR, который **строго ограничен документацией** и **не имеет права** изменять runtime, CI или поведение приложения.

**Allowed changes (docs-only):**
* `*.md` files
* `README.md`
* `AGENTS.md`, `RUNBOOK_AGENT.md`, `DEPLOYMENT.md`
* `.github/*.md` (templates, instructions)

**❌ Forbidden changes (docs-only):**
* Any source code (`*.py`, `*.js`, `*.ts`, `*.swift`, etc.)
* CI / infra (`*.yml`, `Dockerfile`, `Makefile`, `requirements*`)
* Runtime configs or imports
* **Any change to application behavior**, even if it is a "cleanup" or "revert"

**Enforcement checklist (before push):**

Before pushing a docs-only PR, **you MUST run**:

```bash
git diff --name-only origin/main...HEAD \
  | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$"
```

* Output **must be empty**.
* If any non-doc file appears → **STOP** and revert it from the PR.

**Special note about legacy files:**
* Files like `legacy_app.py` **MUST NOT** appear in docs-only PRs.
* If a docs PR accidentally touches code, it must be **reset to `origin/main`** and removed from the diff.
* Code cleanup related to other PRs (e.g. PR-457) **belongs only to that PR**, never to docs PRs.

**Rationale:**
This rule exists to prevent accidental regressions, keep PR reviews focused and safe, avoid CI failures caused by unrelated changes, and enforce clean separation between **documentation governance** and **runtime evolution**.

**Policy reference:** See `docs/policy/DOCS_ONLY_PR_POLICY.md` for the canonical policy source of truth.

Violation of this rule blocks merge.

## Known pitfalls
- Dual Base issue: Fixed in PR #403. `app/__init__.py` now uses PEP 562 forwarding to `legacy_app`.
  Import hygiene guards prevent regression.

## Duplicate modules / imports policy (critical)

### Hard rules
- There must be exactly ONE FastAPI app instance used by runtime and tests.
  - Entrypoint: `app.main:app`
  - `app/__init__.py` is a shim only (no dynamic loading).

- Forbidden patterns (cause namespace duplication / Dual Base):
  - `importlib.util.spec_from_file_location`
  - `importlib.util.module_from_spec`
  - `spec.loader.exec_module`
  - `sys.path.insert(...)`
  - mutating `sys.modules[...] = ...` (except explicitly whitelisted guard cases)

### Source of truth
- Domain logic → `core/`
- FastAPI layer → `app/routers/` (thin)
- Storage adapters → `app/services/` (thin wrappers calling `core/`)
- Legacy entrypoint → `legacy_app.py` (compat only; no new features here)

### If you see duplicate behavior
- Do NOT copy logic into a second place.
- Move shared logic into `core/` and call it from both sides.

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

## Deployment docs
- `DEPLOYMENT.md` → `docs/deploy/README.md`

---

## AGENTS Update Rule (Canonical)

### Purpose
Prevent instruction drift, duplication, and conflicting rules across agents.
There must be a **single source of truth** for each class of instruction.

### Canonical rules

1) **Global rules live ONLY in root `AGENTS.md`.**
   - Architecture invariants
   - Import hygiene
   - CI / coverage gates
   - Commit / PR process rules

2) **Scoped rules live ONLY in the nearest `*/AGENTS.md`.**
   - Module-specific commands
   - Local setup or tooling
   - Narrow exceptions explicitly scoped to that module

3) **Do NOT duplicate identical text across multiple AGENTS files.**
   - If a rule applies everywhere → root `AGENTS.md`
   - If a rule applies to one module → that module's `AGENTS.md`

4) **When new workflow, invariant, or command is introduced:**
   - Update exactly **ONE** document:
     - `AGENTS.md` (global), OR
     - `X/AGENTS.md` (scoped)
   - Never "broadcast" the same instruction into multiple AGENTS files.

5) **PR requirement**
   - Any PR that changes engineering workflow, guards, or agent behavior
     MUST include a documentation commit:
       `docs(agents): update instructions`

6) **Escalation path**
   - Long-term lessons → `docs/ENGINEERING_LESSONS.md`
   - Operational/debug procedures → `RUNBOOK_AGENT.md`
   - Do not overload AGENTS with runbook-level detail.

### Non-goals
- AGENTS files are NOT changelogs.
- AGENTS files are NOT PR notes.
- AGENTS files must remain stable and auditable.
