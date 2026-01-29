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

- [x] PR-611 AI Insight Safety & Error Hygiene (merged 2026-01-28)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-611
  - Status: ✅ Merged
  - Reason: P0 safety — ensure insight endpoints never leak internal errors (ImportError, provider.generate exceptions) and return safe 503 responses with sanitized detail messages. Also enforce `response_model=InsightResponse` contract.
  - Links:
    - docs/audit/PR_611_INSIGHT_SAFETY_ERROR_HYGIENE_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/611>
  - DoD: ✅ Completed
    - ✅ Import-failure returns 503 with safe detail (no "boom" leak)
    - ✅ Provider.generate exceptions return 503 with safe detail (no raw exception leak)
    - ✅ All insight endpoints use `response_model=InsightResponse`
    - ✅ Tests use attribute access (`out.provider`, `out.insight`) not dict keys
    - ✅ Import-failure test is deterministic (`FEATURE_INSIGHT=true` enforced)
    - ✅ CI green (all checks pass)
    - ✅ Post-merge verification passed (13 tests, OpenAPI sync)

- [x] PR-616 Thin-proxy cleanup (helpers-1) — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-616
  - Status: ✅ Merged
  - Priority: P0
  - Branch: `chore/p1-thin-proxy-cleanup-helpers-1-new`
  - Reason: Architectural cleanup — move helpers out of `legacy_app.py` to restore "thin proxy only" invariant. Steps 1/2/3/4/6/7 complete (scheduler wrappers, utility helpers, feature flags, nutrition wrappers, fingerprint, dead BMI helpers). Step 5 (DB fallback) deferred to TP2.
  - Links:
    - docs/audit/PR_THIN_PROXY_CLEANUP_AUDIT.md
    - docs/pr/PR_THIN_PROXY_CLEANUP_PLAN.md
  - DoD:
    - ✅ Steps 1/2/3/4/6/7 complete (helpers moved to canonical modules)
    - ✅ Step 5 explicitly deferred to TP2 (DB fallback helpers remain in `legacy_app.py`)
    - ✅ `pytest -q` green (0 FAILED/ERROR)
    - ✅ Guard tests pass (`test_repo_policy_guards.py`, `test_no_legacy_bmi_helpers_request_path.py`)
    - ✅ No "tail" imports (`from app import normalize_flags|waist_risk` removed from tests)
    - ✅ Tests updated to use canonical functions (`core.bmi.engine`, `core.bmi.risk`)
    - ✅ All actionable items fixed (CodeRabbit/Cubic/Sourcery)
    - ✅ PR merged

- [x] PR-TP2 Thin-proxy cleanup (DB fallback) — Done (PR #617 open)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #617 (branch: `refactor/tp2-db-fallback`)
  - Status: ✅ Done (ready to merge after CI green)
  - Reason: High-risk cleanup — move DB fallback helpers from `legacy_app.py` to canonical module. Completed audit → plan → Phase 1 (extract) → Phase 2 (rewire) → Phase 3 (tests) → policy docs.
  - Links:
    - PR #617
    - docs/pr/PR_TP2_DB_FALLBACK_PLAN.md
    - docs/audit/PR_TP2_DB_FALLBACK_AUDIT.md
    - docs/CONTEXT_HANDOFF_2026-01-28.md
  - Preconditions:
    - ✅ TP1 merged (helpers-1 cleanup complete)
  - DoD:
    - ✅ DB fallback in `core/db/fallback.py` (single source of truth)
    - ✅ `legacy_app.py` thin proxy only (no DB fallback logic)
    - ✅ Tests rebound to `core.db.fallback`; guard tests pass
    - ✅ OpenAPI unchanged; AGENTS.md + BACKLOG_LEDGER updated
    - [ ] CI green on PR #617 → merge → post-merge sanity

---

## P1 — Improvements (Optional / polish)

- [ ] core/db.py vs core/db/ collision cleanup (post-TP2)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD
  - Reason: TP2 introduced `core/db/` package alongside `core/db.py` (file); Python resolves `core.db` to the package. Re-exports and guard exception are documented. Follow-up: stabilize module layout (e.g. rename `core/db.py` or consolidate) and remove guard exception when safe.
  - Links: AGENTS.md (DB fallback policy), tests/test_repo_policy_guards.py (core/db/ exception)
  - DoD: Module layout stabilized; guard exception removed or justified long-term; no new runtime behavior.

- [ ] Remove Trivy suppression for gpgv CVE (CVE-2026-24883)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD (follow-up after upstream fix)
  - Reason: Trivy reports `gpgv` vulnerability (CVE-2026-24883) with no fixed version available as of 2026-01-28; we suppress via `trivy/ignore-policy.rego` with expiry enforcement to keep Trivy's signal actionable. Should remove when Debian publishes a patched package / Trivy metadata updates.
  - Links:
    - `trivy/ignore-policy.rego` (rule for CVE-2026-24883)
    - `docs/security/CVE-2026-24883-gpgv.md`
    - `.github/workflows/trivy.yml`
  - DoD:
    - Debian bookworm publishes a fixed `gpgv` package (or Trivy publishes fixed-version metadata)
    - Remove CVE-2026-24883 suppression from `trivy/ignore-policy.rego`
    - Remove `docs/security/CVE-2026-24883-gpgv.md` (or mark as resolved)
    - Trivy Code Scanning alerts remain closed on `main`

- [x] Resolve CVE-2026-24882 Trivy alert (accepted risk) (merged 2026-01-28)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-615 (merged)
  - Status: ✅ Suppression added; monitoring until 2026-04-28 (expiry date)
  - Reason: GitHub alert #515 reports CVE-2026-24882 (gpgv tpm2daemon buffer overflow) for installed version 2.2.40-1.1. Debian tracker confirms bookworm is vulnerable (no fixed version available). Suppressed as accepted risk (no attack surface: runtime does not invoke gpgv/tpm2daemon, no TPM2-backed keys used).
  - Links:
    - `trivy/ignore-policy.rego` (rule for CVE-2026-24882)
    - `docs/security/CVE-2026-24882-gpgv.md`
    - GitHub alert #515
    - `.github/workflows/trivy.yml`
    - PR-615 (merged)
  - DoD:
    - ✅ Suppression added in `trivy/ignore-policy.rego` with expiry 2026-04-28
    - ✅ Security doc created (`docs/security/CVE-2026-24882-gpgv.md`)
    - 🔄 Monitor: GitHub alert #515 should auto-resolve after next Trivy scan on `main`
    - 🔄 Follow-up (after 2026-04-28 or when fixed): Remove suppression when Debian bookworm publishes fixed `gpgv` package (≥ 2.5.17 or backported fix), OR Trivy metadata includes fixed version

- [ ] Move insight redaction/import helpers out of legacy_app.py
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD
  - Reason: Codex actionable — keep legacy_app thin proxy only. Move `_redact_rag_context_for_insight` and `_load_llm_get_provider` to canonical module (`core/insight/`) to maintain AGENTS invariant. Follow-up from PR-611.
  - Links:
    - docs/audit/PR_611_INSIGHT_SAFETY_ERROR_HYGIENE_AUDIT.md
    - PR-611 (merged 2026-01-28)
  - Preconditions (already true as of PR-611):
    - `_redact_rag_context_for_insight` lives in `core/insight/safety.py`
  - DoD:
    - Move `_load_llm_get_provider` to canonical module (not `legacy_app.py`)
    - `legacy_app.py` contains only thin proxies (no business/import helpers)
    - Tests pass
    - OpenAPI unchanged

- [ ] PR-595 iOS Thin HTTP Adapter Audit
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-595
  - Status: 🟡 In progress (draft)
  - Reason: CodeRabbit actionable — if not recorded in ledger, it does not exist. Audit-first for iOS networking layer (dual-path HTTP, legacy services, DTO drift) and deterministic remediation plan.
  - Links:
    - docs/audit/PR_595_IOS_THIN_HTTP_ADAPTER_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/595>
  - DoD:
    - Evidence captured for dual-path networking (`file:line → transport`)
    - Legacy services and direct HTTP entry points enumerated
    - DTO/contract drift documented at network boundary
    - Remediation plan defined (PR-596 scope)

- [x] PR-596 merged: iOS thin HTTP adapter remediation (merged 2026-01-26)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-596
  - Status: ✅ Merged
  - Reason: Consolidate iOS networking under a single thin transport (`APIClient`) and eliminate direct HTTP calls outside transport layer.
  - Links:
    - docs/audit/PR_595_IOS_THIN_HTTP_ADAPTER_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596>
  - DoD:
    - All services use `APIClient` (no direct `URLSession` outside transport layer)
    - No direct HTTP in non-transport layers (models/view models/views/services)
    - DTO boundary aligned with canonical backend contracts
    - Tests/guards pass
  - Notes (post-merge):
    - Services/UI: no direct URLSession
    - APIError: transport vs HTTP
    - snake_case decoder parity
    - emptyResponse semantics
    - unknown vs transport

- [ ] Stabilize/restore PlateViewTests in CI (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (separate from PR-559)
  - Priority: P1
  - Reason: PlateViewTests were unstable historically; UI tests bundle-load is now fixed, but PlateViewTests stability + CI inclusion remains open.
  - Links:
    - ios/PulsePlateTests/PlateViewTests.swift
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/607>
  - DoD:
    - PlateViewTests stabilized (no flaky failures)
    - PlateViewTests included in CI signal (job or explicit `-only-testing` list)
    - CI green with PlateViewTests included

- [x] PR-607 merged: iOS UITests bundle load fix + CI UI smoke (merged 2026-01-27)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-607
  - Status: ✅ Merged
  - Reason: Restore UI tests build-product correctness (bundle contains executable) and add dedicated `ios-ui-smoke` CI signal.
  - Links:
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/607>
  - DoD: ✅ Completed
    - `PulsePlateUITests.xctest` contains executable (no Code=4 / exit 65 before tests execute)
    - CI `ios-ui-smoke` job runs minimal UI smoke

- [x] PR-608 merged: audit post-merge evidence stamp (merged 2026-01-27)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-608
  - Status: ✅ Merged
  - Reason: Record post-merge verification evidence (main SHA + minimal stdout excerpt) for Q2b DoD closure.
  - Links:
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/608>
  - DoD: ✅ Completed

- [ ] P1 (postponed): CI iOS workflow dedup (extract shared helpers / composite action)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD
  - Reason: Avoid drift between `ios-tests` and `ios-ui-smoke` jobs (Xcode pinning, destination selection, boot logic, xcodebuild wrapper). Requested in PR-607 review; deferred to keep remediation PR scope tight.
  - Links:
    - .github/workflows/ci.yml
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md
  - DoD:
    - One shared implementation for destination selection + bootstatus gating + xcodebuild wrapper (script or composite action)
    - Both iOS jobs reuse the same logic (no duplicated Python snippets)
    - CI remains deterministic (UDID-only destination, no `OS=latest`)

- [ ] Standardize audit verification blocks (require minimal stdout excerpt)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: TBD
  - Reason: Audit items labeled “Verified” must include minimal observed stdout evidence (1–3 lines) to remain reproducible and reviewable.
  - Links:
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md (section F)
    - AGENTS.md (Verification-audit rule)
  - DoD:
    - Add a short, canonical checklist line for audit PRs: include 1–3 raw stdout lines + exit code for each key verification command
    - No scope creep into runbook-level detail

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

- [x] Unify ShoppingListService / WeeklyPlanService under thin HTTP adapter (iOS) — completed in PR-596 (merged 2026-01-26)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-596
  - Status: ✅ Merged
  - Reason: Remove direct URLSession usage from services; consolidate under APIClient/HTTPClient seam.
  - Links:
    - ios/PulsePlate/Services/ShoppingListService.swift
    - ios/PulsePlate/Services/WeeklyPlanService.swift
    - ios/PulsePlate/Networking/APIClient.swift (reference implementation)
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596>
  - DoD:
    - ShoppingListService uses APIClient (no direct URLSession)
    - WeeklyPlanService uses APIClient (no direct URLSession)
    - Custom error enums replaced with APIError from Networking layer
    - All services follow same thin adapter pattern
    - Tests updated to use HTTPClientProtocol stubs
    - No breaking changes to public APIs

- [x] Migrate BMICalculatorViewModel + Screen to BMICalculate*DTO; delete legacy BMIRequest/BMIResponse (iOS) — completed in PR-596 (merged 2026-01-26)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-596
  - Status: ✅ Merged
  - Reason: Align iOS BMI UI/service to canonical BMICalculate*DTO contract and APIError.
  - Links:
    - ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift
    - ios/PulsePlate/Screens/BMICalculatorScreen.swift
    - ios/PulsePlate/Models/BMI/BMICalculateRequestDTO.swift (new)
    - ios/PulsePlate/Models/BMI/BMICalculateResponseDTO.swift (new)
    - ios/PulsePlate/Services/BMIService.swift
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596>
  - DoD:
    - BMICalculatorViewModel uses BMICalculateRequestDTO/BMICalculateResponseDTO
    - BMICalculatorViewModel uses APIError (not BMIServiceError)
    - BMICalculatorScreen uses new DTO types
    - Legacy BMIRequest.swift deleted
    - Legacy BMIResponse.swift deleted
    - BMI service is BMIServicing (thin adapter over APIClient)
    - Error handling updated to use APIError (incl. unknown vs transport)
    - Tests updated

- [x] PR-566 (Phase 2): Coordinator cleanup and deduplication — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-566
  - Status: ✅ Merged
  - Reason: Agent coordinator deduplication (removed capability duplication)
  - Links:
    - docs/audit/PR_566_COORDINATOR_CLEANUP_AUDIT.md
  - DoD: ✅ Completed (coordinator references agent files instead of duplicating)

- [x] Fix test skips/xfails (batch) — completed in PR-602
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-602
  - Status: ✅ Completed (remediated-by-removal for invalid/non-contract tests + traced skip)
  - Priority: P1
  - Area: backend / tests
  - Finding Type: skip/xfail
  - Locations:
    - `tests/test_bmi_visualization.py:523` — xfail → **removed**
      - Reason: deterministic failure under `--runxfail` (404); test expected a legacy route to be mounted.
        Classified in PR-600 as **invalid test / route wiring mismatch** (non-contract).
    - `tests/test_app_branching_and_errors.py:185` — xfail → **removed**
      - Reason: reload-dependent internal symbol assertions (`importlib.reload(app)` → symbols become `None`) are not a stable contract.
        Classified in PR-600 as **invalid / environment-dependent assumption**.
    - `tests/test_repo_policy_guards.py:85` — skip (sys.modules cleanup) → **kept skipped**, but reason now explicitly tied to ledger + PR-600 (no behavior change).
  - Reason: Technical debt from remediation; tests disabled to unblock CI
  - Links:
    - docs/audit/PR_600_QUALITY_TESTS_AUDIT.md
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
    - docs/audit/BACKEND_XFAILED_TESTS_AUDIT.md
  - DoD:
    - Each xfail/skip either fixed or removed (if obsolete)
    - Tests pass without xfail markers
    - CI green

- [x] NutritionData.swift: migrate to APIClient (iOS thin-client violation) — completed in PR-596 (merged 2026-01-26)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-596
  - Status: ✅ Merged
  - Priority: P1
  - Area: iOS
  - Finding Type: thin-client violation
  - Location: `ios/PulsePlate/Models/NutritionData.swift:60`
  - Reason: Direct URLSession usage in model layer violated thin-client transport policy.
  - Links:
    - ios/PulsePlate/Models/NutritionData.swift
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/596>
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

**Last updated:** 2026-01-28 (PR-TP1: Add thin-proxy cleanup TP1/TP2 ledger entries)
**Maintainer:** @katsiaryna_kavaleuskaya
