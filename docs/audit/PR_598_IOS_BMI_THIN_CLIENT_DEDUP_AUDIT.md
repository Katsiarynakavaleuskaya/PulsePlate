# PR-598 — iOS BMI thin-client dedup (verification audit)

Status: 🟢 Verified (already remediated in PR-596)
Owner: @katsiaryna_kavaleuskaya
Date: 26 января 2026 года

## 0) Goal

Verify that iOS BMI feature no longer contains legacy BMI shims/types and uses:

- **Canonical DTOs**: `BMICalculateRequestDTO` / `BMICalculateResponseDTO`
- **One HTTP path**: `BMIService` → `APIClient` → `HTTPClient` (no direct URLSession outside transport)
- **Canonical errors**: `APIError` (incl. `transport` vs `unknown`)

## 1) Scope / Non-goals

### In-scope

- iOS BMI transport + DTO boundary + error mapping in the BMI feature surface.

### Out-of-scope

- Any backend BMI math / categorization.
- Any UI redesign or UX improvements (only contract/transport correctness).

## 2) Canonical invariants (policy anchors)

- **Thin HTTP Adapter**: iOS client must be transport/contract/UX only; no domain logic.
- **No dual-path networking**: no direct `URLSession` usage outside `Networking/*`.
- **APIError semantics**:
  - Network/transport failures → `APIError.transport` (never `statusCode: 0`)
  - Unexpected non-`APIError` failures → `APIError.unknown` (not transport)

## 3) Evidence commands (copy/paste)

```bash
# Legacy shims/types MUST be absent
rg -n "LegacyBMIServicing|DefaultBMIService|BMIServiceError\\b|\\bBMIRequest\\b|\\bBMIResponse\\b" ios/

# Canonical BMI DTO usage
rg -n "BMICalculateRequestDTO|BMICalculateResponseDTO" ios/PulsePlate ios/PulsePlateTests

# Endpoint path and transport seam
rg -n "/api/v1/bmi/calculate" ios/PulsePlate
rg -n "APIClient\\(|HTTPClient\\(|URLSession\\.shared|URLSession\\(" ios/PulsePlate
```

## 4) Findings (AS-IS, verified)

### 4.1 Canonical DTOs used by UI/service

- `ios/PulsePlate/Screens/BMICalculatorScreen.swift:103-114` builds `BMICalculateRequestDTO`.
- `ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift:6-32` stores `BMICalculateResponseDTO?` and `APIError?`.
- `ios/PulsePlate/Models/BMI/BMICalculateRequestDTO.swift` documents canonical request contract (snake_case keys).

### 4.2 Single HTTP path (thin adapter)

- `ios/PulsePlate/Services/BMIService.swift:27-34` calls **canonical** endpoint:
  - `POST /api/v1/bmi/calculate`
  - via `apiClient.post(path:..., body: request)`

### 4.3 Legacy shims/types removed

Verified: no matches for `LegacyBMIServicing`, `DefaultBMIService`, `BMIServiceError`, `BMIRequest`, `BMIResponse` in `ios/`.

### 4.4 Error mapping semantics present

- `ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift:27-32`:
  - `APIError` is preserved as-is
  - non-`APIError` failures map to `APIError.unknown(...)`

## 5) AS-IS → TO-BE table

| Area | AS-IS | TO-BE | Status |
|------|-------|-------|--------|
| DTO boundary | `BMICalculateRequestDTO/ResponseDTO` | same | ✅ |
| Transport seam | `BMIService → APIClient → HTTPClient` | same | ✅ |
| Legacy BMI shims/types | absent | absent | ✅ |
| Error semantics | `APIError.transport` vs `APIError.unknown` | same | ✅ |

## 6) Decision

**No remediation PR needed** for “BMI thin-client dedup”: the intended end state is already present (landed via PR-596).

## 7) Links

- PR-596 (remediation): `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596`
