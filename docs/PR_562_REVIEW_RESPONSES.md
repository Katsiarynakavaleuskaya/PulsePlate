# PR-562 Review Responses (Quick Reference)

**PR:** PR-562 (Thin HTTP Adapter iOS)
**Date:** 2026-01-22
**Status:** In Review

---

## Common Review Questions & Answers

### Q1: "Why did you touch legacy/UI/compat shims in a transport PR?"

**Answer:**

> This is **temporary compatibility** to unblock compilation and tests without breaking existing UI code.
>
> **Technical debt is explicitly tracked** in `BACKLOG_LEDGER.md` (P1 item: "Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO") with DoD for removal.
>
> **Next PR:** "BMI UI migration to DTO + delete legacy shims" will remove:
> - `LegacyBMIServicing` protocol
> - `DefaultBMIService` class
> - `BMIServiceError` enum
> - Legacy `BMIRequest`/`BMIResponse` types
>
> **See:** `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md` for detailed analysis.

**Rationale:** PR scope is transport layer only. UI migration is separate, larger scope (ViewModel + Screen + tests). Legacy shims ensure backward compatibility until migration.

---

### Q2: "Why is there only one commit?"

**Answer:**

> PR scope is controlled by **DoD + audit + checklist**, not commit granularity.
>
> **History preserved:** Full commit structure documented in `docs/PR_XXX_COMMIT_STRUCTURE.md` (5 atomic commits if needed later).
>
> **Priority:** Safe merge without contract drift. Commit history can be squashed/split later if needed, but transport layer correctness is the blocker.

**Alternative:** If reviewer insists, we can split into 5 commits (see `docs/PR_XXX_COMMIT_STRUCTURE.md`), but this doesn't change PR scope or DoD.

---

### Q3: "Why isn't 422 error localized?"

**Answer:**

> This is **FastAPI standard** (`RequestValidationError` format: `{"detail": [{"type": "...", "loc": [...], "msg": "...", "input": ...}]}`).
>
> **Contract frozen:** Backend returns `msg` in plain English (not i18n keys) for 422 errors. This is documented in audit (`docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md`).
>
> **Client responsibility:** Map error format to UI-friendly messages (UI layer), not transport layer.
>
> **400/500 errors:** These ARE localized (via backend `t(lang, key)`), and client displays them as-is.

**See:** `AGENTS.md` section "Thin HTTP Adapter Policy" — transport layer maps error envelope format, UI layer handles localization.

---

### Q4: "Why is there code duplication (DefaultBMIService vs BMIService)?"

**Answer:**

> This is **temporary technical debt** to unblock compilation without breaking existing UI code.
>
> **Isolated:** Legacy shims are in `BMIService.swift` lines 48-159, clearly marked as temporary.
>
> **Removal plan:** Next PR (BMI UI migration) will delete `DefaultBMIService` and unify on `BMIService(APIClient(HTTPClient))`.
>
> **Trade-off:** Code duplication accepted to keep PR scope focused (transport layer only). UI migration tracked in `BACKLOG_LEDGER.md` (P1 item).

**See:** `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md` for detailed analysis and follow-up plan.

---

### Q5: "Why are there two error types (BMIServiceError vs APIError)?"

**Answer:**

> `BMIServiceError` is **legacy error type** for backward compatibility with existing UI code (`BMICalculatorViewModel`).
>
> **New code:** Should use `APIError` from `Networking/APIError.swift`.
>
> **Removal plan:** When UI migrates to new DTOs, `BMIServiceError` will be deleted and replaced with `APIError`.
>
> **Isolated:** Legacy error type only used by legacy shims (lines 48-159 in `BMIService.swift`).

**See:** `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md` section "Technical Debt Created".

---

### Q6: "Shouldn't ShoppingListService/WeeklyPlanService also use APIClient?"

**Answer:**

> Yes, that's tracked in `BACKLOG_LEDGER.md` (P1 item: "Unify ShoppingListService / WeeklyPlanService under thin HTTP adapter").
>
> **This PR:** Establishes the pattern (`APIClient`/`HTTPClient`).
>
> **Next PRs:** Other services will migrate in follow-up PRs (see `AGENTS.md` "No dual-path networking" rule).
>
> **Rationale:** Keeps PR scope focused (BMI service only). Other services migration is separate scope.

**See:** `BACKLOG_LEDGER.md` (P1 item: "Unify ShoppingListService / WeeklyPlanService under thin HTTP adapter").

---

### Q7: "Why does BMICalculatorViewModel still use legacy types?"

**Answer:**

> UI migration is **deferred to separate PR** to keep this PR focused on transport layer only.
>
> **Tracked:** `BACKLOG_LEDGER.md` (P1 item: "Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO").
>
> **This PR:** Adds new transport layer without breaking existing UI code.
>
> **Next PR:** Will migrate ViewModel + Screen to new DTOs and delete legacy types.

**See:** `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md` section "ViewModel Still Uses Legacy Types".

---

### Q8: "Can you add more tests?"

**Answer:**

> **Current coverage:** 10 tests covering contract boundary (422 vs 400/500, snake_case, canonical path, DTO passthrough).
>
> **Scope:** Transport layer only (no business logic to test).
>
> **If reviewer requests specific tests:** Please specify which contract boundary needs additional verification. Current tests cover:
> - Error mapping (422 vs 400/500)
> - Request building (URL, headers, snake_case)
> - Thinness verification (canonical path, DTO passthrough)

**See:** `docs/PR_XXX_DOD_CHECKLIST.md` section "Tests" for full test coverage details.

---

### Q9: "Can you add retry logic / timeout handling?"

**Answer:**

> **Out of scope:** This PR is transport layer only (error mapping, URL building, JSON encode/decode).
>
> **Future enhancement:** Retry/timeout logic can be added in follow-up PR (transport layer enhancements).
>
> **Current:** `HTTPClient` uses `URLSession.shared` defaults (timeouts handled by system).

**Rationale:** Keeps PR focused on contract correctness. Transport enhancements (retry, timeout, circuit breaker) are separate scope.

---

### Q10: "Why is AnyCodable marked as @unchecked Sendable?"

**Answer:**

> `AnyCodable` is **test-only helper** for decoding validation payloads in tests.
>
> **Usage:** Only in test fixtures, not in production code or across actor boundaries.
>
> **Rationale:** `Any` type cannot be `Sendable` without `@unchecked`, but usage is isolated to single-threaded test context.
>
> **Documentation:** Comment in code explains: "Used only for decoding backend validation payloads in tests. Must not cross actor boundaries with non-primitive values."

**See:** `ios/PulsePlate/Services/BMIService.swift` lines 163-167 (AnyCodable documentation).

---

## Red Flags to Watch For

**If reviewer asks to:**

1. **Add BMI math to client** → **BLOCK** (violates thin client policy)
2. **Remove legacy shims in this PR** → **DEFER** (tracked in BACKLOG_LEDGER, separate PR)
3. **Migrate UI in this PR** → **DEFER** (separate scope, tracked in BACKLOG_LEDGER)
4. **Add business logic to transport layer** → **BLOCK** (violates thin client policy)

**Acceptable requests:**

- Split commits (if reviewer insists, see `docs/PR_XXX_COMMIT_STRUCTURE.md`)
- Add more contract boundary tests (if specific gap identified)
- Clarify documentation (if unclear)
- Fix typos / formatting

---

## Quick Links for Reviewer

- **DoD Checklist:** `docs/PR_XXX_DOD_CHECKLIST.md`
- **Review Checklist:** `docs/PR_XXX_REVIEW_CHECKLIST.md`
- **Technical Debt Report:** `docs/audit/PR_XXX_TECHNICAL_DEBT_REPORT.md`
- **Audit Document:** `docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md`
- **Backlog Ledger:** `docs/roadmap/BACKLOG_LEDGER.md`

---

**Last updated:** 2026-01-22
**Status:** Ready for review
