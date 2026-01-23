# PR-XXX: Thin HTTP Adapter for iOS (Transport Layer)

## Summary

Implements thin HTTP transport layer for iOS client, aligned with backend contracts. Adds `HTTPClient`/`APIClient` for error mapping and `BMIService` as thin wrapper. DTOs match backend OpenAPI schemas exactly.

**Scope:** Transport layer only (no UI migration in this PR).

**DoD Evidence:** See `docs/PR_XXX_DOD_CHECKLIST.md`
**Review Checklist:** See `docs/PR_XXX_REVIEW_CHECKLIST.md`

---

## Contract Freeze

**Effective date:** 2026-01-22

**Frozen contracts:**

- **Canonical endpoint:** `/api/v1/bmi/calculate`
- **Error formats:**
  - `422`: `{"detail": [{"type": "...", "loc": [...], "msg": "...", "input": ...}]}` (plain English)
  - `400/500/501`: `{"detail": "localized text"}` (via backend `t(lang, key)`)
- **Request/Response schemas:** `app/schemas/bmi.py` (backend source of truth)
- **i18n approach:** Mixed model (text fields vs i18n keys — see audit doc)

**Enforcement:**

- Client implementation matches frozen contracts exactly
- Any deviation requires explicit backend PR to change contract first
- See: `docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md`

---

## Changes

### Core Transport Layer

**Files:**

- `ios/PulsePlate/Networking/HTTPClient.swift` — low-level HTTP client with error mapping
- `ios/PulsePlate/Networking/APIClient.swift` — request builder (URL, headers, JSON encoding)
- `ios/PulsePlate/Networking/APIError.swift` — unified error model (422 vs 400/500)
- `ios/PulsePlate/Networking/ErrorsDTO.swift` — error response DTOs

**Responsibilities:**

- Transport only (no business logic)
- Error envelope mapping (422 `detail[]` vs 400/500 `detail: str`)
- JSON encode/decode with `snake_case` conversion

### BMI Thin Adapter

**Files:**

- `ios/PulsePlate/Services/BMIService.swift` — thin wrapper over `APIClient` (lines 1-46)
- `ios/PulsePlate/Models/BMI/BMICalculateRequestDTO.swift` — request DTO
- `ios/PulsePlate/Models/BMI/BMICalculateResponseDTO.swift` — response DTO
- `ios/PulsePlate/Models/BMI/WaistRiskDTO.swift` — waist risk DTO
- `ios/PulsePlate/Models/BMI/BMIScaleV1DTO.swift` — visualization DTO
- `ios/PulsePlate/Models/BMI/BMIInterpretationV1DTO.swift` — interpretation DTO
- `ios/PulsePlate/Models/BMI/SoftPaywallHookDTO.swift` — soft paywall DTO

**Responsibilities:**

- Call canonical endpoint only
- Return DTOs as-is (no computation, no interpretation)
- Forbidden: BMI math, thresholds, category inference

### Tests

**Files:**

- `ios/PulsePlateTests/Networking/HTTPClientTests.swift` — error mapping tests (422 vs 400/500)
- `ios/PulsePlateTests/Networking/APIClientTests.swift` — request building tests (URL, headers, snake_case)
- `ios/PulsePlateTests/Services/BMIServiceThinAdapterTests.swift` — thinness verification tests

**Coverage:**

- ✅ 10 tests passing
- ✅ Contract boundary verified (422/400/500, snake_case, canonical path)
- ✅ Anti-flake: `StubURLProtocol.handler` reset in `tearDown()`

### Compatibility Shims (Temporary)

**Why:** To unblock compilation and tests without breaking existing UI code.

**Files:**

- `ios/PulsePlate/Models/NutritionData.swift` — renamed `APIError` → `NutritionAPIError` (naming conflict)
- `ios/PulsePlate/Services/BMIService.swift` (lines 48-159) — legacy compatibility shims:
  - `LegacyBMIServicing` protocol (uses `BMIRequest`/`BMIResponse`)
  - `DefaultBMIService` class (legacy implementation with direct `URLSession`)
  - `BMIServiceError` enum (legacy error type)
- `ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift` — still uses legacy types (migration deferred)
- `ios/PulsePlateTests/Mocks/MockBMIService.swift` — updated to `LegacyBMIServicing` for test compatibility

**Trade-off:** Code duplication (legacy vs new) accepted to keep PR scope focused (transport layer only). UI migration tracked in `BACKLOG_LEDGER.md` (P1 item).

**See:** `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md` for detailed analysis.

---

## DoD Evidence

### Tests

```bash
cd ios && xcodebuild -project PulsePlate.xcodeproj -scheme PulsePlate \
  -destination 'platform=iOS Simulator,id=8B9BF341-A44D-4BB0-A898-EC8CFEE56B79' \
  -only-testing:PulsePlateTests/HTTPClientTests \
  -only-testing:PulsePlateTests/APIClientTests \
  -only-testing:PulsePlateTests/BMIServiceThinAdapterTests test
```

**Result:** ✅ 10 tests passing

- `HTTPClientTests` (4 tests): 422 vs 400/500 error mapping
- `APIClientTests` (3 tests): URL building, headers, snake_case encoding
- `BMIServiceThinAdapterTests` (3 tests): canonical path, DTO passthrough, nullable `category`

### Contract Verification

- ✅ `HTTPClient` distinguishes 422 (`detail[]`) vs 400/500 (`detail: str`)
- ✅ `APIClient` builds URL from `baseURL + path`, sets `Content-Type`, supports custom headers
- ✅ `BMIService` calls canonical path `/api/v1/bmi/calculate`, only passthrough DTO
- ✅ DTO contract: `category: String?` (nullable), `soft_paywall: nil|object`, `visualization.ranges.from/to` verified

### Documentation

- ✅ `AGENTS.md` updated (thin client policy, contract-first, legacy DTO migration tracking, "No dual-path networking" rule)
- ✅ `BACKLOG_LEDGER.md` updated (UI migration tracked as P1 item)
- ✅ Audit document: `docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md`
- ✅ Technical debt report: `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md`

**Full DoD checklist:** `docs/PR_XXX_DOD_CHECKLIST.md`

---

## Deferred / Follow-ups

**Tracked in:** `docs/roadmap/BACKLOG_LEDGER.md`

### P1 — UI Migration (Post PR-XXX) 🔴

**Item:** "Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO; delete legacy BMIRequest/BMIResponse (iOS)"

**Scope:**

- Migrate `BMICalculatorViewModel` to use `BMIServicing` + DTOs
- Update `BMICalculatorScreen` to use new DTOs
- Delete legacy types: `BMIRequest`, `BMIResponse`
- Delete legacy shims: `LegacyBMIServicing`, `DefaultBMIService`, `BMIServiceError`
- Update `MockBMIService` to `BMIServicing`
- Single HTTP client path (no duplication)

**DoD:** See `BACKLOG_LEDGER.md` (P1 item: "Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO")

**Technical debt created in this PR:** See `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md`

### P1 — Other Services Migration (Post PR-XXX)

**Item:** "Unify ShoppingListService / WeeklyPlanService under thin HTTP adapter (iOS)"

**Scope:**

- Migrate `ShoppingListService` to use `APIClient` (no direct `URLSession`)
- Migrate `WeeklyPlanService` to use `APIClient` (no direct `URLSession`)
- Replace custom error enums with `APIError` from Networking layer
- All services follow same thin adapter pattern

**DoD:** See `BACKLOG_LEDGER.md` (P1 item: "Unify ShoppingListService / WeeklyPlanService under thin HTTP adapter")

**Rationale:** Enforces "No dual-path networking" rule (see `AGENTS.md`)

### P0 — Web Thin Adapter (Post PR-562)

**Item:** "PR-563 Thin HTTP Adapter (Web)"

**Scope:**

- Implement thin fetch wrapper (TypeScript)
- Generate types from OpenAPI (`openapi-typescript`)
- Error envelope mapping (422 vs 400/500)
- BMI API client (transport only)

**DoD:** See `BACKLOG_LEDGER.md` (P0 item: "PR-563 Thin HTTP Adapter (Web)")

---

## Breaking Changes

**None** — this PR adds new transport layer without breaking existing UI code. Legacy compatibility shims ensure backward compatibility until UI migration.

---

## Testing

### Unit Tests

- ✅ `HTTPClientTests` — error mapping (422 vs 400/500)
- ✅ `APIClientTests` — request building (URL, headers, snake_case)
- ✅ `BMIServiceThinAdapterTests` — thinness verification (canonical path, DTO passthrough)

**Full test results:** See `docs/PR_XXX_DOD_CHECKLIST.md` (section: "Tests")

### Manual Testing

- ✅ Project compiles
- ✅ Existing UI code still works (via legacy shims)
- ✅ New `BMIService` can be used independently (for future UI migration)

---

## References

- **DoD Checklist:** `docs/PR_XXX_DOD_CHECKLIST.md`
- **Review Checklist:** `docs/PR_XXX_REVIEW_CHECKLIST.md`
- **Audit document:** `docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md`
- **Technical debt report:** `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md`
- **Context handoff:** `docs/CONTEXT_HANDOFF_2026-01-21.md`
- **Backlog ledger:** `docs/roadmap/BACKLOG_LEDGER.md`
- **Thin client policy:** `AGENTS.md` (section: "Thin HTTP Adapter Policy (Hard Rule)")

---

**Related PRs:**

- PR-560: CI iOS stability (merged 2026-01-21)
- PR-561: Trivy suppression (merged 2026-01-21)

---

**Reviewer notes:**

- Focus on transport layer correctness (error mapping, URL building, snake_case)
- Verify no BMI math in client code (grep for thresholds)
- Check DTO alignment with backend schema (`app/schemas/bmi.py`)
- Legacy shims are temporary (documented in technical debt report)
