# Backlog Ledger (Canonical)

**Purpose:** single source of truth for postponed / follow-up work.
If it is not recorded here — it does not exist.

## Rules (non-negotiable)
1) Any postponed work MUST be recorded here immediately.
2) Each item MUST include:
   - Owner
   - Priority (P0/P1/P2)
   - Target PR (number or placeholder)
   - Reason for deferral
   - Links to relevant audit/docs
   - DoD (acceptance criteria)
3) Every PR description MUST include a "Deferred / Follow-ups" section with links to items here.
4) Closing an item requires:
   - PR merged OR explicit "won't do" decision recorded (with reason).

---

## P0 — Next (Must happen)
- [x] PR-560 CI iOS stability (merged 2026-01-21)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-560
  - Status: ✅ Merged
  - Links:
    - docs/CONTEXT_HANDOFF_2026-01-21.md

- [x] PR-561 Trivy suppression (CVE-2025-15281 glibc) (merged 2026-01-21)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-561
  - Status: ✅ Merged
  - Links:
    - docs/security/CVE-2025-15281-glibc.md
    - trivy/ignore-policy.rego

- [ ] PR-XXX Thin HTTP Adapter (iOS + Web)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-XXX (TBD)
  - Reason: unified thin transport layer for iOS and Web clients (no business logic)
  - Links:
    - docs/CONTEXT_HANDOFF_2026-01-21.md
    - docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md
  - DoD:
    - iOS: HTTPClient/APIClient/BMIService implemented (transport only)
    - Web: thin fetch wrapper + BMI API client (transport only)
    - No BMI/waist/risk logic on clients (grep policy / guard tests)
    - Unit tests green (iOS + Web)
    - DTOs aligned with backend OpenAPI schemas
    - Error envelope mapping implemented
    - AGENTS.md updated (thin client policy)
    - CI green

---

## P1 — Improvements (Optional / polish)

- [ ] Stabilize/restore PlateViewTests and UI tests in CI (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (separate from PR-559)
  - Reason: PlateViewTests unstable; UI tests excluded from PR-559 CI to unblock merge. Needs stabilization/rewrite before restoring to CI.
  - Links:
    - ios/PulsePlate/Tests/PlateViewTests.swift
    - .github/workflows/ci.yml (line 633: `-skip-testing:PulsePlateUITests`)
    - ios/AGENTS.md (Test scope policy)
  - DoD:
    - PlateViewTests stabilized (no flaky failures)
    - UI tests (`PulsePlateUITests`) pass consistently
    - `-skip-testing:PulsePlateUITests` removed from CI
    - CI green with UI tests included

- [ ] Stabilize AnimationTests.swift (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (separate from PR-559)
  - Reason: pre-existing compilation failures (missing types: PulsingView, ShimmerEffect, SlideInTransition, FadeTransition, AnimatedProgressRing, NutritionSegment; internal access issues). Excluded from PulsePlateTests target via `PBXFileSystemSynchronizedBuildFileExceptionSet.membershipExceptions` to unblock PR-559 CI.
  - Links:
    - ios/PulsePlateTests/AnimationTests.swift
    - ios/PulsePlate.xcodeproj/project.pbxproj (line 51: `AnimationTests.swift` in membershipExceptions)
    - ios/AGENTS.md (Animated/UI helper tests policy)
  - DoD:
    - Either rewrite using available public components
    - Or extract to separate test target
    - Or remove if dead test code (no longer needed)
    - AnimationTests.swift compiles without errors
    - All referenced types/modifiers are accessible (public/internal as needed)
    - Tests restored to PulsePlateTests target (if kept)
    - CI green with AnimationTests included (if restored)

- [ ] Fix ShoppingPlan public API (make nested types public or narrow API surface)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (separate from PR-559)
  - Reason: CodeRabbit flagged "ShoppingPlan isn't constructible" - public type with internal nested types (DailyMenu, Meal). Outside PR-559 scope but architectural smell.
  - Links:
    - ios/PulsePlate/Models/ShoppingList/ShoppingListStubPlan.swift
    - CodeRabbit comment (outside diff, actionable=0)
  - DoD:
    - Either make DailyMenu/Meal public with explicit init
    - Or narrow API: make ShoppingPlan/ShoppingListRequestPayload internal if it's "stub" only
    - No breaking changes to existing usage

- [ ] Wire soft paywall CTA to real paywall router (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Reason: paywall navigation infrastructure not yet available; hook is rendered but CTA is no-op
  - Links:
    - ios/PulsePlate/Screens/BMICalculatorScreen.swift (line ~73)
  - DoD:
    - Paywall router/navigation handler implemented
    - SoftPaywallHookView CTA wired to navigation
    - No TODO comments in production code
- [ ] Optional: CI script guard for iOS (repo-wide scan)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Reason: current Swift Testing guard is sufficient; script is hardening
  - Links:
    - docs/audit/PR_559_ANTI_DUPLICATION_GUARDS.md
  - DoD:
    - GH Actions step scans iOS app Swift sources for forbidden patterns
    - Excludes fixtures/mocks
    - Documented in ios/AGENTS.md

- [ ] Optional: tighten guard false-positives (comment stripping / pattern tuning)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Reason: avoid guard flakiness if comments include examples
  - Links:
    - ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift
  - DoD:
    - Guard remains strict but avoids comment-only hits
    - CI remains deterministic

- [ ] Unify ShoppingListService / WeeklyPlanService under thin HTTP adapter (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (post PR-XXX)
  - Reason: ShoppingListService and WeeklyPlanService currently use URLSession directly with custom error enums, not aligned with thin HTTP adapter policy established in PR-XXX. BMIService was refactored to use APIClient/HTTPClient; other services should follow same pattern for consistency.
  - Links:
    - ios/PulsePlate/Services/ShoppingListService.swift
    - ios/PulsePlate/Services/WeeklyPlanService.swift
    - ios/PulsePlate/Networking/APIClient.swift (reference implementation)
    - docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md
  - DoD:
    - ShoppingListService uses APIClient (no direct URLSession)
    - WeeklyPlanService uses APIClient (no direct URLSession)
    - Custom error enums replaced with APIError from Networking layer
    - All services follow same thin adapter pattern
    - Tests updated to use HTTPClientProtocol stubs
    - No breaking changes to public APIs

- [ ] Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO; delete legacy BMIRequest/BMIResponse (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (post PR-XXX)
  - **Status:** 🔴 **Technical debt created in PR-XXX** — legacy compatibility shims added to unblock tests/compilation
  - Reason: UI layer (BMICalculatorViewModel, BMICalculatorScreen) still uses legacy BMIRequest/BMIResponse types. New thin adapter uses BMICalculateRequestDTO/BMICalculateResponseDTO. Migration deferred to separate PR to keep PR-XXX scope focused on transport layer only.
  - **Technical debt details (created in PR-XXX):**
    - `LegacyBMIServicing` protocol (lines 53-55 in BMIService.swift) — uses BMIRequest/BMIResponse instead of DTOs
    - `DefaultBMIService` class (lines 91-159 in BMIService.swift) — legacy implementation with direct URLSession, duplicates HTTP logic from HTTPClient/APIClient
    - `BMIServiceError` enum (lines 59-87 in BMIService.swift) — legacy error type, duplicates APIError functionality from Networking/APIError.swift
    - `BMICalculatorViewModel` (lines 6-35) — still uses LegacyBMIServicing, BMIRequest, BMIResponse, BMIServiceError
    - `MockBMIService` — updated to LegacyBMIServicing for test compatibility (should be BMIServicing after migration)
  - **Why deferred:** To avoid breaking existing UI code in transport-layer PR. UI migration is separate scope. Tests needed to compile/run, so legacy shims were added as temporary compatibility layer.
  - **Risk:** Code duplication (DefaultBMIService vs BMIService), two error types (BMIServiceError vs APIError), maintenance burden, potential confusion about which service to use.
  - Links:
    - ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift
    - ios/PulsePlate/Screens/BMICalculatorScreen.swift
    - ios/PulsePlate/Models/BMI/BMIRequest.swift (legacy, to be deleted)
    - ios/PulsePlate/Models/BMI/BMIResponse.swift (legacy, to be deleted)
    - ios/PulsePlate/Models/BMI/BMICalculateRequestDTO.swift (new)
    - ios/PulsePlate/Models/BMI/BMICalculateResponseDTO.swift (new)
    - ios/PulsePlate/Services/BMIService.swift (lines 48-159: legacy compatibility shims)
    - ios/PulsePlate/Networking/APIError.swift (canonical error type)
  - DoD:
    - BMICalculatorViewModel uses BMICalculateRequestDTO/BMICalculateResponseDTO
    - BMICalculatorViewModel uses APIError (not BMIServiceError)
    - BMICalculatorScreen uses new DTO types
    - Legacy BMIRequest.swift deleted
    - Legacy BMIResponse.swift deleted
    - LegacyBMIServicing protocol removed
    - DefaultBMIService class removed (replaced by BMIService)
    - BMIServiceError enum removed (replaced by APIError from Networking/)
    - MockBMIService updated to BMIServicing (not LegacyBMIServicing)
    - Error handling updated to use APIError (not BMIServiceError)
    - No breaking changes to public ViewModel API
    - Tests updated
    - No code duplication (single HTTP client path)

---

## P2 — Future (Low priority / research)
- (None currently)

---

**Last updated:** 2026-01-21 (after PR-560 + PR-561 merge)
**Maintainer:** @katsiaryna_kavaleuskaya
