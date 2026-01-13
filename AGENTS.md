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
make cov-check  # Total coverage ≥97%
make diff-cov   # Diff-coverage ≥97% on changed lines
```

**Coverage rule (hard):**
- Never use per-file coverage % as a readiness signal.
- Only `make cov-check` (total ≥97%) + `make diff-cov` (diff-coverage ≥97%) count.
- If CI is red, PR is not ready.
- File-level coverage (e.g., "95.5% for app/middleware/metrics.py") is NOT a gate metric.

**legacy_app.py policy (hard):**
- `legacy_app.py` is a thin compatibility proxy only.
- Forbidden: registering middleware, observability/instrumentation, infra routes (/metrics), or any runtime behavior changes.
- All middleware/observability registration must live in bootstrap modules (e.g., `app/bootstrap/metrics.py`) and be called from the primary app entrypoint (e.g., `app/main.py`).
- `legacy_app.py` must only contain: thin proxies, response formatting, legacy endpoint shims.
- This prevents drift and keeps legacy as a pure compatibility layer.

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

## BMI anti-duplication guard (PR-502)

**Guard test:** `tests/test_no_bmi_math_outside_core.py`

**What it enforces:**
- BMI formulas/thresholds/constants ONLY allowed in `core/bmi/*`
- `legacy_app.py` is scanned (no longer whitelisted)
- Any hardcoded thresholds (18.5/24.9/25/30 for BMI, 80/88/94/102 for waist) outside `core/bmi/` → FAIL

**Canonical sources:**
- Waist risk thresholds: `core/bmi/risk._waist_thresholds()`
- Waist risk note (compat): `core/bmi/risk.get_waist_risk_note()`
- Healthy BMI range: `core/bmi/engine.HEALTHY_BMI_RANGE`

**❌ Forbidden in `legacy_app.py`:**
- `warn, high = (94, 102)` or similar
- `{"min": 18.5, "max": 24.9}` or similar BMI literals
- Any BMI category logic (use `core/bmi/engine`)

**✅ Allowed in `legacy_app.py`:**
- Thin proxies that import and delegate to `core/bmi/*`
- Response shape formatting (no domain logic)

---

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

## Product tiers and API namespaces (canonical)

### Product tiers (source of truth)
- **Tiers are: FREE / PRO / VIP** (per `SubscriptionTier` enum in `app/middleware/api_tiers.py`).
- **`/premium/*` is a deprecated namespace** (aliases only), not a tier.
- **VIP endpoints MUST live under `/api/v1/vip/*`** (canonical namespace).

### Testing tier guards (VIP/PRO endpoints)
- **All tests that call VIP endpoints and expect 200/422/404 MUST use valid VIP key** (`vip_headers` fixture from `tests/conftest.py`).
- **Guard-consistency tests assert status codes only** (not error payload shape); payload-shape belongs to dedicated contract tests.
- **FREE tier tests use empty headers** (`{}`), not a "FREE key" — FREE = no key required.
- **Tests must not mutate `os.environ` directly** — use `monkeypatch.setenv` (prefer an `autouse` fixture for class-level suites).
- **Type hints required for all new or modified functions** (including tests).
  - OK: `def test_x(vip_headers: dict[str, str]) -> None:`
  - Not OK: `def test_x(vip_headers):` (missing types)
  - When unsure: prefer explicit `-> None` for test functions.
  - **No mass type-hint sweeps** — fix opportunistically when touching files, or when CR requests it locally.
- **VIP guard matrix lives in `tests/test_vip_tier_guard_matrix.py`** — do not duplicate this matrix in other vip_* tests.
- **sys.modules mutation forbidden** — use `monkeypatch.delitem(sys.modules, name, raising=False)` and `monkeypatch.setitem(sys.modules, name, value)` instead of direct `del sys.modules[...]` or `sys.modules[...] = ...`.
- **Env vars set in tests must be cleaned in teardown** — all variables set in `setup_method` must be popped/restored in `teardown_method` to prevent xdist pollution.
- **Dependency override pattern:**
  - If test overrides `require_vip_tier` dependency → do NOT send `vip_headers` (guard is bypassed)
  - If test name includes `_with_guard_bypassed` → override is intentional for business logic testing
  - If test name does NOT include bypass marker → no overrides, use real keys
- **Forbidden:** Testing private `_require_*` functions from routers — use behavioral tests through `TestClient` + middleware.
- **When tier guards are tightened:** All existing tests calling protected endpoints must be updated to use appropriate tier keys, otherwise tests check auth instead of business logic.
- **PRO endpoints MUST live under `/api/v1/pro/*`** (canonical namespace).
- **FREE endpoints live under `/api/v1/bmi/*`** and other free paths.

### API namespace policy
- **Canonical namespaces:** `/api/v1/bmi/*` (FREE), `/api/v1/pro/*` (PRO), `/api/v1/vip/*` (VIP).
- **Deprecated namespace:** `/api/v1/premium/*` (aliases only, must delegate to canonical `/pro/*` or `/vip/*`).
- **OpenAPI must not expose deprecated aliases by default** (hide `/premium/*` from schema to prevent frontend from generating types for wrong paths).
- **File naming must not imply tier unless enforced** (e.g., `bmi_pro.py` is FREE tier, not PRO).

### Tier enforcement
- PRO tier: use `require_pro_tier()` middleware (from `app.middleware.api_tiers`).
- VIP tier: use `require_vip_tier()` middleware (from `app.middleware.api_tiers`).
- All `/premium/*` endpoints must delegate to canonical handlers (no business logic in aliases).
- **Deprecated alias hard-stop (contracts):** never proxy between endpoints with different `response_model` (that is a breaking change).
- **Plate policy:** `premium/plate` must proxy only to `pro/nutrition/plate` (`PlateRequest` → `PlateResponse`), never to `pro/nutrition/daily` (`DailyNutritionResponse`).
- **Weekly policy:** if `premium/plan/week` is VIP-dependent or contract-incompatible, do not proxy it to PRO; use `premium/plan/week-flexible` as the sanctioned deprecated PRO-compatible bridge.
- **Guard divergence:** Premium aliases may use legacy guards (`_get_api_key_dynamic`) while canonical PRO endpoints use tier guards (`require_pro_tier`). This is intentional for backward compatibility; guard alignment is a separate product/infra decision. See `docs/audit/PR_520_INSIGHTS.md` for enforcement checklist and recurring anti-patterns.
- **Do not use `Header(...)` in tier dependencies** — use `Security(api_key_header)` to ensure OpenAPI models credentials as security scheme (not per-operation header params). This prevents OpenAPI drift and dirty TypeScript types.
- **Tier guard order**: Tier checks (403) must run before payload validation (422). Principle: "tier wins over payload".

**See:**
- `docs/contracts/PRODUCT_TIER_MAP.md` — contract/specification (what IS)
- `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md` — remediation roadmap (what we DO)

## OpenAPI generation (determinism requirement)

### Canonical source
- **Do not edit** `frontend/src/api/openapi.json` or `frontend/src/api/schema.ts` manually.
- Canonical OpenAPI source: `app.main.app` (bootstrap + metrics applied).
- Generator: `scripts/generate_openapi.py` (single source of truth for CI and local).
- **OpenAPI generation policy**: OpenAPI must be generated via `make openapi` (never direct `python scripts/generate_openapi.py`). CI and local must use the same entrypoint.
- `frontend/AGENTS.md` should link to this section as the canonical OpenAPI workflow (AGENTS Update Rule); do not duplicate these bullets there.

### SQLAlchemy model import policy (critical)
- **Forbidden**: Import SQLAlchemy models at module level in routers that are included in OpenAPI generation.
- Routers that import `app.models.*` must be conditionally imported when `PULSEPLATE_OPENAPI=1` to prevent SQLAlchemy "Table already defined" errors.
- **Allowed**: Import models inside endpoint functions or dependencies (lazy loading).
- **Rationale**: OpenAPI generation must not trigger SQLAlchemy table creation to ensure deterministic schema generation.

### OpenAPI generation mode
- Generator sets `PULSEPLATE_OPENAPI=1` before importing app.
- Routers that import SQLAlchemy models (e.g., `premium_week`, `pro`) are skipped in this mode.
- This ensures schema generation does not load DB layer and prevents double-loading errors.

### Determinism requirement
- Determinism is enforced by `pytest tests/test_openapi_determinism.py`.
- If drift appears: fix **generator normalization** in `scripts/generate_openapi.py`, not "accept drift".
- Local verification: run `make openapi` and then `make openapi-check`.
- **If OpenAPI sync fails in CI** → first check generated artifacts under `frontend/src/api/*` and run `make openapi` locally, then commit the updated artifacts.
- **Normalization policy**: Never sort semantically meaningful OpenAPI list keys (`required`, `enum`, `allOf/anyOf/oneOf`, `prefixItems`, `examples`, etc.). Add to denylist before touching normalization.
- **Determinism gate**: If OpenAPI artifacts are committed/compared, add a determinism test (hash compare) in the CI job that owns it.

### Response model policy
- **Forbidden**: Endpoints returning `dict[str, Any]` or untyped responses.
- **Required**: All endpoints must use Pydantic `response_model` to ensure proper OpenAPI schema generation.
- **Rationale**: Untyped responses degrade to `unknown` in generated TypeScript types, making frontend integration impossible.

### Update flow
1. From repo root: `make openapi` (generates OpenAPI + regenerates TS types).
2. Commit changes to:
   - `frontend/src/api/openapi.json`
   - `frontend/src/api/schema.ts`
3. Verify locally: `make openapi-check` (fails if generated artifacts are not committed).
4. CI will fail if generated artifacts are out of sync (see the CI check that verifies generated artifacts).

### Test requirement
- `pytest tests/test_openapi_determinism.py` **must pass** and cannot be disabled/weakened.
- Any changes to routers/schemas must preserve determinism.

### Documentation requirement
- If a PR changes workflow/agent behavior/tooling, include a `docs(agents): ...` commit in the same PR.

### 🛑 Docs-only PR Rule (Mandatory)

**Docs-only PR** — a PR strictly limited to documentation that **must not** change runtime, CI, or application behavior.

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
* Code cleanup related to other PRs **belongs only to that PR**, never to docs PRs.

**Rationale:**
This rule exists to prevent accidental regressions, keep PR reviews focused and safe, avoid CI failures caused by unrelated changes, and enforce clean separation between **documentation governance** and **runtime evolution**.

**Canonical policy:** This section in `AGENTS.md` is the source of truth.
**Last updated:** 2026-01-11

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

## Git conflict resolution (canonical ritual)

If `git push` fails with "failed to push some refs" (conflict):

**Required steps (in order):**
```bash
# 1. Fetch latest from remote
git fetch origin

# 2. Rebase on top of main (preserves linear history)
git rebase origin/main

# 3. Resolve conflicts if any (edit files, then):
git add <resolved-files>
git rebase --continue

# 4. Verify tests still pass after rebase
make test-fast
make cov-check

# 5. Push with force-with-lease (safe force push)
git push --force-with-lease
```

**Hard rules:**
- ❌ Never use `git push -f` without `--force-with-lease` (unsafe, can overwrite others' work)
- ❌ Never push after rebase without re-running `make test-fast` and `make cov-check`
- ❌ Never use `git pull` (without rebase) unless you explicitly want a merge-commit (usually not)
- ✅ Always rebase (don't merge main into feature branch) to keep history linear
- ✅ If CI is red → PR does not exist. Any work except fixing CI is forbidden.

**Why force-with-lease:**
- Prevents overwriting remote changes you haven't seen
- Fails if someone else pushed to your branch (forces you to fetch first)

**Alternative (no force, preferred when branch is polluted):**
- Create a fresh branch from `origin/main` and cherry-pick/squash only relevant commits.
- Open a new PR from the clean branch; close the old PR as superseded.
- This avoids force push entirely and keeps history clean without risk of overwriting others' work.

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
