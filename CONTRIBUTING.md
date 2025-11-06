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
  - Tests pass on Python 3.13.5
  - Coverage ≥ 96% (repo currently ~99%)
- Run locally before pushing:

```bash
# Standard tests
pytest -q --maxfail=1 --disable-warnings \
  --cov=. --cov-report=term-missing --cov-fail-under=97

# Docker tests (if Docker files changed)
make docker-build
docker run -d --rm --name test -p 8000:8000 pulseplate:latest
sleep 2  # Allow container to start
curl -f http://localhost:8000/health || (docker stop test; exit 1)  # Verify health check
```

## Auto‑delete merged branches

- Merged PR branches are deleted automatically.
- A workflow (`.github/workflows/auto-delete-branches.yml`) removes the
  head branch when a PR is merged in this repository.

## Coding

- Follow existing style. Keep changes minimal and scoped.
- Prefer tests that isolate external services by mocking.
- Don’t lower coverage thresholds; add tests instead.
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

### Dependency Security Policy (Safety)

- Policy file: `safety-policy.toml` at the repository root. It defines allow‑lists/ignores (currently none) and ensures a single source of truth for Safety configuration.
- Severity threshold: builds and PRs are blocked on findings of severity **high** or **critical**.
- CI enforcement: the Security workflow runs Safety against `requirements.txt` using the shared policy file and fails the job with a non‑zero exit code when high/critical vulnerabilities are present. This blocks merges.
- Local usage:
  - English / EN:
    ```bash
    pip install safety==2.3.5
    safety check --policy-file safety-policy.toml \
      --severity high,critical \
      --full-report -r requirements.txt
    ```
  - Русский / RU:
    ```bash
    pip install safety==2.3.5
    safety check --policy-file safety-policy.toml \
      --severity high,critical \
      --full-report -r requirements.txt
    ```
  - Notes / Примечания:
    - The repo policy currently has `ignore = []` (no ignored findings). Update via PR if a temporary waiver is justified.
    - Keep CI and local checks aligned by always using the same `safety-policy.toml` and severity filter.

## Getting Help

- Open a Draft PR early for feedback.
- Use the issue tracker for bugs and small enhancements.
