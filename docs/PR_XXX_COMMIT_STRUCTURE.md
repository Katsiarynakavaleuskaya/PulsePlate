# PR-XXX Commit Structure (Atomic Commits)

**PR:** PR-XXX (Thin HTTP Adapter iOS)
**Date:** 2026-01-22

---

## Commit 1: Networking transport (core)

**Message:**
```
feat(ios): add thin HTTPClient + APIClient error mapping

- HTTPClient: low-level HTTP client with error envelope mapping
  - Distinguishes 422 (detail[]) vs 400/500 (detail: str)
  - Uses ValidationErrorResponse for 422 decoding
  - Uses SimpleErrorResponse for 400/500 decoding
- APIClient: request builder (URL, headers, JSON encoding)
  - Builds URL from baseURL + path
  - Sets Content-Type: application/json
  - Supports custom headers
  - JSON encodes with snake_case conversion
- APIError: unified error model (422 vs 400/500)
- ErrorsDTO: error response DTOs (ValidationErrorResponse, SimpleErrorResponse)

Transport layer only (no business logic).
```

**Files:**
- `ios/PulsePlate/Networking/HTTPClient.swift` (new)
- `ios/PulsePlate/Networking/APIClient.swift` (new)
- `ios/PulsePlate/Networking/APIError.swift` (new)
- `ios/PulsePlate/Networking/ErrorsDTO.swift` (new)

---

## Commit 2: BMI thin adapter + DTO contract

**Message:**
```
feat(ios): wire BMIService to thin adapter + canonical DTOs

- BMIService: thin wrapper over APIClient
  - Calls canonical endpoint /api/v1/bmi/calculate
  - Returns BMICalculateResponseDTO as-is (no computation)
  - Forbidden: BMI math, thresholds, category inference
- DTOs aligned to backend schema (app/schemas/bmi.py):
  - BMICalculateRequestDTO (request)
  - BMICalculateResponseDTO (response with nullable category)
  - WaistRiskDTO (wht_ratio, risk_level, notes[])
  - BMIScaleV1DTO (visualization ranges)
  - BMIInterpretationV1DTO (goalDirection, targetRange, priorityNotes)
  - SoftPaywallHookDTO (with reasonKey)

Contract frozen per audit document.
```

**Files:**
- `ios/PulsePlate/Services/BMIService.swift` (new BMIService class, lines 1-46)
- `ios/PulsePlate/Models/BMI/BMICalculateRequestDTO.swift` (new)
- `ios/PulsePlate/Models/BMI/BMICalculateResponseDTO.swift` (new)
- `ios/PulsePlate/Models/BMI/WaistRiskDTO.swift` (new)
- `ios/PulsePlate/Models/BMI/BMIScaleV1DTO.swift` (new)
- `ios/PulsePlate/Models/BMI/BMIInterpretationV1DTO.swift` (new)
- `ios/PulsePlate/Models/BMI/SoftPaywallHookDTO.swift` (new)

---

## Commit 3: Tests (contract boundary)

**Message:**
```
test(ios): add thin adapter contract tests (422/400/500, snake_case, path)

- HTTPClientTests: error mapping tests
  - 422 validation error decoding (detail[])
  - 400/500 API error decoding (detail: str)
  - Successful 200 decoding
  - Anti-flake: tearDown() resets StubURLProtocol.handler
- APIClientTests: request building tests
  - URL construction (baseURL + path)
  - Content-Type header
  - Custom headers
  - snake_case JSON encoding
- BMIServiceThinAdapterTests: thinness verification
  - Canonical path /api/v1/bmi/calculate
  - DTO passthrough (no modification)
  - Nullable category decoding
  - visualization.ranges[].key, from, to decoding

10 tests passing. Contract boundary verified.
```

**Files:**
- `ios/PulsePlateTests/Networking/HTTPClientTests.swift` (new)
- `ios/PulsePlateTests/Networking/APIClientTests.swift` (new)
- `ios/PulsePlateTests/Services/BMIServiceThinAdapterTests.swift` (new)

---

## Commit 4: Compatibility shims (temporary)

**Message:**
```
fix(ios): resolve naming conflicts and keep legacy BMI UI compiling

- NutritionData.swift: rename APIError → NutritionAPIError
  - Avoids conflict with Networking/APIError
- BMIService.swift: add legacy compatibility shims (lines 48-159)
  - LegacyBMIServicing protocol (uses BMIRequest/BMIResponse)
  - DefaultBMIService class (legacy implementation)
  - BMIServiceError enum (legacy error type)
- BMICalculatorViewModel.swift: use LegacyBMIServicing
  - Migration deferred to separate PR (tracked in BACKLOG_LEDGER.md)
- MockBMIService.swift: update to LegacyBMIServicing

Temporary shims to unblock compilation without breaking UI.
UI migration tracked in BACKLOG_LEDGER.md (P1 item).
See: docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md
```

**Files:**
- `ios/PulsePlate/Models/NutritionData.swift` (rename APIError → NutritionAPIError)
- `ios/PulsePlate/Services/BMIService.swift` (add legacy shims, lines 48-159)
- `ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift` (use LegacyBMIServicing)
- `ios/PulsePlateTests/Mocks/MockBMIService.swift` (update to LegacyBMIServicing)

---

## Commit 5: Docs/Process updates

**Message:**
```
docs(process): enforce thin client policy and track UI DTO migration

- AGENTS.md: add "Thin HTTP Adapter Policy (Hard Rule)"
  - Forbidden patterns (BMI math, thresholds, business logic)
  - Allowed patterns (transport, error mapping, i18n lookup)
  - Contract-first principle
  - Enforcement mechanisms (guard tests, code review)
- BACKLOG_LEDGER.md: track UI migration (P1 item)
  - Technical debt details (legacy shims, code duplication)
  - DoD for UI migration
  - Links to relevant files
- docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md: contract freeze
- docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md: technical debt analysis
```

**Files:**
- `AGENTS.md` (add thin client policy section)
- `docs/roadmap/BACKLOG_LEDGER.md` (add UI migration item)
- `docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md` (if not already committed)
- `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md` (if not already committed)
- `docs/CONTEXT_HANDOFF_2026-01-21.md` (if not already committed)

---

## Alternative: Single Commit (If Already Too Late)

If commits are already mixed, use single commit with comprehensive message:

**Message:**
```
feat(ios): implement thin HTTP adapter for BMI service

Transport layer:
- HTTPClient: error mapping (422 vs 400/500)
- APIClient: request builder (URL, headers, JSON encoding)
- BMIService: thin wrapper (canonical path, DTO passthrough)
- DTOs aligned to backend schema (app/schemas/bmi.py)

Tests:
- 10 tests passing (HTTPClient, APIClient, BMIService)
- Contract boundary verified (422/400/500, snake_case, canonical path)
- Anti-flake: tearDown() resets StubURLProtocol.handler

Compatibility shims (temporary):
- LegacyBMIServicing/DefaultBMIService for existing UI
- UI migration tracked in BACKLOG_LEDGER.md (P1 item)

Documentation:
- AGENTS.md: thin client policy
- BACKLOG_LEDGER.md: UI migration tracking
- Technical debt report: docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md

See: docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md
```

---

## Git Commands (If Starting Fresh)

```bash
# Commit 1: Networking transport
git add ios/PulsePlate/Networking/HTTPClient.swift
git add ios/PulsePlate/Networking/APIClient.swift
git add ios/PulsePlate/Networking/APIError.swift
git add ios/PulsePlate/Networking/ErrorsDTO.swift
git commit -m "feat(ios): add thin HTTPClient + APIClient error mapping

- HTTPClient: low-level HTTP client with error envelope mapping
- APIClient: request builder (URL, headers, JSON encoding)
- APIError: unified error model (422 vs 400/500)
- ErrorsDTO: error response DTOs

Transport layer only (no business logic)."

# Commit 2: BMI thin adapter + DTOs
git add ios/PulsePlate/Services/BMIService.swift
git add ios/PulsePlate/Models/BMI/BMICalculateRequestDTO.swift
git add ios/PulsePlate/Models/BMI/BMICalculateResponseDTO.swift
git add ios/PulsePlate/Models/BMI/WaistRiskDTO.swift
git add ios/PulsePlate/Models/BMI/BMIScaleV1DTO.swift
git add ios/PulsePlate/Models/BMI/BMIInterpretationV1DTO.swift
git add ios/PulsePlate/Models/BMI/SoftPaywallHookDTO.swift
git commit -m "feat(ios): wire BMIService to thin adapter + canonical DTOs

- BMIService: thin wrapper over APIClient
- DTOs aligned to backend schema (app/schemas/bmi.py)
- Contract frozen per audit document."

# Commit 3: Tests
git add ios/PulsePlateTests/Networking/HTTPClientTests.swift
git add ios/PulsePlateTests/Networking/APIClientTests.swift
git add ios/PulsePlateTests/Services/BMIServiceThinAdapterTests.swift
git commit -m "test(ios): add thin adapter contract tests (422/400/500, snake_case, path)

10 tests passing. Contract boundary verified."

# Commit 4: Compatibility shims
git add ios/PulsePlate/Models/NutritionData.swift
git add ios/PulsePlate/Services/BMIService.swift  # (legacy shims only)
git add ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift
git add ios/PulsePlateTests/Mocks/MockBMIService.swift
git commit -m "fix(ios): resolve naming conflicts and keep legacy BMI UI compiling

Temporary shims to unblock compilation without breaking UI.
UI migration tracked in BACKLOG_LEDGER.md (P1 item)."

# Commit 5: Docs
git add AGENTS.md
git add docs/roadmap/BACKLOG_LEDGER.md
git add docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md
git add docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md
git add docs/CONTEXT_HANDOFF_2026-01-21.md
git commit -m "docs(process): enforce thin client policy and track UI DTO migration

- AGENTS.md: thin client policy
- BACKLOG_LEDGER.md: UI migration tracking
- Technical debt report"
```

---

## Verification After Commits

```bash
# Verify all tests still pass
cd ios && xcodebuild -project PulsePlate.xcodeproj -scheme PulsePlate \
  -destination 'platform=iOS Simulator,id=8B9BF341-A44D-4BB0-A898-EC8CFEE56B79' \
  -only-testing:PulsePlateTests/HTTPClientTests \
  -only-testing:PulsePlateTests/APIClientTests \
  -only-testing:PulsePlateTests/BMIServiceThinAdapterTests test

# Verify no BMI math in client code
grep -r "18\.5\|24\.9\|25\|30\|80\|88\|94\|102" ios/PulsePlate/Networking/ ios/PulsePlate/Services/BMIService.swift | grep -v "test\|TODO\|comment" || echo "OK: No BMI thresholds in transport layer"

# Verify DTOs match backend schema (manual review)
# Compare ios/PulsePlate/Models/BMI/*.swift with app/schemas/bmi.py
```

---

**Last updated:** 2026-01-22
