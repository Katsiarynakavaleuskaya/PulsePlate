# PR-XXX Review Checklist (Thin HTTP Adapter iOS)

**Reviewer:** @katsiaryna_kavaleuskaya (or assigned reviewer)
**PR:** PR-XXX
**Date:** 2026-01-22

---

## ✅ Pre-Review Checks

- [ ] PR description includes "Contract Freeze" section
- [ ] PR description includes "Compatibility Shims (Temporary)" section
- [ ] PR description links to technical debt report
- [ ] All commits are atomic (one logical change per commit)
- [ ] Commit messages follow convention (`feat:`, `test:`, `fix:`, `docs:`)

---

## 🔍 Code Review — Transport Layer

### HTTPClient.swift

- [ ] Distinguishes 422 (`detail[]`) vs 400/500 (`detail: str`)
- [ ] Uses `ValidationErrorResponse` for 422 decoding
- [ ] Uses `SimpleErrorResponse` for 400/500 decoding
- [ ] Throws `APIError.validation()` for 422
- [ ] Throws `APIError.api(statusCode, message)` for 400/500
- [ ] Handles decoding failures gracefully (`APIError.decodingFailed`)
- [ ] No business logic (BMI math, thresholds, categories)

### APIClient.swift

- [ ] Builds URL from `baseURL + path` correctly
- [ ] Sets `Content-Type: application/json` header
- [ ] Supports custom headers (passed through)
- [ ] JSON encodes request body with `snake_case` conversion
- [ ] Uses `HTTPClientProtocol` for dependency injection
- [ ] No business logic

### APIError.swift

- [ ] Enum cases: `.validation()`, `.api()`, `.decodingFailed()`, `.invalidResponse()`, `.unhandledStatusCode()`
- [ ] Conforms to `LocalizedError` (for UI display)
- [ ] Conforms to `Equatable`, `Sendable` (for testing/concurrency)

### ErrorsDTO.swift

- [ ] `ValidationErrorResponse` matches backend 422 format exactly
- [ ] `SimpleErrorResponse` matches backend 400/500 format exactly
- [ ] `ValidationErrorItem` includes all fields: `type`, `loc`, `msg`, `input`

---

## 🔍 Code Review — BMI Thin Adapter

### BMIService.swift

- [ ] Calls canonical endpoint `/api/v1/bmi/calculate` only
- [ ] Uses `APIClientProtocol` (dependency injection)
- [ ] Returns `BMICalculateResponseDTO` as-is (no modification)
- [ ] No BMI math, thresholds, category inference
- [ ] No i18n logic (backend provides localized text)
- [ ] No soft paywall logic (backend provides hook structure)

### DTOs (BMICalculateRequestDTO, BMICalculateResponseDTO, etc.)

- [ ] Field names match backend schema exactly (`snake_case` → `camelCase` via `CodingKeys`)
- [ ] Types match backend schema (nullable fields, enums, arrays)
- [ ] `category: String?` is nullable (valid for child/teen/pregnant/too_young)
- [ ] `soft_paywall: nil|object` (never `{enabled: false}`)
- [ ] `visualization.ranges[].from/to` are optional (for future extensions)
- [ ] `SoftPaywallAvailabilityDTO` includes `reasonKey: String?`
- [ ] `BMIInterpretationV1DTO` includes all fields (`goalDirection`, `targetRange`, `priorityNotes`)

---

## 🔍 Code Review — Tests

### HTTPClientTests.swift

- [ ] Tests 422 error decoding (`detail[]` → `APIError.validation()`)
- [ ] Tests 400/500 error decoding (`detail: str` → `APIError.api()`)
- [ ] Tests successful 200 decoding
- [ ] Uses `StubURLProtocol` for mocking
- [ ] **Anti-flake:** `tearDown()` resets `StubURLProtocol.handler = nil`
- [ ] No business logic in tests

### APIClientTests.swift

- [ ] Tests URL building (`baseURL + path`)
- [ ] Tests `Content-Type` header
- [ ] Tests custom headers (passed through)
- [ ] Tests `snake_case` conversion in JSON body
- [ ] Uses `CapturingHTTPClient` mock
- [ ] `DummyResponse` can decode from `{}` (has `ok: Bool?` field)

### BMIServiceThinAdapterTests.swift

- [ ] Tests canonical path `/api/v1/bmi/calculate`
- [ ] Tests DTO passthrough (no modification)
- [ ] Tests nullable `category` decoding
- [ ] Tests `visualization.ranges[].key`, `from`, `to` decoding
- [ ] Uses `FakeAPIClient` mock
- [ ] No business logic in tests

---

## 🔍 Code Review — Compatibility Shims

### NutritionData.swift

- [ ] `APIError` renamed to `NutritionAPIError` (naming conflict resolved)
- [ ] Comment explains why (to avoid conflict with `Networking/APIError`)

### BMIService.swift (Legacy Shims)

- [ ] `LegacyBMIServicing` protocol clearly marked as temporary
- [ ] `DefaultBMIService` clearly marked as temporary
- [ ] `BMIServiceError` clearly marked as temporary
- [ ] TODO comments reference `BACKLOG_LEDGER.md`
- [ ] Legacy shims isolated to lines 48-159 (not mixed with new code)

### BMICalculatorViewModel.swift

- [ ] Still uses legacy types (expected — migration deferred)
- [ ] TODO comments reference `BACKLOG_LEDGER.md`
- [ ] No breaking changes to public API

### MockBMIService.swift

- [ ] Updated to `LegacyBMIServicing` (for test compatibility)
- [ ] Comment explains why (temporary until UI migration)

---

## 🔍 Code Review — Documentation

### AGENTS.md

- [ ] "Thin HTTP Adapter Policy (Hard Rule)" section added
- [ ] Forbidden patterns listed (BMI math, thresholds, business logic)
- [ ] Allowed patterns listed (transport, error mapping, i18n lookup)
- [ ] Contract-first principle documented
- [ ] Enforcement mechanisms listed (guard tests, code review)

### BACKLOG_LEDGER.md

- [ ] UI migration item added (P1)
- [ ] Technical debt details included (legacy shims, code duplication)
- [ ] DoD for UI migration specified
- [ ] Links to relevant files

### Audit Document

- [ ] `PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md` exists
- [ ] Contract freeze declaration included
- [ ] All TODOs replaced with facts from code

### Technical Debt Report

- [ ] `PR_XXX_TECHNICAL_DEBT_REPORT.md` exists
- [ ] Technical debt items listed with rationale
- [ ] Follow-up plan specified
- [ ] Risk assessment included

---

## ⚠️ Red Flags (Blockers)

- [ ] **BMI math in client code** (any thresholds, categories, calculations) → **BLOCK**
- [ ] **Business logic in transport layer** (interpretation, i18n keys computed) → **BLOCK**
- [ ] **DTO fields don't match backend schema** (missing fields, wrong types) → **BLOCK**
- [ ] **Tests don't verify contract** (no 422/400/500 tests, no snake_case tests) → **BLOCK**
- [ ] **No tearDown() in HTTPClientTests** (potential test flakiness) → **BLOCK**
- [ ] **Legacy shims not documented** (no comments, no BACKLOG_LEDGER entry) → **BLOCK**

---

## ✅ Green Flags (Good Practices)

- [ ] ✅ Dependency injection via protocols (`HTTPClientProtocol`, `APIClientProtocol`)
- [ ] ✅ Tests use mocks (no real network calls)
- [ ] ✅ Anti-flake measures (`tearDown()` resets static state)
- [ ] ✅ Contract verification in tests (422 vs 400/500, snake_case, canonical path)
- [ ] ✅ Documentation updated (`AGENTS.md`, `BACKLOG_LEDGER.md`)
- [ ] ✅ Technical debt explicitly tracked and documented

---

## 📋 Review Questions (For Reviewer)

1. **Scope:** Is PR scope clear? (Transport layer only, UI migration deferred)
2. **Contract:** Are DTOs aligned with backend schema? (Check against `app/schemas/bmi.py`)
3. **Tests:** Do tests verify contract boundary? (422 vs 400/500, snake_case, canonical path)
4. **Technical debt:** Is technical debt acceptable? (Code duplication vs scope discipline)
5. **Documentation:** Are follow-ups tracked? (BACKLOG_LEDGER.md updated)

---

## 🎯 Approval Criteria

**Must-have:**
- ✅ All tests passing (10 tests)
- ✅ No BMI math in client code (grep verification)
- ✅ DTOs match backend schema (manual review)
- ✅ Contract freeze documented
- ✅ Technical debt tracked in BACKLOG_LEDGER.md

**Nice-to-have:**
- ✅ Commits are atomic
- ✅ PR description is comprehensive
- ✅ Documentation is clear

---

**Reviewer notes:**

---

**Status:** ⏳ Pending review
