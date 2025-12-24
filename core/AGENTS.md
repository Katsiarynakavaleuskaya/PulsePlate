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
