# Contributing Guidelines

This repo uses a simple branch model designed to keep `main` always green.

## Branching

- Long‑lived branch: `main` only.
- Create short‑lived branches for work:
  - `feature/<topic>` for new features
  - `fix/<issue>` for bug fixes
  - `chore/<task>` for maintenance
- Avoid direct pushes to `main`. Open a PR.

## Pull Requests

- Keep PRs small and focused. Prefer squash merge.
- Ensure CI is green:
  - Tests pass on Python 3.12 and 3.13
  - Coverage ≥ 96% (repo currently ~99%)
- Run locally before pushing:

```bash
pytest -q --maxfail=1 --disable-warnings \
  --cov=. --cov-report=term-missing --cov-fail-under=96
```

## Auto‑delete merged branches

- Merged PR branches are deleted automatically.
- A workflow (`.github/workflows/auto-delete-branches.yml`) removes the
  head branch when a PR is merged in this repository.

## Coding

- Follow existing style. Keep changes minimal and scoped.
- Prefer tests that isolate external services by mocking.
- Don’t lower coverage thresholds; add tests instead.

## Commit Messages

- Use conventional style where possible:
  - `feat: ...`, `fix: ...`, `chore: ...`, `docs: ...`, `tests: ...`
- One logical change per commit.

## Security & Quality

- Non‑blocking scanners run in CI (Bandit, CodeQL).
- Address warnings when practical; don’t block urgent fixes.

## Getting Help

- Open a Draft PR early for feedback.
- Use the issue tracker for bugs and small enhancements.

