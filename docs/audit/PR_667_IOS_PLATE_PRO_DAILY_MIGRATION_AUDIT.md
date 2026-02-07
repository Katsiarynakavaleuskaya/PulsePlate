# PR-667 — iOS Plate → canonical /api/v1/pro/nutrition/daily

## Scope
- iOS client only
- Plate screen
- PRO daily nutrition fetch

Out of scope:
- Backend
- OpenAPI
- BACKLOG_LEDGER
- AGENTS.md

## Problem
iOS Plate previously used legacy endpoint `/api/nutrition/{date}` as
source-of-truth. This endpoint is deprecated, hidden from OpenAPI,
and forbidden as SoT by canonical API policy.

## Canonical Decision
- iOS Plate MUST use:
  GET /api/v1/pro/nutrition/daily
- Auth via `X-API-Key` (ProKeyProvider)
- Profile query params provided by a single provider

## Evidence (file:line)

### Legacy (before)
- `ios/PulsePlate/Models/NutritionData.swift`
  - Built path: `api/nutrition/{date}` (legacy SoT)

### Canonical backend
- `app/routers/pro.py`
  - `@router.get("/nutrition/daily", ...)`
  - Protected by `Depends(require_pro_tier)`
  - Query params: `date, sex, age, height_cm, weight_kg, activity, goal, lang`

### iOS changes
- `Services/ProDailyNutritionService.swift`
  - Deterministic GET request builder
  - Canonical path `/api/v1/pro/nutrition/daily`
  - Adds `X-API-Key` header
- `Services/ProfileProvider.swift`
  - Single source of truth for profile + language
- `Models/NutritionData.swift`
  - Validates presence of PRO key and profile
  - Delegates to canonical service
- `Views/PlateView.swift`
  - Explicit `PlateLoadIssue` UX states
- `Views/ProfileView.swift`
  - Minimal PRO profile input form

### Tests
- `PulsePlateTests/Services/ProDailyNutritionServiceTests.swift`
  - Deterministic path assertion
  - `X-API-Key` header assertion

## UX States
- Missing PRO key
- Missing profile
- 401 / 403 (authorization)
- 422 (validation, human-readable)
- Transport error
- Decoding error
- Unknown error

## Security Notes
- PRO API key accessed only via `ProKeyProvider`
  - DEBUG: env
  - Release: Keychain
- Full API key is never logged
- Query params are not logged in production

## Verification
- `pre-commit run --all-files` — verified locally
- `make ios-test` — verified locally

## Conclusion
PR-667 migrates iOS Plate to the canonical PRO daily nutrition endpoint
in full compliance with API, security, and UX policies.
No backend or schema changes.
Ready to merge.
