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
- Ensure CI is green and follow the canonical local gates in `AGENTS.md` and
  `RUNBOOK_AGENT.md`. Do not duplicate Python-version or coverage thresholds
  here; repo policy owns those values.
- Run locally before pushing:

```bash
# Required before every push
pre-commit run --all-files

# Standard verification bundle
make verify

# Operator-approved machine-heavy exception only: run and document narrow gates
make validate-changed

# Docker tests (if Docker files changed)
make docker-build
docker run -d --rm --name test -p 8000:8000 pulseplate:latest
sleep 2  # Allow container to start
curl -f http://localhost:8000/health || (docker stop test; exit 1)  # Verify health check
```

## Local Development Setup

### Dev Container (recommended)

The recommended path for backend/web/docs/orchestration work keeps repository
bootstrap manual and forwards only the private package proxy settings needed for
dependency installation. Do not load the full project `.env` into the
devcontainer.

```bash
export PULSEPLATE_PYTHON_INDEX_URL=https://packages.example.internal/simple
# Optional, only if the approved proxy requires pip trusted-host behavior:
export PULSEPLATE_PYTHON_TRUSTED_HOST=

# VS Code: Cmd/Ctrl+Shift+P -> "Dev Containers: Reopen in Container"
# CLI: make dc-up && make dc-shell
# After reviewing/trusting the workspace, run bootstrap manually inside the container:
make devcontainer-bootstrap
[ -f .env ] || cp .env.example .env
# Fill required local-only values such as SERVER_SALT before starting the app.
make dev
```

Host Docker daemon access is intentionally not enabled by default. If a task
requires Docker from inside the devcontainer, use a separate reviewed local
override after the workspace is trusted rather than committing socket access to
the default configuration.

### Host .venv compatibility path

```bash
make venv
source .venv/bin/activate
make dev
```

The devcontainer remains the recommended backend/web/docs/orchestration path.
Host `.venv` bootstrap is supported only when the approved proxy provides a
compatible binary wheel for the host platform. In the bounded 2026-08-04
`cryptography==50.0.0` snapshot, the proxy provided macOS arm64 wheels but no
macOS `x86_64` or `universal2` wheel. Apple Silicon exact-50 bootstrap was
validated; Intel macOS backend bootstrap must use the devcontainer at this
floor. The installer remains binary-only, so source-build fallback is not
supported. This is a dated artifact snapshot, not a permanent compatibility
claim. iOS/Xcode development stays host-native on macOS.

Generic developer targets (`make test`, `make lint`, `make typecheck`, `make cov`,
`make openapi`, etc.) use `DEV_PYTHON`, which auto-detects `.venv/bin/python` or
falls back to `python3` inside containers.  No manual activation needed.

## Network Access in Tests (CI Guard)

To keep CI deterministic (no flaky 429/timeouts from real external services), CI forbids outbound HTTP(S)
from tests (allowed: `localhost`, `127.0.0.1`, `::1`, `testserver`).

- Reproduce locally: `BLOCK_TEST_NETWORK=true pytest ...`
- Temporary CI escape hatch: `ALLOW_TEST_NETWORK=true` (use sparingly; prefer mocks)
- Allow additional internal hostnames (e.g., docker-compose): `TEST_NETWORK_ALLOWED_HOSTS=service1,service2`

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
