# PR-562 DoD Checklist (Thin HTTP Adapter iOS)

**PR:** PR-562
**Date:** 2026-01-22
**Status:** ✅ All checks passing

---

## ✅ Must-have (Transport Layer)

### HTTPClient

- [x] Distinguishes 422 (`detail[]`) vs 400/500 (`detail: str`)
  - **Evidence:** `HTTPClientTests.test_422_decodesValidationErrorResponse()` passes
  - **Evidence:** `HTTPClientTests.test_400_decodesSimpleErrorResponse()` passes
  - **Evidence:** `HTTPClientTests.test_500_decodesSimpleErrorResponse()` passes

- [x] Uses `ValidationErrorResponse` for 422 decoding
  - **Evidence:** `HTTPClient.swift` line 70-76: `decodeValidationError(from:)`

- [x] Uses `SimpleErrorResponse` for 400/500 decoding
  - **Evidence:** `HTTPClient.swift` line 80-91: `decodeAPIError(from:statusCode:)`

- [x] Throws `APIError.validation()` for 422
  - **Evidence:** `HTTPClient.swift` line 52: `throw try decodeValidationError(from: data)`

- [x] Throws `APIError.api(statusCode, message)` for 400/500
  - **Evidence:** `HTTPClient.swift` line 52: `throw try decodeAPIError(from: data, statusCode: httpResponse.statusCode)`

- [x] Handles decoding failures gracefully
  - **Evidence:** `HTTPClient.swift` line 66-68: `catch { throw APIError.decodingFailed(...) }`

- [x] No business logic (BMI math, thresholds, categories)
  - **Evidence:** `grep -r "18\.5\|24\.9\|25\|30" ios/PulsePlate/Networking/` → no matches

### APIClient

- [x] Builds URL from `baseURL + path` correctly
  - **Evidence:** `APIClientTests.test_post_buildsCorrectURLAndHeadersAndBody()` passes
  - **Evidence:** `APIClient.swift` line 45: `baseURL.appendingPathComponent(path)`

- [x] Sets `Content-Type: application/json` header
  - **Evidence:** `APIClientTests.test_post_buildsCorrectURLAndHeadersAndBody()` passes
  - **Evidence:** `APIClient.swift` line 47: `request.setValue("application/json", forHTTPHeaderField: "Content-Type")`

- [x] Supports custom headers (passed through)
  - **Evidence:** `APIClientTests.test_post_withCustomHeaders_appendsHeaders()` passes
  - **Evidence:** `APIClient.swift` line 49-51: `headers.forEach { ... }`

- [x] JSON encodes request body with `snake_case` conversion
  - **Evidence:** `APIClientTests.test_post_buildsCorrectURLAndHeadersAndBody()` verifies `json?["weight_kg"]`
  - **Evidence:** `BMICalculateRequestDTO.swift` uses `CodingKeys` for snake_case mapping

- [x] Uses `HTTPClientProtocol` for dependency injection
  - **Evidence:** `APIClient.swift` line 36: `private let httpClient: HTTPClientProtocol`

- [x] No business logic
  - **Evidence:** `grep -r "18\.5\|24\.9\|25\|30" ios/PulsePlate/Networking/APIClient.swift` → no matches

### BMIService

- [x] Calls canonical endpoint `/api/v1/bmi/calculate` only
  - **Evidence:** `BMIServiceThinAdapterTests.test_calculate_callsCanonicalEndpoint()` passes
  - **Evidence:** `BMIService.swift` line 30: `path: "/api/v1/bmi/calculate"`

- [x] Uses `APIClientProtocol` (dependency injection)
  - **Evidence:** `BMIService.swift` line 21: `private let apiClient: APIClientProtocol`

- [x] Returns `BMICalculateResponseDTO` as-is (no modification)
  - **Evidence:** `BMIServiceThinAdapterTests.test_calculate_returnsBMICalculateResponseDTO()` passes

- [x] No BMI math, thresholds, category inference
  - **Evidence:** `grep -r "18\.5\|24\.9\|25\|30" ios/PulsePlate/Services/BMIService.swift` → no matches (only in legacy shims, lines 48-159)

- [x] No i18n logic (backend provides localized text)
  - **Evidence:** `BMIService.swift` lines 1-46: no i18n code

- [x] No soft paywall logic (backend provides hook structure)
  - **Evidence:** `BMIService.swift` lines 1-46: no paywall code

---

## ✅ Contract Enforcement

### DTO Contract

- [x] `category: String?` is nullable
  - **Evidence:** `BMICalculateResponseDTO.swift` line 8: `public let category: String?`
  - **Evidence:** `BMIServiceThinAdapterTests.test_calculate_nullableCategory_decodesCorrectly()` passes

- [x] `soft_paywall: nil|object` (never `{enabled: false}`)
  - **Evidence:** `BMICalculateResponseDTO.swift` line 18: `public let softPaywall: SoftPaywallHookDTO?`
  - **Evidence:** Audit doc confirms backend returns `null` when disabled

- [x] `visualization.ranges[].from/to` are optional
  - **Evidence:** `BMIScaleV1DTO.swift`: `BMIRangeDTO` has `from: Double?`, `to: Double?`
  - **Evidence:** `BMIServiceThinAdapterTests.test_calculate_returnsBMICalculateResponseDTO()` verifies `from`/`to` decoding

- [x] `SoftPaywallAvailabilityDTO` includes `reasonKey: String?`
  - **Evidence:** `SoftPaywallHookDTO.swift` line 48: `public let reasonKey: String?`

- [x] `BMIInterpretationV1DTO` includes all fields
  - **Evidence:** `BMIInterpretationV1DTO.swift`: includes `goalDirection`, `targetRange`, `priorityNotes`

### Error Contract

- [x] 422: `{"detail": [{"type": "...", "loc": [...], "msg": "...", "input": ...}]}`
  - **Evidence:** `ErrorsDTO.swift`: `ValidationErrorResponse` matches format
  - **Evidence:** `HTTPClientTests.test_422_decodesValidationErrorResponse()` passes

- [x] 400/500: `{"detail": "localized text"}`
  - **Evidence:** `ErrorsDTO.swift`: `SimpleErrorResponse` matches format
  - **Evidence:** `HTTPClientTests.test_400_decodesSimpleErrorResponse()` passes

### Tests

- [x] 10 tests passing
  - **Evidence:** `xcodebuild test` output shows 10 tests passed:
    - `HTTPClientTests` (4 tests)
    - `APIClientTests` (3 tests)
    - `BMIServiceThinAdapterTests` (3 tests)

- [x] Anti-flake: `tearDown()` resets `StubURLProtocol.handler`
  - **Evidence:** `HTTPClientTests.swift` line 30-32: `override func tearDown() { StubURLProtocol.handler = nil }`

- [x] Contract boundary verified
  - **Evidence:** Tests verify 422 vs 400/500, snake_case, canonical path

---

## ✅ Documentation

### AGENTS.md

- [x] "Thin HTTP Adapter Policy (Hard Rule)" section added
  - **Evidence:** `AGENTS.md` lines 320-361: section exists

- [x] Forbidden patterns listed
  - **Evidence:** `AGENTS.md` lines 321-326: forbidden patterns listed

- [x] Allowed patterns listed
  - **Evidence:** `AGENTS.md` lines 328-335: allowed patterns listed

- [x] Contract-first principle documented
  - **Evidence:** `AGENTS.md` lines 337-341: contract-first principle

- [x] Enforcement mechanisms listed
  - **Evidence:** `AGENTS.md` lines 343-347: enforcement mechanisms

### BACKLOG_LEDGER.md

- [x] UI migration item added (P1)
  - **Evidence:** `BACKLOG_LEDGER.md` lines 149-178: P1 item exists

- [x] Technical debt details included
  - **Evidence:** `BACKLOG_LEDGER.md` lines 152-160: technical debt details

- [x] DoD for UI migration specified
  - **Evidence:** `BACKLOG_LEDGER.md` lines 161-178: DoD specified

- [x] Links to relevant files
  - **Evidence:** `BACKLOG_LEDGER.md` lines 153-159: links included

### Audit Document

- [x] `PR_562_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md` exists
  - **Evidence:** File exists in `docs/audit/`

- [x] Contract freeze declaration included
  - **Evidence:** Audit doc has "Contract Freeze Declaration" section

- [x] All TODOs replaced with facts from code
  - **Evidence:** Audit doc verified against `app/schemas/bmi.py`

### Technical Debt Report

- [x] `PR_562_TECHNICAL_DEBT_REPORT.md` exists
  - **Evidence:** File exists in `docs/audit/`

- [x] Technical debt items listed with rationale
  - **Evidence:** Report includes detailed analysis

- [x] Follow-up plan specified
  - **Evidence:** Report includes "Follow-Up Plan" section

- [x] Risk assessment included
  - **Evidence:** Report includes "Impact Assessment" table

---

## ✅ Compatibility Shims (Temporary)

- [x] Legacy shims documented
  - **Evidence:** `BMIService.swift` lines 48-52: comments explain temporary nature
  - **Evidence:** `BMICalculatorViewModel.swift` lines 6-19: TODO comments reference BACKLOG_LEDGER.md

- [x] Naming conflicts resolved
  - **Evidence:** `NutritionData.swift`: `APIError` renamed to `NutritionAPIError`

- [x] UI still compiles
  - **Evidence:** `xcodebuild build` succeeds

- [x] Tests still pass
  - **Evidence:** `xcodebuild test` shows 10 tests passing

---

## ✅ Final Verification

- [x] All tests passing (10 tests)
  - **Command:** `xcodebuild test -only-testing:PulsePlateTests/HTTPClientTests -only-testing:PulsePlateTests/APIClientTests -only-testing:PulsePlateTests/BMIServiceThinAdapterTests`
  - **Result:** ✅ 10 tests passed

- [x] No BMI math in client code
  - **Command:** `grep -r "18\.5\|24\.9\|25\|30" ios/PulsePlate/Networking/ ios/PulsePlate/Services/BMIService.swift | grep -v "test\|TODO\|comment"`
  - **Result:** ✅ No matches (except in legacy shims, which are temporary)

- [x] DTOs match backend schema
  - **Method:** Manual review of `ios/PulsePlate/Models/BMI/*.swift` vs `app/schemas/bmi.py`
  - **Result:** ✅ DTOs aligned

- [x] Contract freeze documented
  - **Evidence:** Audit doc has "Contract Freeze Declaration" section

- [x] Technical debt tracked
  - **Evidence:** `BACKLOG_LEDGER.md` updated, technical debt report created

---

## Summary

**Status:** ✅ **All DoD checks passing**

- ✅ Transport layer implemented (HTTPClient, APIClient, BMIService)
- ✅ 10 tests passing (contract boundary verified)
- ✅ DTOs aligned to backend schema
- ✅ Documentation updated (AGENTS.md, BACKLOG_LEDGER.md)
- ✅ Technical debt tracked and documented
- ✅ Compatibility shims added (temporary, documented)

**Ready for:** PR review and merge

---

**Last updated:** 2026-01-22
**Verified by:** @katsiaryna_kavaleuskaya
