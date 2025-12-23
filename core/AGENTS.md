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

## Feature map
- See `app/AGENTS.md` for the full backend feature map covering `core/` + `app/`.
