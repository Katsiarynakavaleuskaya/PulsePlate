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

**Pre-commit hook policy (mandatory before push):**

- **Always run `pre-commit run --all-files` locally before pushing any PR.**
- **If hooks modify files:**
  1. Run `pre-commit run --all-files`
  2. Check `git status` for modified files (e.g., `.secrets.baseline`, whitespace fixes, formatting)
  3. **Commit hook modifications as a separate commit:** `chore(pre-commit): apply hook fixes`
  4. **Important:** If `detect-secrets` updated `.secrets.baseline`, this must be committed (it's a legitimate baseline update, not a secret leak)
- **Policy note:** `.secrets.baseline` is a generated `detect-secrets` artifact with hashed fingerprints; it is excluded from Sourcery scans (false-positive “Generic API Key”).
- **Carryover rule:** If a PR intentionally carries over missed changes from a prior PR, the PR description MUST include a short **Carryover** note and the work MUST be tracked in `docs/roadmap/BACKLOG_LEDGER.md` (entry updated to point to that PR).
- CI runs `pre-commit run --all-files` and will fail if hooks would modify files that aren't committed.
- This is not optional: uncommitted hook modifications guarantee CI failure.
- **One-time setup:** Run `pre-commit install` locally once to enable automatic hook execution on `git commit` (reduces CI noise).

**Pre-commit and "expected red" PRs (guard policy):**

- **`--no-verify` is allowed ONLY for "expected-red PR" (guards-first approach)** and **only** with explicit explanation in commit message and PR description.
- **Rationale:** Guard tests intentionally fail to document architectural violations. Pre-commit hook runs pytest and blocks commits when guards fail (expected behavior).
- **Process:**
  1. Guard Policy PR: Use `--no-verify` with explanation: "Pre-commit hook fails because guards intentionally document violations. This is expected behavior — guards will pass after remediation."
  2. Remediation PR: **Must pass pre-commit** (guards turn green, no `--no-verify` needed).
  3. **Future improvement:** Consider moving pytest from pre-commit to CI-only (or make it optional via `SKIP_TESTS=1` env var) to avoid blocking commits for expected-red PRs.
- **Note:** Pre-commit currently runs `backend-tests` hook (pytest) via `.pre-commit-config.yaml`. This is intentional for normal PRs, but creates friction for guard policy PRs. This is acceptable for now; process improvement can be done in separate PR.

**❌ Forbidden:**

- Saying "all checks pass" without showing command outputs
- Using `|| true`, `continue-on-error`, or ignoring failures
- Adding `# type: ignore` without explicit user approval
- Testing dead code instead of deleting it
- Pushing PRs without running `pre-commit run --all-files` first
- Using `SKIP=...` or disabling hooks without explicit justification (default: "fix it, don't skip it"; if skip is needed, document why in PR description/comment)

**Dead code policy:**
If diff-cover shows uncovered helpers that have zero call sites → **delete them**, don't write tests for unused code.

**Rate Limiting Policy:**

**Hard rule:** Expensive endpoints (LLM, exports) MUST be rate-limited AND MUST have deterministic 429 tests.
PRs that add expensive endpoints MUST include deterministic 429 tests (no smoke-only substitutes).
If adding rate-limit to endpoints, use thin **route wrappers**; do not change callable function signatures used by coverage tests.

**Enforcement:**

- All LLM endpoints (`/api/v1/insight`, `/insight`) MUST use `@limit_if_available(RATE_LIMIT_INSIGHT)`.
- All export endpoints (CSV/PDF) MUST use `@limit_if_available(RATE_LIMIT_EXPORTS)`.
- OpenAPI MUST document 429 responses for rate-limited endpoints: `responses=RATE_LIMIT_429_RESPONSES` (from `app/security/rate_limit.py`).
- Tests MUST verify 200 → 429 transitions with low limits (2/minute in tests).
- Rate-limited endpoints MUST accept `request: Request` in the handler signature (SlowAPI requirement).
- Runtime behavior is env-gated: in tests (`TESTING=true`) rate limiting is disabled unless `RATE_LIMITING_IN_TESTS=true`.
- Client identification uses proxy-aware key_func with CIDR support (`app/security/rate_limit.py`).

**LLM Monthly Quota Policy (Hard rule):**

- All LLM endpoints MUST enforce a **server-side monthly hard quota** **before** any provider call.
- Minimal baseline quota unit is **`requests/month`** (budget/cost-based quotas may be added later).
- Quota MUST be deterministic (no soft-limit-only behavior) and have tests that prove enforcement.
- CI container smoke-start MUST set `SERVER_SALT` (dummy value allowed) so app startup can pass fail-fast requirements.

**Rationale:**

- LLM endpoints: $72k/month abuse risk (documented in `BACKLOG_LEDGER.md`).
- Export endpoints: Resource-intensive (PDF generation, CSV streaming) → DoS risk.
- Deterministic tests prevent time-window flakiness.

**See:**

- Audit: `docs/audit/PR_628_RATE_LIMIT_LLM_EXPORTS_AUDIT.md`
- Implementation: `app/security/rate_limit.py`
- Tests: `tests/test_rate_limit_llm_and_exports_api.py`, `tests/test_rate_limit_client_key_api.py`

---

## REQUIRED READING (before any change)

1) `docs/ENGINEERING_LESSONS.md` (project-level lessons and hard-won invariants)
2) `RUNBOOK_AGENT.md` (CI/debug playbook)
3) The nearest scoped `AGENTS.md` for the files you touch (e.g. `tests/AGENTS.md`, `scripts/AGENTS.md`)

If your change conflicts with these docs, you must explain why and how risks are mitigated.

## Agent Coordination (Coordinator-First Rule)

**Hard rule:** Any new task MUST start with `agent-coordinator` for task analysis and agent routing.

### Definition of a Task (Canonical)

A **task** is any unit of work that:
- Affects code, documentation, architecture, security, or process; or
- Requires a decision, trade-off, or coordination between domains; or
- May impact quality gates, invariants, or downstream systems.

**Non-tasks (explicitly excluded):**
- Trivial typo fixes
- Formatting-only edits (whitespace, line breaks)
- Local experiments with no intent to commit

**Rule of thumb:** If unsure, treat it as a task and start with coordinator.

### Workflow

1. **Task Analysis** → Coordinator analyzes task, identifies domains, assigns priority
2. **Agent Assignment** → Coordinator routes to appropriate agent(s) based on capabilities
3. **Work Review** → Coordinator reviews agent outputs, verifies quality gates
4. **Synthesis** → Coordinator synthesizes multi-agent work into coherent solution
5. **DoD** → Coordinator verifies Definition of Done before PR merge

**Templates:**
- Task Analysis: `docs/orchestration/task_analysis.template.md`
- Work Review: `docs/orchestration/work_review.template.md`
- Synthesis: `docs/orchestration/synthesis.template.md`
- DoD: `docs/orchestration/dod.template.md`

**Full workflow:** See `docs/orchestration/workflow.md`

**Coordinator agent:** `.cursor/agents/agent-coordinator.md`

**Postponed items:** Any deferred work MUST be recorded in `docs/roadmap/BACKLOG_LEDGER.md` immediately.

**Rationale:** Ensures consistent task start, proper agent routing, quality gates, and systematic tracking of postponed work.

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
- **Diff-cover failures:** Fix ONLY via tests (preferred) unless behavior is wrong; do not rewrite code solely for coverage.

**legacy_app.py policy (hard):**

- `legacy_app.py` is a thin compatibility proxy only.
- Forbidden: registering middleware, observability/instrumentation, infra routes (/metrics), or any runtime behavior changes.
- All middleware/observability registration must live in bootstrap modules (e.g., `app/bootstrap/metrics.py`) and be called from the primary app entrypoint (e.g., `app/main.py`).
- `legacy_app.py` must only contain: thin proxies, response formatting, legacy endpoint shims.
- This prevents drift and keeps legacy as a pure compatibility layer.

**DB fallback policy (hard, TP2):**

- DB fallback implementation lives **only** in `core/db_fallback.py`. Single source of truth.
- `legacy_app.py` must **not** define fallback helpers or `_db_fallback_active`; it may only *delegate* to `core.db_fallback`.
- **DB lifecycle invariant:** In `core/`, `SessionLocal.configure()` is forbidden; on fallback use only reassignment via `sessionmaker(bind=engine, ...)`.
- **State mutation policy:** `_db_fallback_active` must not be written/read directly outside `core/db_fallback.py`; use `set_fallback_active()`, `clear_fallback_active()`, `reset_fallback_state()`, and `is_fallback_active()`.
- Health/status checks must use `is_fallback_active()` (or module access `fallback_mod.is_fallback_active()`). **Forbidden:** `from core.db_fallback import _db_fallback_active` (stale-value risk).
- Tests must import/patch fallback only via `core.db_fallback`; any global flag must be reset via `reset_fallback_state()` or fixture (autouse allowed).
- **Test hygiene:** Any test that mutates `core.db.SessionLocal` or calls `_configure_session_bindings` **must** restore `core_db.SessionLocal` and env keys (`DB_HEALTH_DEGRADED`, `DB_FALLBACK_URL`, `DATABASE_URL`) in a `finally` block or via `monkeypatch`.

**Module/package collision (hard):** Never introduce `core/<name>/` (package) when `core/<name>.py` (module) exists; Python would resolve `core.<name>` to the package and break imports. Use a non-colliding name (e.g. `core/db_fallback.py`) instead.

**Dockerfile policy (hard):**

- Do not pin `pip` to an exact version in the Dockerfile (e.g., `pip==24.2`). Exact pins can fail when the build environment cannot resolve the version from PyPI index (proxy/index/TLS issues).
- Prefer using base image pip without upgrade, or upgrade without version pin if upgrade is required.
- If a pip version constraint is required, use a version range and document the reason + CI verification.
- **Security fixes for Python dependencies must be done via `requirements.in`/`requirements.txt`, not via ad-hoc `pip install -U ...` in Dockerfile.** We allow unsafe packages (setuptools/pip/wheel) in lockfiles via `pip-compile --allow-unsafe` so security fixes live in `requirements.txt` and Dockerfile remains simple (no upgrade/install steps).
- **Python 3.13+ compatibility:** If CI/main uses Python 3.13+, then `greenlet` must be `>=3.1.0,<4.0.0` (greenlet 3.1.0+ adds Python 3.13 support; 3.0.x may fail to build/run on 3.13).
- Smoke tests must build the image on the current base image; any Python base image bumps → verify tooling compatibility (pip/setuptools/wheel).

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

### Exit codes

- `0` — OK / skipped (e.g., cannot fetch base ref locally)
- `1` — BLOCK (scope violation)
- `128` — hard failure (base ref resolution/checkout misconfigured in CI)

### Enforced checks

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
- Any hardcoded thresholds (18.5/24.9/25/30 for BMI, 80/88/94/102 for waist, 0.95/0.80/0.90/0.85 for WHR) outside `core/bmi/` → FAIL

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

**Guard scanner requirements:**

- **Docstring tracking:** Guard scanners must not be state-breakable by one-line triple-quoted docstrings. Parity-based tracking (or tokenize) required.
- **Pattern tests:** Regex guard patterns must have explicit tests for any new thresholds (including near-miss values to verify precision).
- **Docstring state update:** Docstring state must be updated BEFORE `SKIP_LINE_RE` check to ensure docstrings starting with `"""` are properly tracked.

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

## Health and readiness endpoints (operational semantics)

**Liveness vs Readiness:**

- **`/health`** = liveness probe: **always returns 200**, no DB dependencies. Used by orchestrators to determine if container should be restarted.
- **`/ready`** = readiness probe: **may return 503 if DB unavailable**. Used by orchestrators to determine if container should receive traffic.
- **`/health/db`** = explicit DB health check: returns 503 if DB unavailable.

**Rules:**

- `/health` endpoint must **never** depend on external services (DB, external APIs). It should always return 200 to indicate the process is alive.
- `/ready` endpoint **may** return 503 if dependencies (DB, external services) are unavailable. This is correct behavior for readiness checks.
- Tests for "metrics/health paths" should allow 503 for `/ready` but expect 200 for `/health`.
- Docker HEALTHCHECK should use `/health` (liveness), not `/ready` (readiness).

**Rationale:** Separating liveness and readiness allows orchestrators to:

- Restart containers that fail liveness (process dead)
- Stop routing traffic to containers that fail readiness (dependencies unavailable)

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

## Thin HTTP Adapter Policy (Hard Rule)

**Invariant:** Clients (iOS/Web) must be **thin adapters only** — zero business logic, only transport/contract/UX.

**Forbidden on clients:**

- ❌ Any BMI/waist/risk calculation formulas (thresholds, categories, interpretations)
- ❌ Any business logic that duplicates backend domain rules
- ❌ Any "smart" inference or computation from API responses (only display as-is)
- ❌ Hand-rolled DTOs that are not generated or kept in sync with backend schemas (OpenAPI-generated types for Web; aligned DTOs for iOS are allowed)

**Allowed on clients:**

- ✅ HTTP transport layer (baseURL, headers, JSON encode/decode, timeouts, retries)
- ✅ Error envelope mapping (422/400/5xx → UI-friendly messages)
- ✅ i18n localization of backend-provided keys
- ✅ UI formatting (rounding numbers for display, date formatting, not recalculation)
- ✅ Conditional rendering based on API response fields (UI logic, not computation)
- ✅ OpenAPI-generated types (`openapi-typescript` for Web, aligned DTOs for iOS)

**Contract-first principle:**

- Any DTO changes → update OpenAPI/contract docs first, then regenerate client types
- Clients must follow canonical error envelope format (no "guessing" error structure)
- Backend `app/schemas/` is the source of truth; clients are consumers only

**Enforcement:**

- iOS: `ThinClientGuardsTests` (scans for BMI thresholds/computation patterns)
- Web: `thin-client-guards.test.ts` (scans for BMI thresholds + direct fetch violations)
- Web: TypeScript types from OpenAPI (prevents manual DTO drift)
- Code review: grep for forbidden patterns (BMI math, threshold literals, category inference)

**Guard PRs and expected-red workflow:**

Some guard PRs are intentionally **expected-red** to expose real policy violations.
Remediation must happen in a follow-up remediation PR.

Source of truth:
- Audit docs: `docs/audit/*`
- Canonical backlog: `docs/roadmap/BACKLOG_LEDGER.md`

**DTO contract rules:**

- SoftPaywall availability MUST include `reason_key` if present; never drop fields silently.
- Legacy DTOs may remain temporarily, but must be tracked in BACKLOG_LEDGER with migration PR.
- All DTO fields must match backend schema exactly (no "convenient" omissions).

**No dual-path networking (hard rule):**

- ❌ **Forbidden:** Any new network calls using direct `URLSession` or custom HTTP clients
- ✅ **Required:** All new network calls MUST use `APIClient`/`HTTPClient` (iOS) or thin fetch wrapper (Web)
- **Rationale:** Prevents code duplication, ensures consistent error handling, enforces thin client policy
- **Enforcement:** Code review + grep for `URLSession.shared.data(for:)` or custom HTTP clients
- **Migration:** Existing services (ShoppingListService, WeeklyPlanService) must migrate to `APIClient` — tracked in `BACKLOG_LEDGER.md` (P1 item)

**External URL security (hard rule):**

- ❌ **Forbidden:** Sending API credentials (headers or cookies) to external URLs
- ✅ **Required:** External fetch MUST omit credentials and strip auth headers
- **Enforcement (Web):** Unit test `client.fetchBlob.test.ts` verifies `credentials: 'omit'` and header stripping
- **Rationale:** Signed URLs contain auth token in query; sending API key to external domain = credential leak
- **Implementation:** `fetchBlob()` in `frontend/src/api/client.ts` with URL classification (`/api/...` vs `https://...`)

**See:**

- `ios/AGENTS.md` — iOS Thin Client Policy (detailed)
- `frontend/AGENTS.md` — Frontend Thin Client Policy (detailed)
- `docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md` — Web adapter audit
- `docs/BMI_CANONICAL_HANDOFF.md` — One BMI Engine invariant
- `docs/CONTEXT_HANDOFF_2026-01-21.md` — Thin HTTP adapter PR plan

## Verification (preferred approach)

- Run quiet first; re-run narrowed failures with verbose logs only when debugging.
- Use module AGENTS.md for exact commands and setup.

## Docs usage

- Do not open/read `docs/` unless the user asks or the task requires it.

## Global conventions and hard rules

- Never mock `builtins.__import__` or `builtins.float` (xdist timeouts).
- **Forbidden: monkeypatching builtins** (`float`, `int`, `str`, `datetime`, etc.) and private compute operators (e.g., `float.__truediv__`). In Python 3.13+, many builtins are immutable, causing test failures and teardown errors. Test non-finite/overflow/edge cases via **inputs** (e.g., `math.inf`, `math.nan`) or controlled context (`decimal.localcontext()`), not by patching builtins.
- **Forbidden: monkeypatching core compute functions** (e.g., `_compute_wht_ratio`, `_compute_whr`, `_compute_bmi`). Tests must stimulate branches through **input data** or through public/internal helpers in engine, not by patching the compute functions themselves. Router/adapter seams (e.g., `calculate_bmi_result` in routers) may be patched for thin adapter testing.
- CI requires >=97% coverage; keep tests updated.
- Never push to `main`; use feature branches.
- Test DB isolation: each xdist worker uses a unique SQLite path.
- Require Marshmallow >=4.1.2 (CVE fix).
- Formatting: Black line-length=100; keep PEP 8; ruff linting enforced.
- Pre-commit hooks run tests on changed files; keep changes minimal and focused.
- Pre-push backend tests are diff-based; see `scripts/AGENTS.md` for details.
- Use Pydantic v2 APIs and FastAPI best practices for backend changes.

**Ruff ANN* rules (type hints) policy:**

- Ruff ANN* rules (`ANN201`, `ANN202`, `ANN401`, etc.) are **non-blocking** and serve as **technical debt indicators**.
- CI reports these warnings but does not fail the pipeline due to them.
- This is intentional: the codebase is large and mixed (core/legacy/scripts/providers), and enforcing ANN* as errors would block velocity.
- Enforcement will be introduced incrementally via scoped PRs (e.g., enable ANN* as blocking for `core/bmi` or `app/routers` only).
- Current state: **observability/tech-debt signal**, not enforcement.

## Product tiers and API namespaces (canonical)

### Product tiers (source of truth)

- **Tiers are: FREE / PRO / VIP** (per `SubscriptionTier` enum in `app/middleware/api_tiers.py`).
- **`/premium/*` is a deprecated namespace** (aliases only), not a tier.
- **VIP endpoints MUST live under `/api/v1/vip/*`** (canonical namespace).

### Product tier policy for BMI extras (hard rule)

**Invariant:** BMI extras calculations must explicitly distinguish Free/Simple vs Pro tier policies.

**Rationale:** Free and Pro tiers use different:

- Rounding precision (2 vs 3 decimal places)
- WHR thresholds (0.90/0.85 vs 0.95/0.80 for male/female)
- Return formats (tuple vs Dict)
- Feature availability (FFMI estimate mode in Pro only)

**Enforcement:**

- **One canonical module:** `core/bmi_extras.py` (satisfies guard requirement)
- **Explicit tier functions:** `*_simple()` for Free tier, `*_pro()` or base names for Pro tier
- **Documentation:** Each function must document which tier it serves and policy differences
- **No mixing:** Free endpoints use Simple tier functions; Pro endpoints use Pro tier functions
- **Allowed:** Pro endpoints may **map/adapt** Pro-tier outputs to legacy DTOs for backward compatibility (contract adaptation, not tier mixing)
- **Forbidden:** Calling any `*_simple()` (Free/Simple tier) functions inside Pro endpoints

**Canonical structure:**

```python
# core/bmi_extras.py structure:
# - Pro tier functions: wht_ratio(), whr_ratio(waist, hip, sex), ffmi(), stage_obesity(), interpret_*()
# - Free/Simple tier functions: wht_ratio_simple(), whr_ratio_simple(waist, hip), ffmi_simple(), stage_obesity_simple(), BMIProCard
```

**Product contract:**

- **Free tier:** BMI + category + basic WHtR (if waist available); no WHR, no FFMI, no staging
- **Pro tier:** All Free features + WHR (sex-specific) + FFMI (with estimate mode) + comprehensive staging + notes

**See:**

- `docs/audit/PR_REMEDIATION_BMI_EXTRAS_ANALYSIS.md` — Detailed tier analysis
- `docs/contracts/PRODUCT_TIER_MAP.md` — Full product tier documentation
- `docs/product/FREE_PRO_CONTRACT.md` — Full product tier contract

### Future scope (explicitly out of current remediation PR)

**VIP tier features (require separate audit and PR):**

- Personalized nutrition menus
- Store-based product selection
- Diet and cuisine preferences
- Goal-driven meal optimization
- Restaurant integration
- Advanced personalization logic

**Rationale:**

- Current remediation PR is **architectural/technical** — restoring invariants
- VIP tier requires separate product audit and design
- Menu automation and product selection are distinct from BMI calculation engine
- Normalization of existing Free/Pro tiers = OK (remediation)
- New features or VIP automation = NOT OK (separate PRs)

**When to implement:**

- After backend P0 remediation is complete (guards green)
- After product contract is established (FREE/PRO tiers)
- Requires separate audit: `docs/audit/VIP_TIER_AUDIT.md` (future)

**Key principle:**
> **PRO tier = automation of interpretation** (calculations, risk assessment)
> **VIP tier = automation of actions** (menus, products, planning)

### Remediation PR policy (hard rule)

**Scope discipline for architectural remediation:**

- **Remediation PR must fix violations and restore invariants** — guards green, `make verify` green, no obvious dead imports (ruff/mypy).
- **Allowed in remediation PR:**
  - Fixing tests that fail due to eliminated violations (legacy paths, duplicate modules, BMI math outside engine)
  - Updating imports to canonical paths
  - Removing tests that covered deleted/consolidated modules (only if replacement coverage exists)
- **Forbidden in remediation PR:**
  - "Cleanup for cleanup's sake" (unused code, orphan tests that don't fail)
  - Mass refactoring beyond scope
  - Coverage optimization unrelated to remediation
- **All warnings and failures must be fixed** — remediation PR must be clean (no `--no-verify`, no ignored warnings).

**Post-remediation follow-up:**

- Dead code removal, orphan test cleanup, coverage optimization → **separate PR**: `chore: remove dead code after BMI remediation`
- Rationale: Keeps remediation PR focused, reviewable, and mergeable without scope creep.

**See:** `docs/audit/PR_REMEDIATION_SELF_AUDIT.md` for detailed checklist.

### Testing tier guards (VIP/PRO endpoints)

- **All tests that call VIP endpoints and expect 200/422/404 MUST use valid VIP key** (`vip_headers` fixture from `tests/conftest.py`).
- **All tests that call PRO endpoints and expect 200/422/404 MUST use valid PRO key** (`pro_headers` fixture from `tests/conftest.py`).
- **PRO tier guard is mandatory** — all PRO endpoints MUST enforce `require_pro_tier` dependency. Tests without `pro_headers` will receive 401/403 (guard enforced before payload validation).
- **Guard-consistency tests assert status codes only** (not error payload shape); payload-shape belongs to dedicated contract tests.
- **FREE tier tests use empty headers** (`{}`), not a "FREE key" — FREE = no key required.
- **Tests must not mutate `os.environ` directly** — use `monkeypatch.setenv` (prefer an `autouse` fixture for class-level suites).
- **Never call `response.json()` without asserting `Content-Type` starts with `application/json`** — prevents cryptic errors when endpoint returns HTML or plain text on error.
- **Type hints required for all new or modified functions** (including tests).
- OK: `def test_x(vip_headers: dict[str, str]) -> None:` or `def test_x(pro_headers: dict[str, str]) -> None:`
- Not OK: `def test_x(vip_headers):` (missing types)
- When unsure: prefer explicit `-> None` for test functions.
- **No mass type-hint sweeps** — fix opportunistically when touching files, or when CR requests it locally.
- **VIP guard matrix lives in `tests/test_vip_tier_guard_matrix.py`** — do not duplicate this matrix in other vip_* tests.
- **sys.modules mutation forbidden** — use `monkeypatch.delitem(sys.modules, name, raising=False)` and `monkeypatch.setitem(sys.modules, name, value)` instead of direct `del sys.modules[...]` or `sys.modules[...] = ...`.
- **Env vars set in tests must be cleaned in teardown** — all variables set in `setup_method` must be popped/restored in `teardown_method` to prevent xdist pollution.
- **Dependency override pattern:**
- If test overrides `require_vip_tier` or `require_pro_tier` dependency → do NOT send `vip_headers`/`pro_headers` (guard is bypassed)
- If test name includes `_with_guard_bypassed` → override is intentional for business logic testing
- If test name does NOT include bypass marker → no overrides, use real keys
- **Forbidden:** Testing private `_require_*` functions from routers — use behavioral tests through `TestClient` + middleware.
- **When tier guards are tightened:** All existing tests calling protected endpoints must be updated to use appropriate tier keys, otherwise tests check auth instead of business logic.
- **PRO endpoints MUST live under `/api/v1/pro/*`** (canonical namespace).
- **FREE endpoints live under `/api/v1/bmi/*`** and other free paths.
- **Legacy deprecated aliases:** Tests should use canonical paths (`/api/v1/pro/bmi`), not deprecated aliases (`/api/v1/bmi/pro`). One test per deprecated alias is sufficient to verify backward compatibility.

### API namespace policy

- **Canonical namespaces:** `/api/v1/bmi/*` (FREE), `/api/v1/pro/*` (PRO), `/api/v1/vip/*` (VIP).
- **Deprecated namespace:** `/api/v1/premium/*` (aliases only, must delegate to canonical `/pro/*` or `/vip/*`).
- **Legacy aliases:** Deprecated endpoints in wrong namespace (e.g., `/api/v1/bmi/pro` for PRO tier) must be implemented as thin shims delegating to canonical endpoints. Both canonical and legacy paths must be guarded with appropriate tier dependencies.
  - **Example:** `POST /api/v1/bmi/pro` (deprecated) → thin proxy to `POST /api/v1/pro/bmi` (canonical). See `app/routers/bmi_pro_legacy_alias.py` for reference implementation.
- **OpenAPI must not expose deprecated aliases by default** (hide `/premium/*` from schema to prevent frontend from generating types for wrong paths).
- **File naming must not imply tier unless enforced** (e.g., `bmi_pro.py` router can be PRO tier if it uses `/api/v1/pro/*` namespace).
- **Frontend must not call `/api/v1/premium/*` endpoints** — use canonical `/api/v1/pro/*` or `/api/v1/vip/*` instead. Deprecated premium endpoints may be removed in future releases.

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
- **New metrics/features policy**: Any new metrics (e.g., WHR) must be added via tier-specific schemas + endpoints; FREE contract must not be extended without explicit tier policy decision.

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
- **Forbidden**: Import `app.models.*` (ORM models) at module level in any module that is reachable from OpenAPI generation (`make openapi` → `scripts/generate_openapi.py` → `app.main:app`).
- **Required wording (canonical)**: OpenAPI generation must be **side-effect free**: no import-time loading of ORM models and no `Base.metadata` registration along the OpenAPI import path.
- **Allowed**: Import models inside endpoint functions or dependencies (lazy loading).
- **Rationale**: OpenAPI generation must not trigger SQLAlchemy table creation to ensure deterministic schema generation.

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
2. **Mandatory:** Commit regenerated artifacts:

- `frontend/src/api/openapi.json`
- `frontend/src/api/schema.ts` (if changed)

3. Verify locally: `make openapi-check` (fails if generated artifacts are not committed).
4. CI will fail if generated artifacts are out of sync (OpenAPI sync check).

**Hard rule:** Any PR that changes OpenAPI (including metadata-only changes via `openapi_extra`) **must** commit regenerated `frontend/src/api/openapi.json` and `frontend/src/api/schema.ts` (if changed) and pass `make openapi-check`.

### Test requirement

- `pytest tests/test_openapi_determinism.py` **must pass** and cannot be disabled/weakened.
- Any changes to routers/schemas must preserve determinism.

### Documentation requirement

- If a PR changes workflow/agent behavior/tooling, include a `docs(agents): ...` commit in the same PR.

### 🛑 Docs-only PR Rule (Mandatory)

**Docs-only PR** — a PR strictly limited to documentation that **must not** change runtime, CI, or application behavior.

**Exception:** Security suppressions must be done in a dedicated **security PR** and may include Trivy ignore config (`.trivyignore` and/or `trivy/ignore-policy.rego`) + `docs/security/*.md` (see "PR Scope Policy (Hard Rule)").

**Allowed changes (docs-only):**

- `*.md` files
- `README.md`
- `AGENTS.md`, `RUNBOOK_AGENT.md`, `DEPLOYMENT.md`
- `.github/*.md` (templates, instructions)

**❌ Forbidden changes (docs-only):**

- Any source code (`*.py`, `*.js`, `*.ts`, `*.swift`, etc.)
- CI / infra (`*.yml`, `Dockerfile`, `Makefile`, `requirements*`)
- Runtime configs or imports
- **Any change to application behavior**, even if it is a "cleanup" or "revert"

**Enforcement checklist (before push):**

Before pushing a docs-only PR, **you MUST run**:

```bash
git diff --name-only origin/main...HEAD \
  | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$"
```

- Output **must be empty**.
- If any non-doc file appears → **STOP** and revert it from the PR.

**Special note about legacy files:**

- Files like `legacy_app.py` **MUST NOT** appear in docs-only PRs.
- If a docs PR accidentally touches code, it must be **reset to `origin/main`** and removed from the diff.
- Code cleanup related to other PRs **belongs only to that PR**, never to docs PRs.

**Rationale:**
This rule exists to prevent accidental regressions, keep PR reviews focused and safe, avoid CI failures caused by unrelated changes, and enforce clean separation between **documentation governance** and **runtime evolution**.

### Verification-audit rule (docs/audit/*)

- Any audit labeled **"Verified"** MUST include, for each key evidence command:
  - the exact command (single line)
  - 1–3 raw stdout/rg lines (may be truncated, but not paraphrased)
  - the exit code
- If output contains sensitive data, it MAY be minimally redacted, but redaction MUST be explicit
  (e.g. `[REDACTED]`) and must not remove the lines proving the condition.
- If observed output is missing, the audit is an **Opinion**, not **Evidence** (must not be treated as verified).

**Canonical policy:** This section in `AGENTS.md` is the source of truth.
**Last updated:** 2026-02-03

Violation of this rule blocks merge.

## Release readiness priorities (hard rule)

**Definition of Ready / Definition of Done for release:**

1. **P0-A: "Product Works"** (must-have before any release)
   - Core functionality works (BMI calculates, forms validate, API contracts match)
   - No "undefined" in UI results
   - Locale parsing works (RU comma → dot)
   - Error handling shows proper messages, not crashes
   - Forms submit valid data to backend
   - API responses are correctly rendered

2. **P0-B: "Can Publish"** (required for App Store/public launch)
   - App Store assets (screenshots, metadata)
   - Basic onboarding (at least 2 screens: value + usage)
   - Language switch works
   - Core user flows are complete

3. **P1: "Brand Magic"** (enhancements, not blockers)
   - Slogan, ECG/pulse animations, FitChef assets
   - Advanced UX, Storybook, design system polish
   - Visual refinements beyond functional requirements

**Hard rule:** Do not work on P1 items until P0-A is complete. "Brand magic" is worthless if the product doesn't calculate.

**Diagnostic approach for "BMI undefined" issues:**

1. **Request:** Check DevTools Network → URL + payload (JSON)
2. **Response:** Check status code + first fields of body
   - **422** → Form sends wrong data (parsing/fields/units) → Fix in PR-525
   - **200, but BMI null/undefined** → Render/field mapping broken in UI
   - **403** → API key/gate/PRO guard issue (not BMI math)
   - **500** → Server error (check logs/endpoint)

## BMI Engine Invariant (Hard Rule)

**Invariant:** *"One BMI Engine must be the sole calculation path for all BMI-related computations."*

**Enforcement:**

- Guard tests in `tests/test_bmi_canonical_guard.py`
- CI fails on violation
- No imports from `bmi_core` in `core/bmi/`
- Only one canonical extras module (or clear purpose)

**Legacy shim policy (`bmi_core.py`):**

- Legacy shim `bmi_core.py` **must preserve positional ABI** (e.g., `lang` = 5th positional in `auto_group`).
- Any shim must have **direct diff-cover tests** on all exported wrappers.
- Deprecated stubs: `(*args, **kwargs) -> raise RuntimeError` + test on raises (no silent None returns).
- Shim must **not contain BMI math** — all calculations delegate to `core/bmi/*`.

**Point of No-Return:**
> *"Until legacy dependency is removed, any downstream fixes (frontend, API contracts) are considered unreliable. The system cannot be diagnosed or fixed reliably until the invariant is restored."*

**Related:**

- `docs/audit/ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md` — Root cause analysis
- `docs/audit/BACKEND_P0_REMEDIATION_PLAN.md` — Remediation plan
- `docs/audit/BACKEND_P0_GUARD_POLICY_PROPOSAL.md` — Guard policy

## Soft Paywall hooks (policy)

**Invariant:** Soft paywall hooks must be built in adapter/router layer only (`app/routers/*`), never in `core/bmi/*`.

**Enforcement:**

- Guard test in `tests/test_no_bmi_logic_in_paywall.py`
- Hook builders must not import `core/bmi/*`
- Hook builders must not check BMI values or categories

**Forbidden:**

- Any BMI-dependent logic/branching for hook display (no thresholds, no categories, no "if BMI…")
- Importing `core/bmi/*` from hook builders
- BMI-based conditions for showing/hiding hooks

**Allowed:**

- Feature flags via env (`SOFT_PAYWALL_ENABLED`)
- i18n lookup via `core.i18n.t()`
- Hook formation in router/adapter layer only

**Rationale:**

- Hooks are UX/contract layer, not domain logic
- BMI logic belongs in `core/bmi/*` only
- Separation prevents accidental BMI logic drift into router layer

**Contract documentation:**

- Soft Paywall Hook contract: `docs/contracts/soft_paywall.md` (text-only, no `core.bmi.*` imports, disabled => `null`)

## Feature changes via PR (hard rule)

**Invariant:** Feature changes must land via a dedicated PR with explicit scope and DoD.

**Rules:**

- Do not mix unrelated scopes (e.g., security hygiene + product feature) in the same PR.
- Emergency hotfix is allowed only under `hotfix/*` branch naming and must remain scope-minimal.
- Docs-only PRs documenting already-merged features must reference the implementation PR/commit.

**Historical incident:** PR #543 mixed scopes — avoid повторения.

## Known pitfalls

- Dual Base issue: Fixed in PR #403. `app/__init__.py` now uses PEP 562 forwarding to `legacy_app`.
  Import hygiene guards prevent regression.

## Frontend form handling rules (hard)

### React Hook Form (RHF) integration

**Hard rule:** Custom input components with `onValueChange(value)` → **only use `Controller` pattern**, never `{...register()}`.

**Why:**

- `register()` expects DOM `onChange(event)`
- Custom components use `onValueChange(value)` → incompatible
- Direct `{...register()}` will cause bugs (values as strings, NaN, undefined)

**Correct pattern:**

```typescript
import { Controller } from "react-hook-form";
import { NumberInput } from "@/components/ui/number-input";

<Controller
  name="weight_kg"
  control={control}
  render={({ field }) => (
    <NumberInput
      value={field.value ?? ""}
      onValueChange={field.onChange}   // (number | "") => void
      onBlur={field.onBlur}
      locale="ru"
    />
  )}
/>
```

**Alternative (quick fix):** Use `setValueAs` with native `<input>`:

```typescript
<input
  {...register('weight_kg', {
    setValueAs: (v) => {
      const s = String(v ?? "").trim().replace(/,/g, ".");
      const n = Number(s);
      return Number.isFinite(n) && n > 0 ? n : undefined;
    },
  })}
/>
```

### Locale numeric parsing (RU/EN)

**Hard rule:** RU locale must support comma decimal separator (`75,1` → `75.1`).

**Implementation:**

- Use `setValueAs` for quick fixes (P0)
- Use `NumberInput` with `Controller` for proper components (P1)
- **Single source of truth:** Either `setValueAs` OR `NumberInput`, not both

**Verification:**

- Test with `75,1` → should parse to `75.1`
- Test with `75.1` → should parse to `75.1`
- Invalid input → should show error, not `undefined`

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

### Router helper policy (FREE/PRO)

- **Shared helpers MUST live in `app/routers/_helpers.py`**.
- **Do not copy/paste helper logic between routers** (`bmi.py`, `bmi_pro.py`, etc.).
- **Soft paywall hook builder lives only in `app/routers/_helpers.py`** and must not import `core.bmi.*`.
- **Default for `SOFT_PAYWALL_ENABLED`:** FREE `True`, PRO `False` (via `default_enabled` parameter).
- **Guard test enforces:** routers must not define local `_build_soft_paywall_hook`; must import from `_helpers`.

## Git workflow (single-developer safe mode)

This workflow is the default while the project is maintained by a single developer and branch protection blocks force-pushes.
If the repo becomes multi-maintainer again, revisit this policy in a dedicated PR with documented rationale.

**Hard rules:**

- ❌ **Never use `git push --force` or `git push --force-with-lease`** on any branch (including PR branches). Force push is forbidden in this repository.
- ❌ **Never push directly to `main`** — always use feature branches and PRs.
- ❌ **Never merge no-op PRs** (branches identical to main after conflict resolution). Close as duplicate instead.
- ❌ Never rewrite branch history (no rebase of published branches).
- ❌ Never use `git pull` (without rebase) unless you explicitly want a merge-commit (usually not)
- ✅ **Before resolving conflicts: check whether upstream PRs already landed; if branch becomes identical to main, close as duplicate.**
- ✅ **Update PRs by adding new commits only.** If you need to undo something, use `git revert`.
- ✅ **History cleanup happens only at merge time via GitHub "Squash and merge"**, not by rewriting branch history.
- ✅ If CI is red → PR does not exist. Any work except fixing CI is forbidden.

**Dependabot merges:** One-at-a-time; after each merge run `pre-commit run -a` and `pytest -q tests/test_repo_policy_guards.py` locally, then proceed to the next. Use squash + delete-branch. Do not extend dependabot PR scope — fix failures in a separate PR.

**Incident response (if force-push to main occurred):**

If a force-push to `main` happened (even for recovery purposes):

1. **Document immediately:** Create incident note in `docs/incidents/INCIDENT_YYYY-MM-DD_FORCE_PUSH_MAIN.md`
2. **Verify recovery:** Confirm `main` is restored to correct state (`git log origin/main`)
3. **Move changes:** Transfer any work to proper feature branch and open PR
4. **Prevention:** Review process gaps (pre-push hooks, branch checks)

See: `docs/incidents/INCIDENT_2026-01-28_FORCE_PUSH_MAIN.md` for example.

**Required steps (in order):**

```bash
# 1. Fetch latest from remote
git fetch origin

# 2. Make changes
# ... edit files ...

# 3. Verify tests pass
make test-fast
make cov-check

# 4. Push normally (no force push)
git push
```

**If your branch diverged or got messy (required approach):**

```bash
# 1. Fetch latest
git fetch origin

# 2. Check if upstream PRs already landed (avoid duplicate work)
git diff origin/main...HEAD --stat
# If diff is empty or only contains unrelated changes, consider closing PR as duplicate

# 3. Create fresh branch from main
git checkout -b fix/<new-branch> origin/main

# 4. Cherry-pick only the clean commits you want
git cherry-pick <sha1> <sha2> ...

# 5. After cherry-pick, verify branch still has meaningful changes
git diff origin/main...HEAD --stat
# If branch becomes identical to main, close PR as duplicate (no-op merges are forbidden)

# 6. Verify tests pass
make test-fast
make cov-check

# 7. Push new branch
git push -u origin fix/<new-branch>

# 6. Preserve review context when superseding a PR
# - Notify reviewers before closing the old PR (comment: "Superseded by #<new-pr>")
# - In the new PR description: "Supersedes #<old-pr-number>"
# - Copy any unresolved review feedback / check failures into the new PR checklist
```

Close the old PR as superseded and open a new PR from the clean branch.

This avoids force push entirely and keeps history clean without risk of overwriting others' work.

## Import Hygiene Checklist (must-run before PR)

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

## Security: Unfixed Distro CVE Policy

**When a CRITICAL CVE is unfixed upstream in base image distro:**

1. **Document:** Create security note in `docs/security/`
2. **Suppress:** Add temporary suppression rule(s) in `trivy/ignore-policy.rego` with expiry date
3. **Monitor:** Check upstream tracker weekly until fix available
4. **Remove:** When fixed version available, remove suppression and update base image

**Suppression requirements:**

- Must have expiry date (max 90 days)
- Must reference CVE tracker URL
- Must document removal condition
- Must be reviewed in separate security PR (PR-SEC)
- Must include `# Suppression expires: YYYY-MM-DD` in the policy file (enforced by CI)

**Rationale:** We cannot fix system library vulnerabilities. We can only:

- Document unfixed status
- Monitor for upstream fix
- Update base image when fix available

**CVE suppressions must live in a dedicated security PR (runtime config allowed), and must reference a single canonical doc in `docs/security/...`.**

**Trivy suppression implementation (canonical):**

- Prefer `trivy/ignore-policy.rego` (scoped by package + version + context fields where possible).
- `.trivyignore` is for legacy/minimal ignores; do not rely on it for expiry monitoring.
- CI uses `TRIVY_IGNORE_POLICY_PATH` to point to active policy file(s); expiry enforcement runs `scripts/ci/check_trivy_ignore_policy_expiry.py`.
- **Runner version drift policy:** If base image/version varies across CI runners (e.g., `deb12u10` vs `deb12u13`), add **allowlist of observed versions** in suppression rules, not wildcards. Example: use helper rules matching `u10` and `u13` explicitly, not `deb12u*` pattern. Rationale: Prevents accidental suppression of future versions (u14/u15) that may have fixes available.

**Security PR scoping:**

- **One PR per CVE:** Security suppression PRs must be CVE-scoped: one PR per CVE (doc + policy rule) for traceability and auditability.
- **Exception:** A base image bump / distro upgrade PR may address multiple CVEs via upstream fixes (no suppression additions required).

**Example:**

- CVE-2026-0861 (glibc) — unfixed in Debian bookworm
- Suppression expires: 2026-03-01
- Monitor: <https://security-tracker.debian.org/tracker/CVE-2026-0861>
- See: `docs/security/CVE-2026-0861-glibc.md`

---

## CI: GitHub Container Registry (GHCR) Policy

**Required for workflows that pull from GHCR:**

1. **Permissions:** Job must have `packages: read` permission
2. **Login:** Must use `docker login` before `docker pull`
3. **Username:** Use `${{ github.repository_owner }}` (not `github.actor`)
4. **Token:** Use `${{ secrets.GHCR_READ_TOKEN }}` from environment secrets
5. **Package access:** Package must grant repository access in settings

**Verification checklist:**

- [ ] Token has `read:packages` scope
- [ ] Token is in Environment secrets (not Repository secrets)
- [ ] Package settings → Actions access → repository has Read access
- [ ] Workflow uses `github.repository_owner` for login username
- [ ] Workflow has `permissions: packages: read`

**Common errors:**

- `denied: denied` → Check token scope and package permissions
- `authentication required` → Verify token is in environment secrets
- `not found` → Check package name and repository access

**See:** `docs/audit/GHCR_TOKEN_SETUP.md` for detailed setup guide.

---

## Post-Remediation Roadmap (Hard Rule)

**PR-D (Frontend Audit) is forbidden until:**

- ✅ Remediation PR merged (PR #535)
- ✅ PR-A cleanup merged
- ✅ Backend guards green
- ✅ `make verify` passes

**Rationale:** Frontend audit requires stable backend contracts. Premature frontend changes create technical debt and alignment issues.

**Roadmap:**

- **PR-A:** Post-remediation cleanup (dead code, orphan tests)
- **PR-B:** Product contract / soft paywall audit (docs only)
- **PR-C:** Legal / compliance pack (wellness positioning)
- **PR-D:** Frontend audit (only after backend stable)

**See:** `docs/audit/ROADMAP_POST_REMEDIATION.md` for detailed audit questions and DoD.

---

## PR Scope Policy (Hard Rule)

This section complements the earlier **"Docs-only PR Rule"** and clarifies the **single allowed exception**: a security PR may include Trivy ignore config (`.trivyignore` and/or `trivy/ignore-policy.rego`) together with related security docs.

**Runtime config changes (`.trivyignore`, `trivy/ignore-policy.rego`, workflows, infra configs) must NEVER be mixed with docs-only PRs.**

**Rules:**

- **Docs-only PR:** Only `*.md` files, `README.md`, `AGENTS.md`, `.github/*.md` (templates)
- **Runtime config PR:** `.trivyignore`, `.github/workflows/*.yml`, `Dockerfile`, `Makefile`, `requirements*`, etc.
- **Tests PR:** `tests/*.py`, test-related configs
- **Mixed PR:** Only when explicitly justified (e.g., security config + security docs)

**Rationale:** Mixing runtime config with docs-only PRs violates PR scope guard policy and makes reviews/CI tracking unreliable.

**Examples:**

- ✅ **OK:** Security config PR with `trivy/ignore-policy.rego` + `docs/security/*.md` (related security docs)
- ❌ **Forbidden:** Docs-only PR with `trivy/ignore-policy.rego` (runtime config)
- ❌ **Forbidden:** Guard scanner PR with `.trivyignore` (different scope)

**Editor troubleshooting docs** (e.g., `CODERABBIT_CURSOR_FIX.md`) should be in separate docs-only PR to avoid scope creep.

---

## Backlog Ledger Policy (Canonical)

**Canonical backlog lives in `docs/roadmap/BACKLOG_LEDGER.md`.**

**Rules (non-negotiable):**

1. Any postponed / deferred work MUST be recorded in the ledger immediately.
2. Each ledger item MUST include:
   - Owner
   - Priority (P0/P1/P2)
   - Target PR (number or placeholder)
   - Reason for deferral
   - Links to relevant audit/docs
   - DoD (acceptance criteria)
3. Backlog entries must be English-first; non-English text MUST include an English summary on the same line.
   Automated review bots may block PRs that violate English-first ledger entries.
4. Every PR description MUST include a "Deferred / Follow-ups" section with links to ledger items (and GitHub issues if present).
5. Closing a ledger item requires:
   - PR merged OR explicit "won't do" decision recorded (with reason).

**Agent enforcement:**

- Agents must refuse to mark work as "done" if deferred items were mentioned but not recorded in the ledger.
- If it is not in the ledger — it does not exist.

**Rationale:** Prevents "deferred → forgotten → resurfaces later" anti-pattern. Single source of truth for follow-up work.

---

## iOS CI Policy (Hard Rule)

**iOS rules and CI policy — canonical in `ios/AGENTS.md` (Cursor-first, Xcode pinning, membershipExceptions, guard tests).**

**iOS PRs must run xcodebuild unit tests in GitHub Actions (macOS runner).**

**Rules:**

- Swift syntax-only checks (pre-commit hooks) are insufficient for enforcement.
- All iOS unit tests (including guard tests like `ThinClientGuardsTests`) must run in CI.
- CI job runs on `macos-15` runner with Xcode 16.x (matches project format).
- Tests must pass before PR merge.

**Rationale:** Guard tests and architectural invariants are only enforced if tests actually run in CI. Syntax checks do not execute test code.

**iOS CI job gating (paths-filter):**

- `ios-tests` job is gated via `changes` job using `dorny/paths-filter`.
- iOS tests run **only** when PR touches: `ios/**`, `.github/workflows/**`, or `.github/actions/**`.
- Docs-only PRs (e.g., `docs/**/*.md`, `README*.md`, `AGENTS.md`, `.github/*.md`) **do not** run macOS iOS jobs.
- **Rationale:** Reduces CI noise, prevents flaky iOS tests on unrelated PRs, speeds up docs-only PR cycle.

**iOS CI destination policy (canonical):**

- **CI destination MUST be UDID-only:** `platform=iOS Simulator,id=<UDID>`
- **`OS=latest` is forbidden in CI:** Job fails if destination contains `latest` (anti-nondeterminism guard). CI must use explicit UDID-based destinations only.
- **Rationale:** UDID-only kills `latest` ambiguity, name mismatch, and OS version format issues on multi-runtime runners.
- **Local runs (developer convenience):** May use friendly device name (e.g., `iPhone 16e`) or select latest available iOS runtime for local testing, but CI is strictly UDID-only.
- **Xcode version pinning (hard rule):** CI must pin Xcode major/minor version compatible with selected simulator runtimes using deterministic priority list (e.g., prefer Xcode 16.4 → 16.3 → 16.2). Avoid mixing Xcode 16.2 (expects iOS 18.2 SDK) with iOS 18.5/18.6 runtimes → use Xcode 16.4/16.3 instead. Xcode version mismatch causes "iOS X.Y is not installed" errors and makes simulators ineligible for `xcodebuild -showdestinations`.
- **"Latest" policy clarification:**
  - ❌ **Forbidden:** `OS=latest` in CI destination strings
  - ✅ **Allowed:** "Latest Xcode installed" selection via deterministic priority list (pin/priority), not "whatever is newest"
  - ✅ **Allowed (local only):** "Latest iOS runtime available" for developer convenience in local runs, but CI must use UDID + pinned Xcode
- **Hard rule:** Any CI flake related to destination/runtime must be resolved via UDID-only approach. No return to `OS=latest` or `name+OS` format.
- **Boot requirement:** If `xcodebuild test` cannot match UDID destination, boot + bootstatus is the first remediation step; keep UDID-only strategy. Some runners require simulator to be booted before `xcodebuild` can resolve destination by UDID.

**iOS Xcode project configuration policy (hard rule):**

- **Info*.plist must have NO Target Membership and must never be in Copy Bundle Resources:** Info.plist files (`Info.plist`, `Info-Debug.plist`, `Info-Release.plist`) must be configured only via `INFOPLIST_FILE` in Build Settings. They must not have Target Membership and must never be added to "Copy Bundle Resources" build phase.
- **Rationale:** Adding Info.plist to Copy Bundle Resources or enabling Target Membership causes Xcode build/test failures and unpredictable behavior. Info.plist is processed automatically by Xcode via `INFOPLIST_FILE` setting; copying it as a resource or enabling target membership creates conflicts.
- **Xcode 15+ File System Synchronized Build Files:** If using Xcode 15+ with File System Synchronized Build Files enabled, add all `Info*.plist` files to `PBXFileSystemSynchronizedBuildFileExceptionSet.membershipExceptions` in `project.pbxproj` to prevent automatic addition to Copy Bundle Resources. Example: `Info.plist`, `Info-Debug.plist`, `Info-Release.plist` must all be in `membershipExceptions`.
- **Verification:**
  - **Target Membership:** In Xcode, select each `Info*.plist` file → File Inspector → Target Membership → ensure NO targets are checked.
  - **Build Phases:** Target → Build Phases → Copy Bundle Resources → ensure no `Info*.plist` files are listed. If found, remove them (file remains on disk, only remove from build phase).
  - **Command line:** Run `xcodebuild -project ... -scheme ... -configuration Debug build 2>&1 | grep -i "copy.*bundle.*resources.*info"` → should return no warnings.

**GitHub Actions shell script policy:**

- **ShellCheck compliance required:** All shell scripts in `.github/workflows/*.yml` must pass `actionlint` (which enforces ShellCheck rules).
- **Forbidden patterns:** `ls | grep` (SC2010) — use glob + for loop or `find` instead.
- **Rationale:** Prevents shell script bugs and ensures CI workflow reliability.

**iOS CI debugging (finding real errors in logs):**

- **SwiftPM compilation noise:** SPM packages (e.g., Lottie) produce verbose compilation logs. This is normal and not an error.
- **Finding real errors:** In GitHub Actions logs, search for:
  - `error:` (first occurrence is usually root cause)
  - `Swift compiler error`
  - `fatal error`
  - `Command SwiftCompile failed with a nonzero exit code`
  - `Ld ... failed`
  - `Undefined symbols`
- **Quick filter (if raw log available):**
  ```bash
  grep -nE "error:|fatal error|nonzero exit|Undefined symbols|Ld .* failed" build.log | head -n 50
  ```
- **In GitHub Actions UI:** Use Ctrl+F to search for `error:` — first match is usually root cause.
- **Always search for root cause before "last message":** Final message (e.g., "Exited with code 65") is often just the symptom. Real error is usually 2000+ lines above.
- **Classify error types immediately:**
  - `SwiftCompile failed` → Swift compilation error (check source code, imports, types)
  - `Ld failed / Undefined symbols` → Linking error (frameworks, architectures, missing symbols)
  - `PackageResolution` / `resolved to…` → SwiftPM dependency resolution issue
  - `The bundle couldn't be loaded` → Test target/host app/signing/Build settings issue
- **Clean run rule:** If error is strange and looks like cache/incremental build issue: run without cache (or clear `.derivedData`) as diagnostic step #1.
- **SwiftPM caching:** CI caches `.derivedData/SourcePackages` only (not Build artifacts) to speed up SPM resolution. Cache key includes `runner.os`, Xcode version, and `Package.resolved` hash for determinism.
- **Build cache policy:** `.derivedData/Build` is NOT cached (contains absolute paths, runner-specific artifacts, can cause flaky failures). If CI becomes unstable, first check: disable Build cache (already disabled).
- **xcodebuild flags:** CI uses `-clonedSourcePackagesDirPath` and `-derivedDataPath` for deterministic package resolution. Both `build-for-testing` and `test-without-building` must use identical paths.

**iOS Networking policy (hard rule):**

- **No shared mutable JSONEncoder/Decoder:** `APIClient` and other networking classes must not store `JSONEncoder`/`JSONDecoder` as instance properties (mutable state + Sendable violation). Use factory closures: `makeEncoder: () -> JSONEncoder` / `makeDecoder: () -> JSONDecoder`.
- **Default JSON key strategy:** All API requests/responses use `.convertToSnakeCase` by default. Any exceptions (camelCase or custom keys) must be handled via explicit `CodingKeys` in models, not by changing encoder strategy globally.
- **Error mapping policy:** Network/transport failures MUST be `APIError.transport` (never `statusCode: 0`); unexpected non-`APIError` failures MUST map to `APIError.unknown` (not `.transport`).
- **Rationale:** Ensures Sendable compliance, deterministic serialization, and contract consistency with backend (backend expects snake_case).

**Git hooks portability (hard rule):**

- **NUL-safe pipelines required:** All git hooks that process file lists must use NUL-safe pipelines:
  - `git diff --name-only -z` (not `--name-only` without `-z`)
  - Portable NUL filtering via `perl` (not GNU-only `grep -z` which fails on macOS BSD grep)
  - `xargs -0` (not `xargs` without `-0`)
- **Rationale:** Prevents breakage on file paths with spaces, special characters, or newlines. Works correctly on macOS (BSD grep) and Linux (GNU grep).
- **Never silence hook failures:** Do not use `|| true` to mask hook failures unless explicitly justified. Prefer fail-fast behavior to catch issues early.
- **Merge conflict detection:** Conflict markers MUST be anchored to line start: `^(<<<<<<<|=======|>>>>>>>)` to avoid false positives from banner separators (e.g., `# ======` in code).

**CI strictness (hard rule):**

- **Forbidden:** Masking errors with shell hacks like `|| true` (or `; true`) inside `run:` steps under `set -euo pipefail`. Errors must surface to fail the job.
- **Allowed:** `continue-on-error: true` **only** as metadata at job/step level in YAML, when the step is genuinely optional (e.g., non-blocking notifications, optional reports).
- **Note:** `continue-on-error: true` is allowed only at YAML level (job/step), **not** inside shell commands.
- **Rationale:** Prevents "false green" CI runs where real issues are hidden. Shell-level masking (`|| true`) breaks `set -euo pipefail` safety; YAML-level `continue-on-error` is explicit and auditable.

---

## Merge Conflict Safety (Hard Rule)

**❌ AGENT MUST NEVER push or open a PR if the working tree contains:**
- Unresolved merge conflicts
- Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
- Partially resolved merges
- Files in state: `both modified`, `unmerged`, `needs merge`

**Mandatory checks before any push:**
1. `git status` MUST show a clean working tree
2. No files in state: `both modified`, `unmerged`, `needs merge`
3. `git diff` MUST NOT contain conflict markers
4. `git ls-files -u` MUST return empty (no unmerged paths)

**Violation handling:**
- If a merge conflict is detected, the agent MUST STOP.
- The agent MUST report the conflict and request manual resolution.
- No auto-resolution, no guessing, no push.
- The agent MUST assume that unresolved merge conflicts are a **STOP condition**, not a warning. No recovery attempts are allowed.

**Enforcement:**
- Pre-push hook blocks pushes with conflicts (technical guard)
- CI guard fails PR if conflict markers detected (last line of defense)
- Code review: grep for conflict markers before merge

**This rule is non-negotiable.**

---

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

7) **Architecture docs must be evidence-driven**
   - Any architecture doc that claims a “truth” (entrypoint, compat shim, schema-only mode, guard enforcement) MUST cite evidence as `file:line` pointers.
   - Any temporary seam (e.g. schema-only OpenAPI, sys.modules compat mapping, whitelists) MUST have:
     - an ADR with explicit **exit criteria**, and
     - a Backlog Ledger item with DoD / blockers.

### Non-goals

- AGENTS files are NOT changelogs.
- AGENTS files are NOT PR notes.
- AGENTS files must remain stable and auditable.
