# Contributing Guidelines

This repo uses a simple branch model designed to keep `main` always green.

## Branching

- Long‑lived branch: `main` only.
- Create short‑lived branches for work:
  - `feature/<topic>` for new features
  - `fix/<issue>` for bug fixes
  - `chore/<task>` for maintenance
- Avoid direct pushes to `main`. Open a PR.

## Git Workflow: Merge vs Rebase

**⚠️ Important:** Always use **merge** instead of **rebase** when syncing with remote.

### ✅ Correct (use merge)

```bash
# Syncing with remote
git pull origin feat/my-feature  # uses merge by default

# Updating feature branch with main
git merge origin/main
```

### ❌ Incorrect (avoid rebase)

```bash
# ❌ DON'T do this (rewrites history)
git pull --rebase
git rebase origin/main
```

**Why?** Rebase rewrites commit history, creates new SHA hashes, and causes conflicts for team members. Use merge to preserve history and avoid force-push.

**Exception:** Interactive rebase (`git rebase -i`) is OK for cleaning up your LOCAL commits BEFORE pushing, but only if you're the sole contributor to the branch.

See [GIT_PUSH_FIX_SUMMARY.md](GIT_PUSH_FIX_SUMMARY.md) for detailed explanation.

## Pull Requests

- Keep PRs small and focused. Prefer squash merge.
- Ensure CI is green:
  - Tests pass on Python 3.12 and 3.13
  - Coverage ≥ 97% (repo currently ~99%)
- Run locally before pushing:

```bash
pytest -q --maxfail=1 --disable-warnings \
  --cov=. --cov-report=term-missing --cov-fail-under=97
```

### PR Automation Workflow

The repository uses an automated PR workflow (`.github/workflows/pr-automation.yml`) that:

1. **Waits for CodeRabbit review** (configurable timeout, default: 15 minutes)
2. **Applies auto-fixes** (ESLint, Ruff format/check)
3. **Runs full test suite** with coverage validation
4. **Auto-commits changes** (for non-fork PRs only)

**Configuring CodeRabbit timeout:**

The workflow waits for CodeRabbit review before proceeding. By default, it waits up to **15 minutes** (reduced from 30 to speed up CI). You can customize this timeout:

- **Via environment variable:** Set `CODE_RABBIT_TIMEOUT_MIN` in your repository settings
- **Via workflow dispatch:** Manually trigger the workflow with a custom timeout value
- **Example values:** 10 (faster), 15 (default), 20 or 30 (for complex PRs)

The timeout is computed as: `max_iterations = (timeout_minutes × 60) / 30s_sleep_interval`

## Auto‑delete merged branches

- Merged PR branches are deleted automatically.
- A workflow (`.github/workflows/auto-delete-branches.yml`) removes the
  head branch when a PR is merged in this repository.

## Coding

- Follow existing style. Keep changes minimal and scoped.
- Prefer tests that isolate external services by mocking.
- Don't lower coverage thresholds; add tests instead.
- **Code formatting**: We use **Ruff** for both linting and formatting (replaces Black + flake8).

  ```bash
  # Format code
  ruff format .

  # Lint and auto-fix
  ruff check --fix .

  # Or use Makefile
  make fmt
  ```

  See [docs/FORMATTING_STRATEGY.md](docs/FORMATTING_STRATEGY.md) for details.
- **Premium endpoints policy / Политика премиальных эндпойнтов**:
  - Every new premium/admin FastAPI route **must** include the shared API key guard (e.g. `Depends(_get_api_key_dynamic)` or `require_premium_key`).
  - Перед добавлением нового платного эндпойнта убедитесь, что он подключает dependency для проверки ключа и что есть тест, подтверждающий 403/401 без ключа.

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
