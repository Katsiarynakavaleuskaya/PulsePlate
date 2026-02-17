---
name: pulseplate-backend-endpoints
description: Add backend endpoints with required schemas, guards, rate limits, quota checks, and deterministic tests.
---

# PulsePlate Backend Endpoints

## When to use

- Creating or modifying FastAPI endpoints in `app/routers`.
- Adding expensive endpoints (LLM/export) requiring rate-limit and quota controls.
- Implementing endpoint changes that need deterministic test coverage.

## Inputs required

- Endpoint path/method.
- Tier requirements (`FREE/PRO/VIP`).
- Rate limit class (`insight` or `exports` if applicable).
- Expected request/response schema updates.

## Procedure (commands)

1. Implement contract-first changes:
   - Add/update schema in `app/schemas/`.
   - Add/update endpoint in `app/routers/`.
   - Keep business logic in `core/`.
2. Apply security/rate-limit rules where applicable:
   - `@limit_if_available(RATE_LIMIT_INSIGHT)` for LLM endpoints.
   - `@limit_if_available(RATE_LIMIT_EXPORTS)` for export endpoints.
   - Ensure handler accepts `request: Request`.
3. Add deterministic tests (including 429 and quota paths as needed):

   ```bash
   pytest -q tests/test_rate_limit_llm_and_exports_api.py
   pytest -q tests/test_repo_policy_guards.py
   ```

4. Run backend verification:

   ```bash
   make verify
   ```

## Output format

- `Endpoint contract`: method/path + request/response schema.
- `Policy compliance`: tier/rate-limit/quota checks applied.
- `Tests`: added/updated test files and results.
- `Evidence`: failing/passing command excerpts and `file:line:error` where relevant.

## Guardrails

- Do not add business logic in routers when core layer is required.
- Do not add expensive endpoints without deterministic 429 tests.
- Do not claim merge readiness without local gate evidence.

## SoT links

- `app/AGENTS.md`
- `core/AGENTS.md`
- `AGENTS.md`
- `app/security/rate_limit.py`
- `tests/test_rate_limit_llm_and_exports_api.py`
- `tests/test_repo_policy_guards.py`
