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
  - Reason: iOS CI stability fixes (simulator selection, Xcode pinning)
  - Links:
    - docs/CONTEXT_HANDOFF_2026-01-21.md
  - DoD: ✅ Completed (iOS CI stable)

- [x] PR-561 Trivy suppression (CVE-2025-15281 glibc) (merged 2026-01-21)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-561
  - Status: ✅ Merged
  - Reason: Security suppression for unfixed upstream glibc CVE
  - Links:
    - docs/security/CVE-2025-15281-glibc.md
    - trivy/ignore-policy.rego
  - DoD: ✅ Completed (suppression with expiry date)

- [x] PR-563 Thin HTTP Adapter (iOS) — merged 2026-01-21
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-563
  - Status: ✅ Merged
  - Reason: unified thin transport layer for iOS client (no business logic)
  - Links:
    - docs/audit/PR_562_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/563>
  - DoD: ✅ Completed (iOS HTTPClient/APIClient/BMIService implemented)

- [x] PR-586 Web Thin HTTP Adapter — Guards
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-586
  - Status: ✅ Guards created, remediation merged via PR-590
  - Reason: Policy enforcement — guard tests to detect thin-client violations
  - Links:
    - docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/586>
  - DoD:
    - ✅ Guard tests created (`frontend/src/api/__tests__/thin-client-guards.test.ts`)
    - ✅ `frontend/AGENTS.md` updated with thin-client policy
    - 🔴 CI expected RED (guards expose 4 direct fetch violations)
    - Remediation tracked in PR-587

- [x] PR-587 Web Thin HTTP Adapter — Remediation (fix-green)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-590 (superseded PR-587/589)
  - Status: ✅ Superseded by PR-590 (merged)
  - Reason: Fix 4 direct fetch() violations detected by guards
  - Links:
    - docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md (violations list)
    - docs/audit/PR_587_WEB_THIN_HTTP_ADAPTER_REMEDIATION_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/590>
  - DoD: ✅ Completed
    - Migrate `features/plan/WeeklyPlanViewer.tsx:39` to use `fetchBlob()`
    - Migrate `features/shoplist/ShoplistPreview.tsx:109` to use `fetchBlob()`
    - Migrate `lib/shareFile.ts:108` to use `fetchBlob()`
    - Migrate `lib/sharedLinks.ts:21` to use `api()`
    - Guard tests pass (all 4 violations fixed)
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
  - Target PR: TBD (post PR-563)
  - Reason: ShoppingListService and WeeklyPlanService currently use URLSession directly with custom error enums, not aligned with thin HTTP adapter policy established in PR-563. BMIService was refactored to use APIClient/HTTPClient; other services should follow same pattern for consistency.
  - Links:
    - ios/PulsePlate/Services/ShoppingListService.swift
    - ios/PulsePlate/Services/WeeklyPlanService.swift
    - ios/PulsePlate/Networking/APIClient.swift (reference implementation)
    - docs/audit/PR_562_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md (originally for PR-562, applies to PR-563)
  - DoD:
    - ShoppingListService uses APIClient (no direct URLSession)
    - WeeklyPlanService uses APIClient (no direct URLSession)
    - Custom error enums replaced with APIError from Networking layer
    - All services follow same thin adapter pattern
    - Tests updated to use HTTPClientProtocol stubs
    - No breaking changes to public APIs

- [ ] Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO; delete legacy BMIRequest/BMIResponse (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (post PR-563)
  - **Status:** 🔴 **Technical debt created in PR-563** — legacy compatibility shims added to unblock tests/compilation
  - Reason: UI layer (BMICalculatorViewModel, BMICalculatorScreen) still uses legacy BMIRequest/BMIResponse types. New thin adapter uses BMICalculateRequestDTO/BMICalculateResponseDTO. Migration deferred to separate PR to keep PR-563 scope focused on transport layer only.
  - **Technical debt details (created in PR-563):**
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

- [x] PR-566 (Phase 2): Coordinator cleanup and deduplication — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-566
  - Status: ✅ Merged
  - Reason: Agent coordinator deduplication (removed capability duplication)
  - Links:
    - docs/audit/PR_566_COORDINATOR_CLEANUP_AUDIT.md
  - DoD: ✅ Completed (coordinator references agent files instead of duplicating)

- [ ] Fix test skips/xfails (batch)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (separate PRs per fix, post PR-585 inventory)
  - Priority: P1
  - Area: backend / tests
  - Finding Type: skip/xfail
  - Locations:
    - `tests/test_bmi_visualization.py:523` — xfail (test isolation issue)
    - `tests/test_app_branching_and_errors.py:185` — xfail (module reload)
    - `tests/test_repo_policy_guards.py:85` — skip (sys.modules cleanup)
  - Reason: Technical debt from remediation; tests disabled to unblock CI
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
    - docs/audit/BACKEND_XFAILED_TESTS_AUDIT.md
  - DoD:
    - Each xfail/skip either fixed or removed (if obsolete)
    - Tests pass without xfail markers
    - CI green

- [ ] NutritionData.swift: migrate to APIClient (iOS thin-client violation)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (post PR-563)
  - Priority: P1
  - Area: iOS
  - Finding Type: thin-client violation
  - Location: `ios/PulsePlate/Models/NutritionData.swift:60`
  - Reason: Uses `URLSession.shared.data` directly instead of APIClient
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
    - docs/audit/PR_562_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md
  - DoD:
    - NutritionData uses APIClient (not direct URLSession)
    - Consistent error handling via APIError
    - No dual-path networking

- [ ] OpenAPI: Add response schema for `/api/v1/export/sign`
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: backend / OpenAPI
  - Finding Type: schema-debt
  - Location: `app/routers/export.py` (sign_export_link endpoint)
  - Reason: Response type is `{ [key: string]: unknown }` in generated schema. Frontend uses hand-written `SignedLinkResponse` type. Should define Pydantic response model for proper OpenAPI generation.
  - Links:
    - frontend/src/lib/sharedLinks.ts (hand-written type)
    - frontend/src/api/schema.ts:4783 (generic dict response)
  - DoD:
    - Backend defines `SignedLinkResponse` Pydantic model
    - OpenAPI regenerated with proper schema
    - Frontend uses generated type from `schema.ts`

- [ ] Web Guards: Extract config constants to shared module
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: frontend / guards
  - Finding Type: improvement (Sourcery PR-592)
  - Location: `frontend/src/api/__tests__/thin-client-guards.test.ts`
  - Reason: FORBIDDEN_PATTERNS/SCAN_DIRS/EXCLUDE_PATTERNS should be shared between guards and AGENTS.md to prevent policy drift
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/592> (source PR)
    - Sourcery comment on PR-592
  - DoD:
    - Config extracted to shared module
    - Guards import config
    - AGENTS.md references canonical source

- [ ] Web Guards: Improve inline block comment parsing
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: frontend / guards
  - Finding Type: improvement (Sourcery PR-592)
  - Location: `frontend/src/api/__tests__/thin-client-guards.test.ts`
  - Reason: Current `isLineInComment` may not handle inline `/* ... */` on same line correctly
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/592> (source PR)
    - Sourcery comment on PR-592
  - DoD:
    - Stricter inline comment parsing
    - Test cases for edge cases

- [ ] API Tiers database lookup implementation
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P1
  - Area: backend
  - Finding Type: TODO/FIXME
  - Locations:
    - `app/middleware/api_tiers.py:146` — TODO: Implement database lookup for production
    - `app/middleware/api_tiers.py:284` — TODO: Implement database lookup
  - Reason: Currently uses env-based tier detection; needs DB lookup for production
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
  - DoD:
    - Database lookup implemented when SUBSCRIPTION_DB_ENABLED=true
    - Fallback to env-based detection when DB unavailable
    - Tests cover both paths

- [ ] Security suppression expiry monitoring
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: N/A (ongoing)
  - Priority: P1
  - Area: security
  - Finding Type: policy exception
  - Locations:
    - `trivy/ignore-policy.rego` — Suppression expires: 2026-03-01
    - `.trivyignore` — CVE-2026-0861 expires: 2026-03-01
  - Reason: Upstream glibc CVEs unfixed; suppressions have expiry dates
  - Links:
    - docs/security/CVE-2026-0861-glibc.md
    - docs/security/CVE-2025-15281-glibc.md
  - DoD:
    - Weekly monitoring for upstream fixes
    - Remove suppressions when fixed versions available
    - Update base image when fixes land

---

## P2 — Future (Low priority / research)

- [ ] Test skips cleanup (low priority batch)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: backend / tests
  - Finding Type: skip/xfail
  - Locations:
    - `tests/test_level_es.py:13` — pytestmark skip (investigate)
    - `tests/test_app_coverage_unit_combined.py:81,86` — skip (interpret_group/estimate_level removed)
    - `tests/test_app_plate_helpers.py:145` — xfail (investigate)
    - `tests/test_update_manager_fixed.py:129` — skip (path attribute issues)
    - `tests/test_food_apis_coverage_errors.py:303,331,351,396,416,437` — 6x skip (mock issues)
  - Reason: Lower priority; tests for removed/legacy functionality
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
  - DoD:
    - Each test either fixed, updated, or removed if obsolete
    - No unexplained skips remain

- [ ] Backend TODO cleanup (i18n, telemetry)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: backend
  - Finding Type: TODO/FIXME
  - Locations:
    - `core/business_bayesian_analyzer.py:145,1067` — TODO: telemetry/metrics
    - `legacy_app.py:1985` — TODO: Read version from pyproject.toml
    - `app/routers/premium_week.py:97,127` — TODO: i18n support
    - `app/routers/pro.py:152,182,529,537` — TODO: i18n, dedup, meal logging
  - Reason: Polish/improvement items, not blocking
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
  - DoD:
    - TODOs addressed or converted to tracked issues
    - No stale TODOs without tracking

- [ ] Deprecated endpoint cleanup (post-migration)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (v2.0 timeline)
  - Priority: P2
  - Area: backend / API
  - Finding Type: deprecated/alias
  - Locations:
    - `app/routers/bmi_pro.py:158` — deprecated POST /api/v1/pro/bmi
    - `app/routers/bmi_pro_legacy_alias.py` — deprecated /api/v1/bmi/pro
    - `app/routers/premium_week.py:179` — deprecated /api/v1/premium/plan/week-flexible
    - `app/routers/vip.py:706` — deprecated legacy VIP endpoint
  - Reason: Legacy aliases; remove after client migration complete
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
    - docs/contracts/PRODUCT_TIER_MAP.md
  - DoD:
    - All clients migrated to canonical endpoints
    - Deprecated endpoints removed
    - OpenAPI updated (no deprecated paths)

- [x] PR-570 (Phase 3): Agent index + model selection rationale — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-570
  - Status: ✅ Merged
  - Links:
    - docs/audit/PR_567_AGENT_INDEX_AUDIT.md
    - docs/agents/index.md

---

**Last updated:** 2026-01-25 (PR-585: Backlog Sweep Audit — inventory complete)
**Maintainer:** @katsiaryna_kavaleuskaya
