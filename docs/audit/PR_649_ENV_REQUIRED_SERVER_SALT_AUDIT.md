## Audit Meta

- **PR**: PR-649
- **Branch**: `chore/pr-649-env-required-server-salt`
- **Scope**: local/dev experience only (`.env.example`, root `docker-compose.yaml`, ledger + 1 agent rule)
- **Non-goals**: production secrets management, runtime behavior changes, feature changes

---

## Audit Questions (concise)

### Q1) Where do we start locally?

- **Primary**: root `docker-compose.yaml` (`docker compose up`)
- **Also present**: `deploy/docker-compose.*.yaml` (staging/prod, env_file points to host secrets; out of scope)

### Q2) Is `SERVER_SALT` already set somewhere?

- **CI smoke-start** sets dummy `SERVER_SALT` (to satisfy fail-fast startup) in workflow `docker run` steps.
- **Root local compose** did not pass `SERVER_SALT` prior to PR-649 (gap fixed here).

### Q3) Naming conflicts?

- No conflicts: `SERVER_SALT` is already canonical (fail-fast required), and `VIP_LLM_INSIGHT_REQUESTS_PER_MONTH`
  is the canonical quota limit env var.

---

## Evidence (BEFORE → AFTER)

- **BEFORE**: `.env.example` did not mention `SERVER_SALT` / `VIP_LLM_INSIGHT_REQUESTS_PER_MONTH` → confusing local start.
- **AFTER**: `.env.example` includes both with guidance; root `docker-compose.yaml` fails fast if `SERVER_SALT` is missing.

## Local smoke (developer experience)

- `docker compose config` fails fast when `SERVER_SALT` is missing, and succeeds when provided.
- Note: local host port conflicts (e.g., 8000/8001 already in use) can prevent `docker compose up` from binding.
  In that case, `docker compose run` can be used for a portless smoke:
  `SERVER_SALT=dev_secret docker compose run --rm --no-deps pulseplate python -c "from app.security.llm_monthly_quota import require_server_salt; require_server_salt(); print('OK')"`
