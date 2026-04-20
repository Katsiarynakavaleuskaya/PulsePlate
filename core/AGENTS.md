# Agent instructions (scope: core/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `core/` and below.
- Key directories: `core/bayes/`, `core/food_apis/`, `core/rag/`, `core/*_analyzer.py`,
  `core/db.py`, `core/models.py`.

## Commands (run from repo root)
- Install: `make venv`
- Test: `make test`, `make test-fast`
- Coverage: `make cov`, `make cov-check`
- Lint/format: `make lint`, `make fmt`, `make fmt-check`

## Conventions
- Keep domain logic pure and reusable; avoid FastAPI imports in `core/`.
- Prefer deterministic functions and explicit inputs/outputs.
- Use timezone-aware UTC (`datetime.now(timezone.utc)`) for new timestamps.
- Keep typing explicit and update tests for new branches.

## Type hints policy (core)

- Type hints in `core/` describe the domain, not test behavior
- Never weaken types to satisfy tests or mocks
- Prefer:
  - precise return types
  - total functions (explicit error handling)
- `Optional[T]` only if `None` is a valid business outcome
- Never introduce `Any` into core logic

If a test fails due to typing:
→ the test setup or import order is wrong, not the core type hints.

## Single source of truth (core)

- Business rules live in `core/`.
- If a function exists in `legacy_app.py` and is used by multiple places:
  - extract it into `core/` and keep a thin wrapper in legacy/app.
- Never duplicate rules in both `core/` and `app/` (tests must enforce this).

- **Single SQLAlchemy Base rule**:
  All ORM models MUST import `Base` from `core.db`.
  Never create a local `declarative_base()` in models or analyzers.
- **No import-time side effects**:
  Do not evaluate feature flags, DB URLs, or environment-dependent logic
  at import time in `core/`.
- **No reload / reconfigure patterns**:
  Do NOT use `importlib.reload`, `Base.metadata.clear()`,
  or `SessionLocal.configure()` in `core/`.
  DB lifecycle is controlled by test fixtures and application startup.

## FitChef domain invariants

- FitChef domain code must consume canonical backend outputs; it must not recreate nutrition math, entitlement logic, or planner truth in `core/fitchef/*`.
- LLM-generated text is not a domain oracle. Domain state, actions, and limits must be decided before any provider call.
- FitChef fallback/templates are mandatory and deterministic so bounded guidance still works when LLM execution is disabled or unavailable.
- Core FitChef interfaces should prefer typed structured payloads over free-form strings whenever the result drives UI actions or navigation.

## Feature map
- See `app/AGENTS.md` for the full backend feature map covering `core/` + `app/`.

## Dual Base & DB lifecycle (critical)

- `core.db.Base` is the single source of truth for ORM metadata.
- All models and analyzers must reference the SAME `Base` object.
- Import order matters: environment variables (DATABASE_URL, TESTING)
  must be set before importing `core.db`.
- Test failures mentioning "multiple Base", "mapper already defined",
  or inconsistent metadata usually indicate import-order violations.

### Quick check
```bash
git grep -n "declarative_base" core/
git grep -n "importlib.reload|metadata.clear|SessionLocal.configure" core/
```
