# API Canonical Map

**Status:** Canonical baseline (PR-508)
**Source of truth:** OpenAPI generated from `app.main.app` (see `scripts/generate_openapi.py`)

## Rules

1. **Canonical contracts live in backend OpenAPI**.
2. Frontend + iOS **generate types/models from OpenAPI** (no manual duplication).
3. Legacy `/api/v1/premium/*` endpoints are **compatibility aliases** (deprecated).

## Canonical vs Compat Endpoints (as of PR-508)

| Feature | Canonical endpoint | Method | Compat (legacy) endpoint | Method | Notes |
|---|---|---:|---|---:|---|
| Targets | (missing) `/api/v1/pro/nutrition/targets` | POST | `/api/v1/premium/targets` | POST | Canonical endpoint does not exist yet. Implement in PR-509. |
| Daily / Plate | `/api/v1/pro/nutrition/daily` | GET | `/api/v1/premium/plate` | POST | Compat differs by method. Long-term: FE/iOS move to canonical GET. |
| Weekly Plan | `/api/v1/pro/meal/weekly` | POST | `/api/v1/premium/plan/week` | POST | Compat delegates to canonical (policy). |
| BMR | `/api/v1/premium/bmr` | POST | (same) | POST | BMR endpoint is stable; no migration needed. |

## Non-goals for PR-508

- Do not add new product logic or new endpoints.
- Do not change business rules.
- Do not refactor legacy entrypoints (`app:app` -> `app.main:app`) in this PR.

## Follow-up PRs (vertical slices)

- **PR-509:** Implement `/api/v1/pro/nutrition/targets` + compat alias behavior and contract tests.
- **PR-510:** Align Plate/Daily contracts and FE usage; keep compat.
- **PR-511:** Type WeekPlan response models (if needed) + contract tests + FE adjustments.
