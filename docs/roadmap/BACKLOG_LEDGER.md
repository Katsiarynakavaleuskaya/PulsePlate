<!-- markdownlint-disable MD013 -->
# Backlog Ledger (Canonical)

**Purpose:** single source of truth for postponed / follow-up work.
If it is not recorded here — it does not exist.

**Language policy:** Primary language: English. Russian details allowed in linked design/analysis docs for clarity, but backlog entries must include English summary/translation for maintainability and tooling compatibility.

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

- [x] P0: Import determinism for app-level tests (remove skip fallback)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-729
  - Status: ✅ Merged (PR-729, 2026-02-13)
  - Area: backend / tests
  - Finding Type: quality / determinism
  - Locations:
    - `tests/test_api.py:343` — guard test enforces "fail, not skip" policy
    - `tests/test_api.py:346` — marker check prevents reintroducing
      `pytest.skip("App import failed unexpectedly")`
  - Reason: Import determinism is a foundation invariant. Skipping app import failures masks CI and runtime risks.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `AGENTS.md:58`
    - `AGENTS.md:64`
  - Evidence (2026-02-13):
    - `pytest -q tests/test_api.py -rs` -> `22 passed`, `0 skipped`
    - `rg -n "SKIPPED \\[4\\]|App import failed unexpectedly" -S tests` -> no matches
  - DoD:
    - No skip fallback for app import in `tests/test_api.py`
    - Import path uses deterministic seams (no `builtins.__import__` patching)
    - The 4 previously skipped import tests execute (pass/fail, not skip)
    - `make verify` passes in PR-729

- [x] PR-653 P0 Welcome onboarding gate (iOS-only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-653
  - Status: ✅ Merged (PR-653, 2026-02-06)
  - Reason: Store readiness — ensure deterministic first-run value framing with a single entry gate (`has_seen_welcome_v1`) before `RootTabs()`.
  - Links:
    - docs/audit/PR_653_P0_WELCOME_ONBOARDING_4SCREENS_AUDIT.md
    - Follow-up: PR-678 (tighten to 2 screens: Value + Usage)
  - DoD:
    - iOS entrypoint gates `RootTabs()` via `WelcomeGateView`
    - `@AppStorage("has_seen_welcome_v1")` persists completion (welcome shown once)
    - RU/EN/ES strings ship for `onboarding.welcome.*`
    - `make ios-test` passes

- [x] iOS: Tighten first-launch onboarding to Value + Usage (2 screens)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0-B (release readiness)
  - Target PR: PR-678
  - Status: ✅ Merged (PR-678, 2026-02-07)
  - Reason: P0-B requires a minimal onboarding (≥2 screens). Keep the existing first-launch gate and tighten the flow to the two essential screens (Value + Usage) without adding networking/paywall/analytics.
  - Links:
    - `ios/PulsePlate/PulsePlateApp.swift`
    - `ios/PulsePlate/Welcome/WelcomeGateView.swift`
    - `ios/PulsePlate/Welcome/WelcomeFlowView.swift`
    - docs/audit/PR_678_IOS_ONBOARDING_VALUE_USAGE_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/678>
  - DoD:
    - On first launch, onboarding shows before `RootTabs()` (gate remains at app entry)
    - On completion, onboarding is not shown again (`has_seen_welcome_v1` persists)
    - Onboarding is exactly 2 screens (Value + Usage)
    - RU/EN/ES strings updated for the 2 screens
    - `make ios-test` passes
- [x] iOS: Remove placeholder PRO key fallback and implement release-safe key storage
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (release safety)
  - Target PR: PR-656
  - Status: ✅ Merged (PR-656, 2026-02-06)
  - Reason: `ProKeyProvider` previously contained a placeholder fallback (`test_pro_key`) in DEBUG. This is not release-safe and can mask missing-key flows in development and tests.
  - Links:
    - `ios/PulsePlate/Services/ProKeyProvider.swift`
    - `ios/PulsePlate/Services/KeychainStore.swift`
    - `docs/IOS_API_INTEGRATION.md`
  - DoD:
    - No placeholder key strings are returned by any provider (dev or prod)
    - Key retrieval uses a secure source (Keychain-backed or explicit developer-only injection that cannot ship)
    - Missing-key path is explicit and testable (UI/service fails with clear error, not silent fallback)
    - iOS tests updated / added for missing-key behavior (deterministic)

- [x] iOS: Guard test forbids placeholder API keys in app sources
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (release safety)
  - Target PR: PR-657
  - Status: ✅ Merged (PR-657, 2026-02-06)
  - Reason: Prevent accidental shipping of placeholder keys like `test_pro_key` in iOS sources; enforce via CI.
  - Links:
    - `ios/PulsePlate/Services/ProKeyProvider.swift`
    - `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift` (existing guard pattern)
  - DoD:
    - A deterministic guard/unit test fails CI if placeholder key strings appear in `ios/PulsePlate/**`
    - Test excludes fixtures/mocks as needed (no false positives)
    - Documented allowlist policy (if any) in `ios/AGENTS.md`

- [x] Backend: Fix deprecated `/api/nutrition/{date_str}` legacy alias to enforce `require_pro_tier` (auth bypass risk)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (security)
  - Target PR: PR-664
  - Status: ✅ Merged (PR-664, 2026-02-07)
  - Reason: `legacy_app.py` implements `/api/nutrition/{date_str}` as a legacy alias and uses `Depends(api_key_header)` (header extraction only), then calls `app/routers/pro.py:get_daily_nutrition()` directly. This bypasses the `require_pro_tier` dependency (tier validation) and does not pass the API key into any guard, risking unauthorized access if the alias is reachable.
  - Decision:
    - Preferred outcome: remove deprecated alias entirely (keep only canonical `GET /api/v1/pro/nutrition/daily`).
    - Fallback (if removal is not possible now): keep alias but explicitly enforce `require_pro_tier` in the alias handler + deterministic 401/403/200 tests.
  - Links:
    - docs/audit/PR_654_BACKEND_LEGACY_NUTRITION_ALIAS_PRO_GUARD_AUDIT.md
    - `legacy_app.py` (`/api/nutrition/{date_str}` legacy alias)
    - `app/routers/api_key.py` (`api_key_header`)
    - `app/middleware/api_tiers.py` (`require_pro_tier`)
    - `app/routers/pro.py` (`GET /api/v1/pro/nutrition/daily`)
    - `ios/PulsePlate/Models/NutritionData.swift` (client currently uses legacy path)
  - DoD:
    - Alias either removed or explicitly enforces PRO tier guard (no auth bypass)
    - Deterministic tests prove 401/403/200 behavior for alias path
    - Docs explicitly mark alias as deprecated and forbidden as client SoT (iOS uses canonical `/api/v1/pro/nutrition/daily`)
    - OpenAPI visibility matches deprecation policy (deprecated/hidden as appropriate)

- [x] Docs: Canonicalize iOS API integration guide to current Networking SoT
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (docs correctness)
  - Target PR: PR-669
  - Status: ✅ Merged (PR-669, 2026-02-07)
  - Reason: Existing `docs/IOS_API_INTEGRATION.md` was outdated and instructed creating a parallel URLSession-based transport layer; this conflicts with thin-client policies and current `ios/PulsePlate/Networking/*` SoT.
  - Links:
    - PR-669
    - `docs/audit/IOS_DOCS_DRIFT_AUDIT_2026-02-07.md`
    - `docs/IOS_API_INTEGRATION.md`
    - `ios/PulsePlate/Networking/APIClient.swift`
    - `ios/PulsePlate/Networking/HTTPClient.swift`
  - DoD:
    - Doc lists repo SoT paths and rules (no new transport)
    - Includes “how to add endpoint” recipe aligned with existing protocols/tests
    - Future items (IAP/receipt/keychain) point to ledger items (no mixed scopes)

- [x] Docs: Refresh iOS roadmap to AS-IS / NEXT ACTIONS (repo-truth)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (docs correctness)
  - Target PR: PR-669
  - Status: ✅ Merged (PR-669, 2026-02-07)
  - Reason: `docs/roadmap/IOS_ROADMAP.md` still described “when iOS development resumes”; iOS is active (RootTabs, Networking SoT, guard tests).
  - Links:
    - PR-669
    - `docs/audit/IOS_DOCS_DRIFT_AUDIT_2026-02-07.md`
    - `docs/roadmap/IOS_ROADMAP.md`
    - `ios/PulsePlate/Views/RootTabs.swift`
    - `ios/PulsePlate/Networking/*`
  - DoD:
    - AS-IS section reflects current entrypoint, navigation, networking, guards, localization
    - NEXT ACTIONS list only real follow-ups (P0/P1) and points to ledger items

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

- [x] PR-TP2 Thin-proxy cleanup (DB fallback) — merged 2026-01-29 (PR #617)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #617 (`refactor/tp2-db-fallback`)
  - Status: ✅ Merged (squash merge SHA: 19e0b8f5; 2026-01-29)
  - Reason: High-risk cleanup — move DB fallback helpers from `legacy_app.py` to canonical module. Original target `core/db/fallback.py` caused `core.db` module/package collision in CI; amended to `core/db_fallback.py`.
  - Links:
    - PR #617
    - docs/pr/PR_TP2_DB_FALLBACK_PLAN.md
    - docs/audit/PR_TP2_DB_FALLBACK_AUDIT.md
    - docs/CONTEXT_HANDOFF_2026-01-29.md
  - Preconditions:
    - ✅ TP1 merged (helpers-1 cleanup complete)
  - DoD:
    - ✅ DB fallback in `core/db_fallback.py` (single source of truth; no package collision)
    - ✅ `legacy_app.py` thin proxy only (no DB fallback logic)
    - ✅ Tests rebound to `core.db_fallback`; guard tests pass (no guard exception)
    - ✅ OpenAPI unchanged; AGENTS.md + BACKLOG_LEDGER updated
    - ✅ CI green on PR #617 → merge → post-merge sanity

- [x] PR-619 DB fallback canonical API in `legacy_app.py` — merged 2026-01-30
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintenance)
  - Target PR: PR #619
  - Status: ✅ Merged
  - Reason: Align `legacy_app.py` with DB fallback policy — no direct read/write of `_db_fallback_active` outside `core/db_fallback.py`; use `is_fallback_active()` and `clear_fallback_active()`.
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/619>
  - DoD:
    - ✅ No direct `_db_fallback_active` in `legacy_app.py`
    - ✅ Guards + tests green; CI green
  - Next after merge: P0 rate-limiting for LLM endpoints

- [x] PR-623 SQLite xdist dual-engine leak + hermetic tests + SoT reset — merged 2026-01-30
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (infra)
  - Target PR: PR #623 (`fix/sqlite-xdist-threading-engine-sot`)
  - Status: ✅ Merged
  - Reason: Fix SQLite xdist dual-engine leak: single-engine SoT reset in fixture, hermetic tests when mutating env, NullPool gated to test/xdist via `make_url`, diff-coverage tests for protective branches. 97% threshold unchanged.
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/623>
    - docs/CONTEXT_HANDOFF_2026-01-30.md
  - DoD:
    - ✅ SoT reset in fixture; hermetic engine reuse tests
    - ✅ NullPool only for file-based SQLite in test/xdist
    - ✅ diff-coverage tests for `_get_sqlite_poolclass` branches
    - ✅ CI green; guards pass

- [x] PR-627 xdist SQLite race conditions (table exists + no-table errors) — merged 2026-02-01
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (infra)
  - Target PR: PR #627 (`fix/p1-sqlite-engine-sot`)
  - Status: ✅ Merged
  - Reason: Fix two independent xdist race conditions: (1) in-memory DB leak from `test_init_db` (no teardown → "no such table" in API tests), (2) fixture ordering race (duplicate `init_db()` + redundant `create_all()` → "table already exists").
  - Links:
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/627>
    - docs/audit/PR_617_SQLITE_ENGINE_SOT_NIGHTLY_AUDIT.md
    - docs/CONTEXT_HANDOFF_2026-01-30.md
  - DoD:
    - ✅ Fix 1: `test_init_db` + `try/finally` cleanup (restore env + `reset_db_for_tests()`)
    - ✅ Fix 2: Explicit fixture dependency + remove redundant `create_all()`
    - ✅ Tests green under xdist -n 2 (targeted subset + full nutrition_log suite)
    - ✅ `make test-fast` passes (exit_code 0)
    - ✅ SoT guard test remains green (no regression)
    - ✅ CI green; PR merged

- [x] P0 CRITICAL: Rate-limiting for LLM endpoints (prevent $72k/month cost attack)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (CRITICAL security)
  - Target PR: PR-639 (supersedes PR-628)
  - Status: ✅ Done (superseded by PR-639)
  - Reason: Close PR-628 via PR-639: audit drift fixed (runtime wiring + proxy-aware CIDR client key + deterministic tests are present) and 429 OpenAPI schema standardized for VIP export; OpenAPI artifacts regenerated.
  - Links:
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (Rate-limiting section)
    - docs/audit/AUDIT_GAPS_ANALYSIS.md (LLM cost control gap)
    - core/insight/analysis_insights.md ($72k/month potential abuse)
    - docs/audit/PR_628_RATE_LIMIT_LLM_EXPORTS_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/628>
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/639>
  - DoD:
    - ✅ Rate-limiting wired in runtime (SlowAPI middleware + 429 handler)
    - ✅ Proxy-aware key function supports trusted proxies with CIDR + CF/XFF precedence
    - ✅ `@limit_if_available(RATE_LIMIT_INSIGHT)` on `/api/v1/insight` + `/insight`
    - ✅ `@limit_if_available(RATE_LIMIT_EXPORTS)` on export endpoints (plan/shoplist/VIP export + legacy demo exports when enabled)
    - WebSocket: N/A (no endpoints found; see WebSocket investigation item)
    - ✅ Tests verify rate-limiting works (deterministic 200→429)
    - Cost tracking added (token usage, API calls)

### P0 Move LLM insight to VIP tier

- [x] P0 CRITICAL: Move LLM insight to VIP tier (prevent FREE tier abuse)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (CRITICAL security)
  - Target PR: PR-640 (runtime), PR-646 (docs-only closure)
  - Status: ✅ Done
  - Reason: Implemented VIP-only access for `/api/v1/insight` and legacy `/insight` (VIP-guarded, hidden from OpenAPI) + kept rate-limiting. This ledger entry was stale vs `main`.
  - Residual risk / follow-up: monthly hard quota/budget enforcement is still required (see next P0 item). Until then,
    LLM endpoints remain economically unsafe per `docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md`.
  - Links:
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (Tier guards section)
    - docs/audit/AUDIT_GAPS_ANALYSIS.md (LLM cost control gap)
    - PR-640: Enforce VIP tier for LLM Insight (runtime implementation)
    - docs/audit/PR_646_VIP_ONLY_LLM_INSIGHT_AUDIT.md (evidence + ledger closure)
  - DoD:
    - ✅ `/api/v1/insight` uses `require_vip_tier()` (VIP-only)
    - ✅ `/insight` is VIP-guarded (deprecated + hidden from OpenAPI)
    - ✅ Tests verify FREE/PRO users get 403, VIP users get 200
    - ✅ OpenAPI shows `/api/v1/insight` and hides `/insight`

- [x] P0 CRITICAL SECURITY: VIP LLM hard monthly quota (deterministic enforcement)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (CRITICAL security)
  - Target PR: PR-647 (security fix)
  - Status: ✅ Merged (PR-647)
  - Reason: VIP-only + rate limit prevent bursts but do not provide a monthly cost ceiling; without quota, sustained
    usage can still create an economic DoS. Policy requires a hard cost cap for LLM endpoints.
  - Links:
    - docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md
    - docs/audit/PR_646_VIP_ONLY_LLM_INSIGHT_AUDIT.md
    - docs/audit/PR_647_VIP_LLM_MONTHLY_QUOTA_AUDIT.md
    - PR-647: VIP LLM hard monthly quota (deterministic enforcement)
  - DoD:
    - Server-side authoritative quota per VIP key (requests/month OR tokens/month OR estimated cost/month)
    - Hard-stop before provider call when quota exceeded
    - Deterministic non-leaky error response on exceed (prefer `429`, e.g. `quota_exceeded`)
    - Tests:
      - VIP under quota → 200
      - VIP over quota → 429
      - FREE/PRO remain → 403
    - Minimal observability: counters/logging for usage and quota decisions

- [x] P0: CI nightly — test DB schema bootstrap broken (users/nutrition_events missing)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (CRITICAL)
  - Target PR: PR-629
  - Status: ✅ Merged (PR-629)
  - Reason: CI/nightly shows DB schema is not created before API tests (`no such table: users`, `no such table: nutrition_events`), causing secondary thread errors. Root cause: metadata/bootstrap ordering (missing model package import before create_all).
  - Signals: "no such table: users / nutrition_events" + "SQLite objects created in a thread..." / check_same_thread/threadpool
  - Scope: tests/conftest + tests/test_nutrition_log_api.py (bootstrap ordering) + minimal agent rule update (implemented in PR-629)
  - Links:
    - PR-629: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/629>
    - CI nightly failed run: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/21577239103>
    - Failing job (tests): <https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/21577239103/job/62166939568>
  - DoD:
    - `pytest -q tests/test_nutrition_log_api.py` passes in CI runner
    - No "no such table: users" or "no such table: nutrition_events" in setup/teardown
    - Fail-fast guard: if schema missing after init_db(), tests fail with clear message (no silent warn+continue)
  - Notes (3 February 2026, America/New_York):
    - Fix: close leaked TestClients (context-managed `tests/conftest.py::client` + close in `tests/test_nutrition_log_api.py` teardown) to ensure lifespan runs deterministically under xdist.
    - Verification (local, 6 February 2026): `pytest -q tests/test_nutrition_log_api.py -n 2 --dist=loadgroup` passed on `main` (post-merge).
    - Verification (local, 6 February 2026): `pytest -q tests/test_db_engine_reuse_diff_coverage.py tests/test_sqlite_engine_sot.py` passed on `main`.

- [x] P1: Verify and secure WebSocket endpoint (if exists) — RESOLVED
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security)
  - Target PR: N/A (investigation only)
  - Status: ✅ Resolved — No WebSocket endpoints found
  - Reason: Comprehensive codebase search found no WebSocket endpoints (`@app.websocket`, `/ws` path, WebSocket imports). Original analysis was false positive — WebSocket never existed or was removed. Security gap does not exist (no endpoint to secure).
  - Links:
    - docs/audit/WEBSOCKET_ANALYSIS.md (investigation results)
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (WebSocket section — updated)
    - docs/audit/AUDIT_GAPS_ANALYSIS.md (WebSocket authentication gap — false positive)
  - DoD:
    - ✅ Searched entire codebase for WebSocket endpoints (no matches found)
    - ✅ Verified no WebSocket routes in `legacy_app.py`, `app/routers/*`, `app/main.py`
    - ✅ Checked OpenAPI schema (no WebSocket paths)
    - ✅ Identified false positives (test fixes, frontend dependency, docs references)
    - ✅ Marked as resolved — security gap does not exist

- [ ] P1: Implement WebSocket endpoint with security from start
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (feature + security)
  - Target PR: TBD (feature implementation)
  - Status: 📋 Planned
  - Reason: WebSocket needed for real-time features (meal plan updates, live nutrition tracking, push notifications, future collaborative meal planning). Must be implemented with authentication and rate-limiting from the start to avoid security gaps.
  - Links:
    - docs/audit/WEBSOCKET_ANALYSIS.md (current state — no WebSocket exists)
    - docs/rfc/TON_RFC.md (WebSocket mentioned as requirement for real-time functions)
    - docs/design/NUTRITION_COACHING_DESIGN.md (potential use case: real-time coaching)
  - Prerequisites:
    - ✅ Security requirements defined (auth + rate-limiting)
    - ⏳ Use cases defined (what real-time features need WebSocket)
  - DoD:
    - WebSocket endpoint `/ws` implemented with FastAPI WebSocket support
    - Authentication required (token in query params or headers)
    - Rate-limiting implemented (per-user message limits, e.g., 100 messages/minute)
    - Tests verify unauthenticated connections are rejected (403/401)
    - Tests verify rate-limiting works (429 when limit exceeded)
    - OpenAPI schema updated (if FastAPI/OpenAPI supports WebSocket documentation)
    - Documentation: WebSocket API contract, authentication flow, rate limits

- [x] P1: Extract hardcoded constants (BMR, export formats)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintainability)
  - Target PR: PR #644
  - Status: ✅ Merged (PR #644)
  - Merge SHA: fda459d743e848b72c2c818b8dd7bef62af99aec
  - Reason: BMR formula constants and export formats are hardcoded in `legacy_app.py`. Should be extracted to `core.bmr` module and `ExportFormat` enum for maintainability.
  - Links:
    - PR #644
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (Hardcoded constants section)
    - legacy_app.py:97 (nutrition_core imports), export functions
  - DoD:
    - Extract BMR constants to `core/bmr.py` module
    - Create `ExportFormat` enum (CSV, PDF, JSON)
    - Replace hardcoded values with constants/enum
    - Tests verify no functionality broken

---

## P1 — Improvements (Optional / polish)

- [x] P1: Home/Plate/Progress CTA runtime remediation from visual matrix SoT
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #794 (`feat/hpp-cta-runtime-remediation`)
  - Status: ✅ Merged (PR #794, 2026-02-18)
  - Merge SHA: 9ebcca2fc377753dc3024a080e6e4f24f59b6479
  - Area: web / ios / design handoff
  - Finding Type: execution follow-up / button-level UX parity
  - Reason: `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md` formalized button-level SoT and exposed runtime gaps (iOS placeholder CTA destinations, missing deterministic CTA tests, and web paywall purchase wiring still callback-only). These follow-ups must be tracked as implementation debt, not left as doc-only intent.
  - Links:
    - PR #794
    - `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
    - `docs/plan/PR_HPP_CTA_RUNTIME_TASK_ANALYSIS.md`
    - `docs/plan/PR_HPP_CTA_RUNTIME_EXECUTION_PLAN.md`
    - `docs/audit/PR_HPP_CTA_RUNTIME_AUDIT.md`
    - `docs/audit/PR_HPP_CTA_RUNTIME_BRAINSTORMING.md`
    - `docs/audit/PR_HPP_CTA_RUNTIME_PR_BODY_SKELETON.md`
    - `AGENTS.md`
    - `frontend/AGENTS.md`
    - `ios/AGENTS.md`
  - DoD:
    - iOS `Add Meal` and `View Details` CTA destinations are no longer placeholders
    - Deterministic CTA-level tests exist for Home/Plate/Progress critical paths (web+iOS)
    - Web paywall CTA has production-ready purchase wiring and success/failure handling
    - Matrix `Exists Now / Missing / Implement Needed` statuses are updated after remediation PR
    - `make verify` and required CI checks are green in remediation PR

- [x] P1: Home/Plate/Progress Figma sync and Code Connect bridge docs package
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #798 (`docs/figma-hpp-sync-package`)
  - Status: ✅ Merged (PR #798, 2026-02-19)
  - Merge SHA: 891a3fcaaac3da351c104a3ebb164c4c02a126c3
  - Area: docs / design / orchestration
  - Finding Type: documentation contract delivery
  - Reason: Landed canonical H+P+Pr Figma sync protocols and Code Connect activation
    bridge docs with evidence anchors, bot-review remediations, and policy-aligned
    AGENTS updates; this closes the docs package while keeping Design URL/node ID
    activation dependency explicitly tracked as a separate open ledger item.
  - Links:
    - PR #798
    - `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
    - `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
    - `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
    - `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
    - `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md`
    - `AGENTS.md`
  - DoD:
    - Figma Make sync audit protocol committed with evidence anchors
    - Code Connect activation blocker protocol and mapping candidate registry committed
    - Design URL + node ID capture protocol committed
    - Orchestration session artifacts committed for the sync package
    - Root `AGENTS.md` updated with canonical Figma workflow protocol references

- [x] P1: Home/Plate/Progress live indicator + CTA instrumentation (web-first)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #801 (`feat/hpp-live-indicator-cta`)
  - Status: ✅ Merged (PR #801, 2026-02-19)
  - Merge SHA: aec126d6b8757a7a413ebf051f5e7f8a917c3e42
  - Area: frontend / product-metrics / HPP UX
  - Finding Type: user-visible activation package
  - Reason: Deliver one narrow user-facing package that adds a live progress signal on
    Home/Plate/Progress, keeps strict static fallback when realtime transport is unavailable,
    and instruments CTA impression/click events for conversion measurement.
  - Links:
    - PR #801
    - `frontend/src/features/progress/LiveProgressIndicator.tsx`
    - `frontend/src/features/progress/useHppLiveIndicator.ts`
    - `frontend/src/lib/hppTelemetry.ts`
    - `frontend/src/pages/Home.tsx`
    - `frontend/src/pages/Plate.tsx`
    - `frontend/src/pages/Progress.tsx`
  - DoD:
    - Live indicator renders on Home, Plate, and Progress surfaces
    - Fallback invariant preserved (`ws unavailable/error -> static indicator + CTA works`)
    - CTA telemetry events (`impression`, `click`) emitted through centralized helper
    - Deterministic tests added for hook, indicator, and HPP page integration
    - Thin-client websocket guard remains green (`src/api/wsClient.ts` adapter boundary)

- [x] P1: WebSocket foundation work-package (`/ws` secure baseline)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #778
  - Status: ✅ Merged (PR #778, 2026-02-17, `48ae6d24`)
  - Merge SHA: 48ae6d24458da4f0bb101b0c92d77e4607a6aded
  - Area: backend / realtime / security baseline
  - Finding Type: delivery packaging / transport foundation
  - Reason: Deliver one scoped realtime package with fail-closed auth, deterministic guardrails, and policy-anchored docs/tests without scope creep into client integration.
  - Links:
    - `docs/audit/PR_778_WEBSOCKET_FOUNDATION_AUDIT.md`
    - `docs/plan/PR_778_WEBSOCKET_FOUNDATION_PLAN.md`
    - `app/routers/realtime_ws.py`
    - `tests/test_websocket_security_api.py`
  - DoD:
    - `/ws` route is registered once in canonical app entrypoint and guarded against duplicates
    - WebSocket auth remains fail-closed with explicit policy close paths
    - Deterministic tests cover auth reject/accept, payload/limit guards, and disconnect path
    - Governance/docs are synchronized in AGENTS + audit + plan
    - CI gates for PR #778 are green before merge

- [x] P1: WebSocket foundation follow-up (realtime expansion package)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #783
  - Status: ✅ Merged (PR #783, 2026-02-17, `a78040a0`)
  - Merge SHA: a78040a0d8a191876f702b426b98ae82ae9460cc
  - Area: backend / realtime / contracts
  - Finding Type: scope control / deferred enhancement
  - Reason: Current work-package intentionally delivers only secure websocket foundation (`/ws`, auth, limits, `ping -> pong`). Any expansion beyond foundation (event catalog, client consumers, rooms/fan-out) is deferred to avoid scope creep.
  - Links:
    - `docs/audit/PR_778_WEBSOCKET_FOUNDATION_AUDIT.md`
    - `docs/plan/PR_778_WEBSOCKET_FOUNDATION_PLAN.md`
    - `docs/audit/PR_WS_REALTIME_EXPANSION_AUDIT.md`
    - `docs/plan/PR_WS_REALTIME_EXPANSION_PLAN.md`
  - DoD:
    - Define versioned event contract for realtime payloads
    - Add client integration scope (web/iOS) without violating thin-adapter policy
    - Add deterministic integration tests for expanded event flow
    - Keep `make verify` and diff-coverage gates green in expansion PR

- [x] P1: WebSocket idle-timeout follow-up (capacity safeguard)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #786
  - Status: ✅ Merged (PR #786, 2026-02-18, `a2e248cb`)
  - Merge SHA: a2e248cb5feaa84608acc68491954476228751d4
  - Area: backend / realtime / capacity
  - Finding Type: deferred hardening / runtime safeguard
  - Reason: PR #783 intentionally shipped secure websocket foundation (`/ws`, auth, limits, versioned events) without idle timeout to avoid scope creep. Remaining risk is capacity/resource retention from idle connections (not a security bypass).
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/786`
    - `docs/audit/PR_WS_REALTIME_EXPANSION_AUDIT.md`
    - `docs/plan/PR_WS_REALTIME_EXPANSION_PLAN.md`
    - `docs/plan/PR_WS_IDLE_TIMEOUT_PLAN.md`
    - `docs/audit/PR_WS_IDLE_TIMEOUT_AUDIT.md`
    - `app/routers/realtime_ws.py`
  - DoD:
    - Add `WS_IDLE_TIMEOUT_SECONDS` with conservative default and explicit disable mode
    - Close idle websocket connections with deterministic policy close semantics
    - Add deterministic tests for idle-timeout behavior without `sleep()`-based flakiness
    - Keep existing websocket guardrails unchanged (fail-closed auth, burst limiter, connection cap)
    - Pass `make verify` and diff-coverage gates in follow-up PR

- [x] P1: WebSocket observability hardening (low-cardinality metrics + structured logs)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #789
  - Status: ✅ Merged (PR #789, 2026-02-18, `7d9e74ec`)
  - Merge SHA: 7d9e74eca58841a120249f98db19880dc18c56e3
  - Area: backend / realtime / observability
  - Finding Type: operational hardening / incident response readiness
  - Reason: After deterministic idle-timeout delivery in PR #786, the remaining high-value runtime gap is operational visibility of `/ws` behavior under load. Without explicit websocket metrics and constrained structured logs, incident triage is slower and capacity regressions are harder to detect early.
  - Worst-case scenario: high-volume idle/malformed websocket traffic degrades service while missing or high-cardinality observability obscures root cause and delays mitigation.
  - Scope IN:
    - Add low-cardinality counters for websocket connect result and close reasons.
    - Add active websocket gauge aligned with tracker state.
    - Add message counters by allowlisted event type (`ping`, `subscribe`) and outcome (`ok`/`closed`).
    - Add structured logs for policy closes using non-sensitive fields only.
  - Scope OUT:
    - Product analytics, user-behavior funnels, and per-user telemetry.
    - New websocket protocol features/channels.
    - Frontend/iOS telemetry changes.
  - Guardrails:
    - Never log tokens, user IDs, raw payloads, or unbounded labels.
    - Metrics labels must remain low-cardinality and enum-bound.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/789`
    - `app/routers/realtime_ws.py`
    - `app/middleware/metrics.py`
    - `docs/audit/PR_WS_OBSERVABILITY_HARDENING_AUDIT.md`
    - `docs/plan/PR_WS_OBSERVABILITY_HARDENING_PLAN.md`
    - `docs/audit/PR_WS_IDLE_TIMEOUT_AUDIT.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/786`
  - DoD:
    - `ws_connect_total{result,reason}` and `ws_messages_total{type,result}` are implemented with bounded labels.
    - `ws_active_connections` gauge reflects tracker state without negative drift.
    - Structured websocket logs include only safe, bounded fields (`reason`, `event_type`, `version`, `result`).
    - Deterministic tests validate metric increments and no-`sleep()` time-based behavior.
    - `make verify` and diff-coverage gates are green in observability PR.

- [x] P1: Shoplist flow stabilization work-package (`plan -> shoplist`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #770
  - Status: ✅ Merged (PR #770, 2026-02-16, `c54143ab`)
  - Merge SHA: c54143abee6568f42443822f9a6cb47b17edbbc4
  - Area: backend / contracts / integration tests
  - Finding Type: delivery packaging / flow contract
  - Reason: Move from micro-PR fragmentation to one scoped runtime package delivering a full user-visible flow outcome with deterministic tests and rollback.
  - Links:
    - `docs/audit/PR_SHOPLIST_FLOW_STABILIZATION_WORK_PACKAGE_PLAN.md`
    - `docs/audit/PR_764_SHOPLIST_HELPERS_ENABLE_AUDIT.md`
  - DoD:
    - One scoped runtime PR delivers `plan -> shoplist` end-to-end outcome
    - Contract tests cover 200 + key failure statuses where applicable
    - Integration happy path is deterministic
    - `Content-Type` and error envelope assertions are explicit
    - `make verify` passes and required CI checks are green

- [x] P1: Re-enable repository `sys.modules` mutation guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-732
  - Status: ✅ Merged (PR-732, 2026-02-13, `b36e88ed`)
  - Area: backend / tests / policy guards
  - Finding Type: quality / guard enforcement
  - Locations:
    - `tests/test_repo_policy_guards.py:98` — active runtime guard
      (`test_no_sys_modules_mutation_in_repo`)
  - Reason: Disabled guard weakens a known import-hygiene invariant and can hide dual-module regressions.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `tests/test_repo_policy_guards.py:98`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/732`
  - Evidence (2026-02-13):
    - `pytest -q tests/test_repo_policy_guards.py -rs` -> pass (guard enabled, not skipped)
  - DoD:
    - Guard is enabled in CI (not skipped)
    - Offenders are cleaned up or explicitly phased with a documented allowlist plan
    - Guard remains deterministic under xdist and normal pytest runs
    - `make verify` passes in PR-732

- [x] P1: Async SQLAlchemy wiring for day shoplist tests
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-742
  - Status: ✅ Merged (PR-742, 2026-02-14)
  - Resolution note: Removed async-config SKIPs; isolated `DATABASE_USE_ASYNC` via
    `monkeypatch`; reset async engine/session globals to prevent cross-test leakage;
    xdist validated on the target suite.
  - Area: backend / tests / infra
  - Finding Type: quality / infrastructure determinism
  - Locations:
    - `tests/test_shoplist_day_db_wiring.py:39`
    - `tests/test_shoplist_day_db_wiring.py:112`
    - `tests/test_shoplist_day_db_wiring.py:180`
    - `tests/test_shoplist_day_db_wiring.py:222`
  - Reason: Async DB tests should be deterministically configured (or removed as obsolete), not skipped by default.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `core/db.py:613`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/742`
  - Evidence (2026-02-14):
    - `rg -n "Async SQLAlchemy not configured" tests` -> no matches
    - `rg -n "reload\\(core\\.db\\)|importlib\\.reload\\(core\\.db\\)" tests`
      -> no runtime matches
    - `pytest -q -n auto tests/test_shoplist_day_db_wiring.py` -> PASS
  - DoD:
    - ✅ No async-config SKIPs
    - ✅ xdist PASS on target suite
    - ✅ No `core.db` reload

- [x] P1: Post-stabilization drift cleanup for skip-heavy coverage suites
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-773
  - Status: ✅ Merged (PR-773, 2026-02-16)
  - Area: backend / tests / contracts
  - Finding Type: drift / contract mismatch
  - Locations:
    - `tests/test_database_apis_coverage.py`
    - `tests/test_direct_core_functions.py`
    - `tests/test_final_core_coverage.py`
    - `tests/test_final_coverage_97_boost.py`
    - `tests/test_quick_coverage_boost.py`
    - `tests/test_remaining_modules.py`
    - `tests/test_zero_coverage_modules.py`
  - Reason: Large skip bucket (`module/symbol not available`) is mostly contract drift between legacy test expectations and current canonical APIs.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `core/food_apis/unified_db.py:265`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/773`
  - Merge SHA: `3404ca39`
  - Notes: CP1+CP2 done in PR-773; CP3 deferred to a separate follow-up PR.
  - DoD:
    - Drift-based skips are reduced via canonical test alignment (not API inflation for coverage)
    - Signature mismatches are resolved with explicit contract assertions
    - Remaining intentional skips are documented as product decisions
    - `make verify` passes in PR-732

- [x] P1: CP3 follow-up for skip-heavy coverage drift cleanup
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #791 (`feat/cp3-skip-drift-execution`)
  - Status: ✅ Merged (PR #791, 2026-02-18)
  - Area: backend / tests / contracts
  - Finding Type: drift / contract mismatch
  - Locations:
    - `tests/test_zero_coverage_modules.py`
    - `tests/test_remaining_modules.py`
    - `tests/test_final_core_coverage.py`
    - `tests/test_direct_core_functions.py`
    - `tests/test_quick_coverage_boost.py`
  - Reason for deferral: CP3 was intentionally split out from PR-773 to keep CP1+CP2 merge-safe and avoid scope creep in a test-only stabilization package.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/791`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/773`
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `docs/audit/CP3_SKIP_HEAVY_A1_NOOP_AUDIT_2026-02-16.md`
    - `docs/plan/CP3_SKIP_COVERAGE_DRIFT_PLAN.md`
    - `docs/plan/PR_CP3_SKIP_DRIFT_TASK_ANALYSIS.md`
    - `docs/plan/PR_CP3_SKIP_DRIFT_EXECUTION_PLAN.md`
    - `docs/audit/PR_CP3_SKIP_DRIFT_AUDIT.md`
    - `docs/audit/PR_CP3_SKIP_DRIFT_PR_BODY_SKELETON.md`
    - `core/food_apis/unified_db.py:265`
  - Merge SHA: `2ea565ddf2c16ead430a1f1aa6770fade88d22bd`
  - DoD:
    - CP3 buckets are implemented in a dedicated follow-up PR with explicit mapping by test file.
    - Remaining intentional skips are documented as product decisions with canonical feature keys.
    - No ad-hoc skip reasons are introduced; skip protocol remains `feature_disabled:<key>`.
    - `make verify` passes in the CP3 execution PR.

- [ ] P1: Feature TODO from runtime SKIPPED suites (optional modules manifest)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-738
  - Reason for deferral: Runtime test suites currently surface optional-module skips with
    ad-hoc strings; defer execution until PR-738 introduces `tests/feature_manifest.py` and
    `require_feature(...)` to standardize skip reasons and keep ledger↔tests keys one-to-one.
  - Status: 📋 Planned (created in PR-736 docs-only; promoted from runtime snapshot on
    13 February 2026)
  - Area: backend / tests / feature debt management
  - Finding Type: technical debt / optional-feature protocol
  - Source of truth command:
    - `pytest -q -rs | rg -n "SKIPPED \\[" || true`
  - Feature TODO keys (aggregated from runtime SKIPPED):
    - `core_db`: `tests/test_database_apis_coverage.py:43`,
      `tests/test_direct_core_functions.py:353`
    - `food_apis`: `tests/test_database_apis_coverage.py:62`,
      `tests/test_database_apis_coverage.py:82`,
      `tests/test_database_apis_coverage.py:102`
    - `unified_db`: `tests/test_database_apis_coverage.py:124`,
      `tests/test_final_coverage_97_boost.py:139`
    - `update_manager`: `tests/test_database_apis_coverage.py:151`,
      `tests/test_final_coverage_97_boost.py:167`,
      `tests/test_final_coverage_97_boost.py:179`,
      `tests/test_update_manager_fixed.py:129`
    - `planner_engines`: `tests/test_direct_core_functions.py:45`,
      `tests/test_direct_core_functions.py:97`,
      `tests/test_direct_core_functions.py:141`,
      `tests/test_direct_core_functions.py:185`,
      `tests/test_final_core_coverage.py:232`,
      `tests/test_final_core_coverage.py:262`,
      `tests/test_final_core_coverage.py:294`,
      `tests/test_final_core_coverage.py:322`
    - `i18n_advanced`: `tests/test_database_apis_coverage.py:306`,
      `tests/test_direct_core_functions.py:234`
    - `rag`: `tests/test_database_apis_coverage.py:333`,
      `tests/test_direct_core_functions.py:320`,
      `tests/test_quick_coverage_boost.py:269`
    - `region_catalog`: `tests/test_direct_core_functions.py:396`
    - `exports_recipes_products`: `tests/test_zero_coverage_modules.py:90`,
      `tests/test_zero_coverage_modules.py:144`,
      `tests/test_zero_coverage_modules.py:190`,
      `tests/test_zero_coverage_modules.py:239`,
      `tests/test_zero_coverage_modules.py:275`
    - `sports_disclaimers_lifestage`: `tests/test_zero_coverage_modules.py:45`,
      `tests/test_zero_coverage_modules.py:313`,
      `tests/test_zero_coverage_modules.py:345`
    - `legacy_bmi_removed`: `tests/test_app_coverage_unit_combined.py:83`,
      `tests/test_app_coverage_unit_combined.py:88`
  - Protocol:
    - Any runtime skip reason matching `module not available` /
      `advanced features not available` MUST map to one feature key above.
    - No ad-hoc skip reasons for optional modules in high-noise suites.
    - Follow-up execution PR introduces `tests/feature_manifest.py` and a shared
      `require_feature(...)` helper for standardized skip reasons.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `tests/test_database_apis_coverage.py`
    - `tests/test_direct_core_functions.py`
    - `tests/test_final_core_coverage.py`
    - `tests/test_quick_coverage_boost.py`
    - `tests/test_zero_coverage_modules.py`
  - DoD:
    - `tests/feature_manifest.py` exists with SoT feature keys and env opt-in
      (`PULSEPLATE_FEATURES=all` or CSV list).
    - High-noise suites use shared helper instead of custom ad-hoc skip strings.
    - Runtime `pytest -q -rs` output shows standardized skip reasons with feature keys.
    - Feature keys in tests and ledger remain one-to-one mapped.

- [ ] P1: Unimplemented feature keys backlog (SoT = tests/feature_manifest.py)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-748
  - Status: 📋 Planned (seeded by PR-747 protocol cleanup)
  - Area: backend / tests / feature debt management
  - Finding Type: product feature debt / runtime skip protocol
  - Reason for deferral: Runtime skip reasons are now standardized via
    `feature_disabled:<key>`, but implementation work for gated features remains
    deferred to focused execution PRs.
  - Source of truth command:
    - `pytest -q -rs | rg -n "feature_disabled:" || true`
  - Links:
    - `tests/feature_manifest.py`
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `docs/roadmap/BACKLOG_LEDGER.md` (this section)
  - DoD:
    - For each implemented feature key, remove/replace corresponding
      `require_feature(...)` gate in tests.
    - Runtime `feature_disabled:<key>` skip count decreases as features land.
    - Ledger item is updated with merged PR references per implemented key.
  - Implemented keys (latest):
    - `shoplist_helpers` -> ✅ Merged (PR-764, 2026-02-16, `48c87f39`)

- [ ] Cross-platform Design System: define tokens + UI primitives (Web + iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design consistency / velocity)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason: Web has initial brand colors in `frontend/src/styles/tokens.ts`, but iOS lacks a centralized token mirror
    (colors/spacing/typography/motion). Without a minimal design system, UI work drifts, is slower to delegate, and is
    harder to review consistently across platforms.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (design canon + agent roster + checklists)
    - `frontend/src/styles/tokens.ts` (current Web token starting point)
    - `frontend/AGENTS.md`, `ios/AGENTS.md` (thin-client + CI invariants)
  - DoD:
    - Token canon defined (colors + spacing + typography + motion + elevation) with explicit names
    - iOS has a single source for tokens (SwiftUI-friendly) and uses it in new components
    - Web components consume tokens (no hardcoded brand colors/spacing in new primitives)
    - Minimal primitives exist on both platforms: Button, Card, Input, Typography

- [ ] Accessibility: ship-blocking UI checklist + enforcement for Web+iOS
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (release quality)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason: Accessibility must be enforced as a process, not a best-effort review comment. We need deterministic checks
    (or at least guardrails) for labels, focus, contrast, and touch targets so new UI ships safely.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (a11y checklist section)
    - `ios/AGENTS.md` (HIG + CI constraints)
    - `frontend/AGENTS.md` (web testing and thin-client guards)
  - DoD:
    - PR template/checklist requires explicit a11y verification (iOS + Web)
    - Web: jsx-a11y (or equivalent) rules applied to new/changed UI components
    - iOS: documented checklist + at least one deterministic guard approach for common failures
    - No new UI components added without a11y confirmation in PR evidence

- [ ] FitChef assets: establish a reusable SVG/Lottie pipeline + usage guide
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (brand consistency)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason: FitChef is the brand anchor, but without an asset pipeline + constraints (states, placement, tone), assets
    will be re-created ad-hoc and drift. We need a repeatable way to request, review, and ship assets.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (fitchef-asset-manager role)
    - Root `AGENTS.md` (wellness-safe language boundaries)
  - DoD:
    - FitChef state list defined (welcome/success/error/empty/loading) with “do/don’t” usage notes
    - Asset packaging rules documented (no text baked into images; localization-safe)
    - A minimal starter pack exists (at least 3 states) and is used in one Web screen and one iOS screen

- [ ] Conversion Safety: paywall/onboarding/result-screen checklists + minimal analytics event taxonomy
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (growth / App Store safety)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason: Conversion optimizations must remain wellness-safe and App Store compliant. We need a consistent checklist
    to avoid “pretty UI that doesn’t convert” and to ensure analytics captures the funnel deterministically.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (conversion checklist section)
    - `docs/contracts/PRODUCT_TIER_MAP.md` (FREE/PRO/VIP differentiation; canonical)
  - DoD:
    - Paywall + onboarding + results-screen checklist documented and used in PR descriptions
    - Minimal event taxonomy defined (activation + paywall funnel + conversion) with properties
    - Copy guidance explicitly avoids medical claims and dark patterns

- [x] Dev tooling: GraphMap viewer + deterministic graph builder (dev-only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (developer experience)
  - Target PR: PR-695 + PR-696
  - Status: ✅ Merged (PR-695 @ 2e3d1a5b, PR-696 @ 8e527c13; 2026-02-08)
  - Reason: Make SoT relationships (docs/agents/policies/tests) navigable as an interactive graph with strict determinism.
    This reduces repeated rediscovery work and improves reviewability without introducing a new SoT.
  - Links:
    - `docs/graph/GRAPHMAP_SPEC.md` (SoT for GraphMap; docs-only)
    - `docs/memory/index.md` (PML capsules as graph inputs)
    - `docs/orchestration/AGENT_CONTEXT_MAP.md`
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/agents/index.md`
  - DoD:
    - ✅ `docs/graph/GRAPHMAP_SPEC.md` defines GraphMap inputs and edge rules
    - ✅ Deterministic builder generates stable `docs/graph/graph.json` from explicit sources only
    - ✅ Viewer supports filtering by `Level` and `NodeType`, plus search, legend, and zoom controls
    - ✅ Clicking opens GitHub file links (optionally `path:line` anchors) and never opens local absolute paths
    - ✅ Forbidden edges are enforced (no semantic guessing / embeddings / AI-inferred relationships)
    - ✅ No runtime impact; no secrets/tokens; safe for local usage (and optionally GitHub Pages)

- [ ] Orchestration: implement AI multi-agent contracts (RAG/UQ/CV + safety) — runtime follow-up
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI / safety / reliability)
  - Target PR: TBD (runtime)
  - Status: 📋 Planned
  - Area: backend / AI orchestration
  - Finding Type: product + safety
  - Reason: We have a docs-level orchestration baseline and role contracts, but runtime implementation must enforce
    bounded recursion (cost control), grounding/citations, uncertainty reporting, and wellness-safe language.
  - Links:
    - `docs/audit/PR_TBD_UNIVERSAL_AGENT_ORCHESTRATION_LAYER_AUDIT.md`
    - `docs/orchestration/workflow.md` (canonical workflow; dev-only)
  - DoD:
    - RAG endpoints (if any) are tier-gated, rate-limited, and enforce monthly quota before provider calls
    - Deterministic tests prove 200 → 429 transitions and quota enforcement
    - Outputs include explicit `sources[]` and confidence/uncertainty fields per contract
    - No OpenAPI determinism regressions; `make verify` passes

- [x] Observability: measure legacy nutrition alias usage (deprecation removal readiness)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (observability / migration)
  - Target PR: PR-698
  - Status: ✅ Merged (PR-698, 2026-02-09)
  - Reason: `GET /api/nutrition/{date_str}` is a deprecated compatibility alias. Before removing it safely, we need
    basic usage telemetry (by client/platform) to confirm iOS migration completion and avoid breaking unknown consumers.
  - Links:
    - `app/routers/legacy_nutrition_alias.py` (`/api/nutrition/{date_str}` legacy alias)
    - `docs/roadmap/BACKLOG_LEDGER.md` (P0 security fix item for alias guard)
  - DoD:
    - Count requests to `/api/nutrition/{date_str}` with low-cardinality labels (e.g., platform/client + status)
    - Dashboard/query recipe documented (where to check usage)
    - Removal decision recorded (remove alias date / keep longer with rationale)
- [x] Backend: Make VIP insight guard tests CI-deterministic
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (CI stability)
  - Target PR: PR-658
  - Status: ✅ Merged (PR-658, 2026-02-06)
  - Reason: VIP insight guard tests should validate tier gating (403/200) without coupling to provider/quota internals, avoiding CI flakiness.
  - Links:
    - `tests/test_insight_vip_guard_api.py`
    - PR-658
  - DoD:
    - Tests patch quota/provider paths deterministically
    - `diff-coverage` passes on PRs touching these guard tests

- [x] iOS: Expose BMI screen from Home / RootTabs (Free MVP UX)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (Free MVP polish)
  - Target PR: PR-671
  - Status: ✅ Merged (PR-671, 2026-02-07)
  - Reason: BMI calculator exists but is not clearly reachable from the main navigation (Free MVP must make value moment obvious).
  - Links:
    - `ios/PulsePlate/Views/RootTabs.swift`
    - `ios/PulsePlate/Screens/BMICalculatorScreen.swift`
    - `ios/PulsePlate/ViewModels/BMICalculatorViewModel.swift`
    - `docs/audit/PR_671_IOS_EXPOSE_BMI_ROOTTABS_AUDIT.md`
  - DoD:
    - User can reach BMI from the default tab flow (Home card or dedicated tab)
    - Loading/error/validation states remain user-friendly (no debug-y messages)
    - `make ios-test` passes

- [x] iOS: Plate (PRO) align to canonical backend `GET /api/v1/pro/nutrition/daily` + profile input
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (Feature integration)
  - Target PR: PR-667
  - Status: ✅ Merged (PR-667, 2026-02-07)
  - Reason: iOS Plate now uses canonical `GET /api/v1/pro/nutrition/daily` with deterministic query building + `X-API-Key` (no legacy alias as source-of-truth).
  - Links:
    - `app/routers/pro.py` (canonical: `/api/v1/pro/nutrition/daily`)
    - `legacy_app.py` (deprecated shim: `/api/nutrition/{date_str}`)
    - `ios/PulsePlate/Views/PlateView.swift` / `ios/PulsePlate/Views/PlateViewPP.swift`
    - `ios/PulsePlate/Services/ProKeyProvider.swift`
    - `ios/PulsePlate/Services/ProDailyNutritionService.swift`
    - `ios/PulsePlate/Views/ProfileView.swift`
    - `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift`
  - Evidence (file:line):
    - iOS request path + deterministic query order: `ios/PulsePlate/Services/ProDailyNutritionService.swift:36-57`
    - iOS sends `X-API-Key` header via APIClient: `ios/PulsePlate/Services/ProDailyNutritionService.swift:94-105`
    - iOS profile inputs (AppStorage keys + form fields): `ios/PulsePlate/Views/ProfileView.swift:8-56`
    - iOS tests assert deterministic URL + header: `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift:6-21`, `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift:23-65`
    - Backend canonical route (guarded by PRO tier): `app/routers/pro.py:369-373`, `app/routers/pro.py:400-422`
  - DoD:
    - iOS implements a reusable profile source for required query params (sex/age/height_cm/weight_kg/activity/goal/lang)
    - iOS uses `APIClient` and calls canonical `GET /api/v1/pro/nutrition/daily` with `X-API-Key` from Keychain/env
    - UX: explicit states for missing PRO key / missing profile / 422 validation errors
    - Tests:
      - unit test for building daily nutrition request query (deterministic)
      - `make ios-test` passes

- [x] iOS: Mount WeeklyPlanReader behind feature flag (PRO demo slice) — ✅ Merged (PR-673, 2026-02-07)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (Demo / TestFlight)
  - Target PR: PR-673
  - Status: ✅ Merged (PR-673, 2026-02-07)
  - Reason: WeeklyPlanReader is mounted behind `FeatureFlags.weeklyPlanReaderEnabled` (Debug Tools entrypoint).
  - Links:
    - `ios/PulsePlate/Utilities/FeatureFlags.swift` (`weeklyPlanReaderEnabled`)
    - `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`
    - `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift`
    - `ios/PulsePlate/Services/WeeklyPlanService.swift`
    - `docs/audit/PR_673_IOS_WEEKLY_PLAN_READER_FLAG_AUDIT.md`
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/673>
  - DoD:
    - When `FeatureFlags.weeklyPlanReaderEnabled` is true, the screen is reachable (Debug tools or a controlled entrypoint)
    - Requests use `APIClient` and include `X-API-Key` where required (no auth bypass in production code)
    - Errors for 400/401/403 are rendered as user-readable states (not crashes)
    - `make ios-test` passes

- [x] P1 (maintenance): Type-hints carryover cleanup (tests)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintenance)
  - Target PR: PR #642
  - Status: ✅ Done (merged via PR #642)
  - Reason: Previously-agreed test typing/hygiene changes were missed in a prior PR and intentionally carried over to keep bots/review consistent. Non-functional change (tests only).
  - Notes: Missed in prior PR; carried over intentionally.
  - Links: PR #642; policy: AGENTS.md (carryover rule); related: PR #640/#641 (context)
  - DoD: Done. CI green; reviewers' sign-off; PR #642 merged; no new skips; only tests/docs changed

- [x] core/db.py vs core/db/ collision resolved (TP2 amendment 2026-01-28)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #617 (amendment)
  - Reason: TP2 originally used `core/db/fallback.py` which caused `core.db` to resolve as package in CI. Resolved by moving fallback to `core/db_fallback.py` (flat module) and removing `core/db/` package; no guard exception needed.
  - DoD: Done. Fallback in `core/db_fallback.py`; AGENTS.md rule: never add `core/<name>/` when `core/<name>.py` exists.

- [x] P1: Local/dev env alignment for SERVER_SALT + quota limit (post PR-647)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-649
  - Status: ✅ Merged (PR-649)
  - Reason: PR-647 introduced a fail-fast requirement for `SERVER_SALT` at app startup (VIP LLM monthly quota). Local/root
    `docker-compose.yaml` and `.env.example` must reflect required env vars to avoid confusing local startup failures.
  - Links:
    - PR-647: VIP LLM hard monthly quota (deterministic enforcement)
    - docs/audit/PR_647_VIP_LLM_MONTHLY_QUOTA_AUDIT.md
    - PR-649: env.example + docker-compose alignment for SERVER_SALT fail-fast
    - docs/audit/PR_649_ENV_REQUIRED_SERVER_SALT_AUDIT.md
  - DoD:
    - ✅ `.env.example` includes `SERVER_SALT` + `VIP_LLM_INSIGHT_REQUESTS_PER_MONTH` (with validation guidance)
    - ✅ Root `docker-compose.yaml` passes both vars; missing `SERVER_SALT` fails fast at compose evaluation time
    - ✅ Local compose boots deterministically when `SERVER_SALT` is provided

- [ ] docs(infra): add `.markdownlint.json` (follow-up after PR #617)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: TBD (separate docs/infra PR)
  - Reason: PR #617 scope reduced to docs-only (audit + handoff); markdownlint config moved out to avoid diff-coverage/CI scope. Add repo-wide markdownlint config in dedicated PR.
  - DoD: New PR with `.markdownlint.json` only; CI green; no mixing with code/audit PRs.

- [x] Restore full OpenAPI schema (remove temporary schema-only mode)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (contract velocity)
  - Target PR: PR-631
  - Status: ✅ Merged (PR-631, 2026-02-03)
  - Reason: Schema-only OpenAPI mode reduced thin-client contract velocity. PR-631 removed the schema-only seam and enabled full-schema generation with deterministic output.
  - Evidence:
    - `scripts/generate_openapi.py:94-109` (FULL schema mode; enables feature-flagged routers in generator context)
    - `tests/test_openapi_determinism.py:17-55` (asserts key PRO/business paths exist)
  - DoD: ✅ Completed (PR-631)
    - OpenAPI generator runs in full-schema mode (no schema-only marker)
    - `frontend/src/api/openapi.json` + `frontend/src/api/schema.ts` in sync (`make openapi` produces no diff)
    - Determinism test remains green

- [x] Eliminate import-time ORM/model imports in routers included in OpenAPI generation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (determinism / import hygiene)
  - Target PR: PR-631
  - Status: ✅ Merged (PR-631, 2026-02-03)
  - Reason: OpenAPI generation must be side-effect free: routers reachable from `app.main:app` must not import ORM models at module import time.
  - Evidence:
    - `app/routers/nutrition_log.py:26-73` (TYPE_CHECKING-only model import + runtime lazy import pattern)
    - `scripts/generate_openapi.py:114-120` (imports canonical entrypoint and calls `app.openapi()` successfully)
  - DoD: ✅ Completed (PR-631)
    - ORM model imports moved to runtime (inside handlers/dependencies), preserving OpenAPI determinism
    - OpenAPI generation works with routers enabled
    - Determinism test stays green

- [ ] P1: Unify `TargetsIn` schemas (legacy_app ↔ `app.schemas.nutrition_targets`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (drift prevention)
  - Target PR: TBD (follow-up after PR-631)
  - Status: 📋 Ready to start
  - Reason: There are currently two `TargetsIn` schemas (`legacy_app.TargetsIn` and `app.schemas.nutrition_targets.TargetsIn`). This is a potential source of drift over time, even though PR-631 intentionally kept them separate to stay scope-minimal (remediation only).
  - Links:
    - PR #631 (remediation): full OpenAPI without import-time `app.models.*` along OpenAPI path
  - Evidence:
    - `app/schemas/nutrition_targets.py:L1-L58` (import-safe schema + `TargetsIn` validators)
    - `legacy_app.py:L2879-L2919` (`legacy_app.TargetsIn` definition)
    - `legacy_app.py:L2939-L2954` (`TargetsIn.model_validate(...)` use in legacy request validator)
  - DoD:
    - One canonical schema (single source of truth) with a thin wrapper/alias where needed
    - Parity tests that prevent schema drift (fields + validation behavior for structured targets payloads)
    - No contract break for legacy endpoints (explicitly verified in tests)

- [ ] P1: Extract import-safe ORM model helper for OpenAPI path (dedupe lazy-import pattern)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintainability / import hygiene)
  - Target PR: TBD (follow-up after PR-631)
  - Status: 📋 Ready to start
  - Reason: `app.routers.nutrition_log` uses repeated lazy-import of `NutritionEvent` model to avoid import-time ORM side effects. A tiny helper (import-safe) would reduce duplication and make future additions safer.
  - Links:
    - PR #631 (remediation): moved ORM model import from module-level to lazy-import inside handlers
  - Evidence:
    - `app/routers/nutrition_log.py:L68-L84` (lazy-import inside `_fetch_existing_event`)
    - `app/routers/nutrition_log.py:L172-L176` (lazy-import inside `log_meal`)
    - `app/routers/nutrition_log.py:L241-L245` (lazy-import inside `close_day`)
  - DoD:
    - Add a single helper (import-safe) for model retrieval used by `nutrition_log` (and any similar routers)
    - Unit test that validates helper is import-safe (no import-time `app.models.*` in OpenAPI path)
    - No runtime behavior change (pure refactor)

- [ ] Constrain compat shim: `sys.modules["app_module"]` mapping in `app/__init__.py`
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (maintainability)
  - Target PR: TBD (post PR-628/629)
  - Status: 📋 Ready to start
  - Reason: `app/__init__.py` sets `sys.modules.setdefault("app_module", legacy_app)` for backward compatibility. This is intentional but must be tightly bounded to avoid “magic layer” imports/patches.
  - Evidence:
    - `app/__init__.py:44-56` (sys.modules mapping)
  - Risk:
    - Hard-to-debug patch behavior, hidden aliasing, accidental reliance by new code/tests.
  - Blocked-by:
    - None (small focused PR), but recommended after PR-628/629 to keep scopes clean
  - Exit criteria:
    - Mapping is either removed OR explicitly documented + guarded (no new uses)
  - DoD:
    - Add a short evidence-driven doc note describing why the mapping exists and what may rely on it
    - Add a small guard test preventing expansion (no overwrites / no new module injection patterns)
    - Define removal plan (conditions under which it can be deleted)

- [ ] Auto-generate architecture diagrams (Mermaid baseline + optional Graphviz import graph)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (docs/tooling)
  - Target PR: PR-630 (docs-only) or follow-up docs PR
  - Status: ✅ Baseline Mermaid added; automation optional
  - Reason: Architecture is enforced by guards, but reviewers/onboarding benefit from quick visuals. Automation reduces doc drift.
  - Evidence:
    - `docs/architecture/system_overview.md` (Mermaid system overview)
    - `docs/architecture/backend_routing_map.md` (evidence-driven routing map)
    - `docs/audit/PR_630_ARCHITECTURE_EVIDENCE_PACK_AUDIT.md` (evidence pack)
  - Risk:
    - Without maintenance/automation, diagrams drift and become misleading.
  - Exit criteria:
    - Diagram updates happen in the same PR as entrypoint/router/flag changes (enforced culturally or via light guard)
  - DoD:
    - Keep Mermaid as canonical diagram (single source of truth)
    - Optional: add a script that emits a filtered import graph (`.dot`/`.svg`) for selected slices (app/core/providers) with stable filtering rules

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

- [x] Resolve pip CVE-2026-1703 (pip 25.2 → 26.0+) in Docker image (GitHub alerts #533/#534)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-636
  - Status: ✅ Merged (PR-636)
  - Reason: Code Scanning alerts #533/#534 report CVE-2026-1703 for `pip 25.2` detected in two locations inside the built image (`/usr/local/lib/...` and `/opt/venv/lib/...`). Fix is to ensure Docker build upgrades pip to ≥26.0 (without exact pin in Dockerfile per policy).
  - Links:
    - GitHub alerts #533 / #534
    - `Dockerfile` (builder venv + runtime-base system pip)
    - `.github/workflows/trivy.yml` (builds `production` target and scans the image)
  - DoD:
    - Production image contains `pip>=26.0,<27.0` in both `/usr/local/lib/.../pip-*.dist-info` and `/opt/venv/lib/.../pip-*.dist-info`
    - 🔄 Awaiting next scan for alerts #533/#534 to close (merged ≠ scanner rerun)

- [x] Resolve cryptography CVE-2026-26007 in runtime/dev/lock manifests
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-716 (remediation: bump + guard); PR-724 = docs-only closure/policy
  - Status: ✅ Closed (remediation on main via PR-716; guard test in place; PR-724 adds AGENTS policy + ledger)
  - Reason: Five GitHub security alerts (Dependabot #27/#28/#29 and Code Scanning #538/#539) report vulnerable
    `cryptography` (`<=46.0.4`); required fixed version is `46.0.5`.
  - Links:
    - `docs/security/CVE-2026-26007-cryptography.md`
    - GitHub alerts: `security/dependabot/27`, `security/dependabot/28`, `security/dependabot/29`
    - GitHub alerts: `security/code-scanning/538`, `security/code-scanning/539`
  - DoD:
    - [x] `cryptography` bumped to `46.0.5` (or higher safe version) in `requirements.in`,
      `requirements.txt`, `requirements-dev.txt`, `requirements-lock.txt`, and `constraints.txt`
    - [x] New dependency security guard test added to enforce cryptography floor version
      (CVE-2026-26007) — `tests/test_dependency_security_guard.py`
    - [ ] Security/code scanning alerts close on next scan

- [ ] Generalize dependency vulnerability guards beyond single-CVE floors
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: TBD follow-up (security guard generalization)
  - Status: 📌 Backlog
  - Reason: Current guard test enforces a floor for one high-risk dependency (`cryptography`). Preventing future
    regressions at scale needs a deterministic allow/deny schema for multiple packages/CVEs.
  - Links:
    - `tests/test_dependency_security_guard.py`
    - `docs/security/CVE-2026-26007-cryptography.md`
  - DoD:
    - Introduce a centralized guard schema (`package -> min_safe_version` or denylist) for key dependencies
    - Deterministic CI/pytest check validates all relevant requirement surfaces
    - Developer docs explain how to update schema when new CVEs are triaged

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

- [x] Move insight redaction/import helpers out of legacy_app.py (merged 2026-02-10)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-703 (merged)
  - Status: ✅ Merged
  - Reason: Codex actionable — keep legacy_app thin proxy only. Move `_redact_rag_context_for_insight` and `_load_llm_get_provider` to canonical module (`core/insight/`) to maintain AGENTS invariant. Follow-up from PR-611.
  - Links:
    - docs/audit/PR_611_INSIGHT_SAFETY_ERROR_HYGIENE_AUDIT.md
    - PR-611 (merged 2026-01-28)
    - PR-703 (merged 2026-02-10)
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
  - Target PR: PR-637
  - Status: 🟡 In progress (PR-637)
  - Reason: Audit items labeled “Verified” must include minimal observed stdout evidence (1–3 lines) to remain reproducible and reviewable.
  - Links:
    - docs/audit/PR_Q2B_IOS_UITESTS_BUNDLE_LOAD_AUDIT.md (section F)
    - AGENTS.md (Verification-audit rule)
  - DoD:
    - Add a short, canonical checklist line for audit PRs: include 1–3 raw stdout lines + exit code for each key verification command
    - No scope creep into runbook-level detail

- [x] Stabilize AnimationTests.swift (iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-681
  - Status: ✅ Merged (PR-681, 2026-02-07)
  - Reason: Root cause: `PBXFileSystemSynchronizedBuildFileExceptionSet.membershipExceptions` excluded `AnimationTests.swift` from `PulsePlateTests`. Fix: removed `AnimationTests.swift` from `membershipExceptions` so the tests are included in `PulsePlateTests` again.
  - Links:
    - ios/PulsePlateTests/AnimationTests.swift
    - ios/PulsePlate.xcodeproj/project.pbxproj
    - ios/AGENTS.md (Animated/UI helper tests policy)
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/681>
  - DoD:
    - Either rewrite using available public components
    - Or extract to separate test target
    - Or remove if dead test code (no longer needed)
    - AnimationTests.swift compiles without errors
    - All referenced types/modifiers are accessible (public/internal as needed)
    - Tests restored to PulsePlateTests target (if kept)
    - CI green with AnimationTests included (if restored)

- [x] Fix ShoppingPlan public API (make nested types public or narrow API surface)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-677
  - Status: ✅ Merged (PR-677, 2026-02-07)
  - Reason: CodeRabbit flagged "ShoppingPlan isn't constructible" - public type with internal nested types (DailyMenu, Meal). Outside PR-559 scope but architectural smell.
  - Links:
    - ios/PulsePlate/Models/ShoppingList/ShoppingListStubPlan.swift
    - CodeRabbit comment (outside diff, actionable=0)
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/677>
  - DoD:
    - Either make DailyMenu/Meal public with explicit init
    - Or narrow API: make ShoppingPlan/ShoppingListRequestPayload internal if it's "stub" only
    - No breaking changes to existing usage

- [x] Wire soft paywall CTA to real paywall router (iOS) — ✅ Merged (PR-674, 2026-02-07)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-674
  - Status: ✅ Merged (PR-674, 2026-02-07)
  - Reason: Soft paywall CTA is wired to a real paywall navigation handler and presents a minimal paywall screen.
  - Links:
    - ios/PulsePlate/Screens/BMICalculatorScreen.swift (line ~73)
    - docs/audit/PR_674_IOS_SOFT_PAYWALL_CTA_ROUTER_AUDIT.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/674>
  - DoD:
    - Paywall router/navigation handler implemented
    - SoftPaywallHookView CTA wired to navigation
    - No TODO comments in production code
- [ ] Optional: CI script guard for iOS (repo-wide scan)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
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
  - Priority: P1
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

- [x] API Tiers database lookup implementation
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-721
  - Status: ✅ Merged (PR-721, 2026-02-12)
  - Priority: P1
  - Area: backend
  - Finding Type: TODO/FIXME
  - Locations:
    - `app/middleware/api_tiers.py` — DB lookup + env fallback (MISS only); ERROR/INVALID_TIER fail-closed
  - Reason: Previously env-only; now DB-first when SUBSCRIPTION_DB_ENABLED=true with explicit fail-closed policy.
  - Links:
    - docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md
    - docs/audit/PR_XXX_API_TIERS_DB_LOOKUP_AUDIT.md (audit in PR-721)
  - DoD:
    - Database lookup implemented when SUBSCRIPTION_DB_ENABLED=true ✅
    - Fallback to env-based detection only on DB MISS (not on ERROR/INVALID_TIER) ✅
    - Tests cover both paths ✅

- [x] Greenlight iOS P0 report-only workflow
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-722
  - Status: ✅ Merged (PR-722, 2026-02-12)
  - Priority: P0
  - Area: CI / iOS
  - Reason: Add report-only App Store readiness scan for iOS in CI.
  - Links:
    - docs/audit/PR_722_GREENLIGHT_INTEGRATION_AUDIT.md
    - docs/runbook/IOS_GREENLIGHT.md
  - DoD:
    - Workflow `.github/workflows/greenlight-ios.yml` path-scoped ✅
    - Report artifact + step summary ✅
    - P0 report-only documented ✅

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

### Home+Plate+Progress design execution follow-up

- [ ] Figma slice structure absent in current Make file
  - Owner: @katsiaryna_kavaleuskaya (Design + FE + iOS)
  - Target PR: PR1/Follow-up
  - Priority: P2
  - Status: ▶️ In progress (Unblocked: Figma seat `Full`, 2026-02-17)
  - Area: design / ios / frontend
  - Finding Type: deferred execution
  - Reason: PR_781 defines the blueprint and keeps docs scope; execution
    continues as a follow-up work package in Figma file
    `<FIGMA_MAKE_FILE_ID>`.
  - Links:
    - `docs/audit/PR_781_HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md`
    - `https://www.figma.com/make/<FIGMA_MAKE_FILE_ID>/Untitled`
  - DoD:
    - Pages created: `00_Foundation_Tokens`, `01_Components`,
      `10_iOS_Home`, `11_iOS_Plate`, `12_iOS_Progress`,
      `20_Web_Parity`
    - Component set created in `01_Components` per audit runbook
    - Naming convention `PP/<Platform>/<Screen>/<Component>/<State>`
      applied consistently
    - Follow-up implementation PR merged with evidence
      (screenshots/links) and this ledger item closed

- [ ] Design file URL + node IDs required for Code Connect activation (H+P+Pr)
  - Owner: @katsiaryna_kavaleuskaya (Design + FE + iOS)
  - Target PR: PR/Figma-CodeConnect-Activation
  - Priority: P1
  - Status: 🔒 Blocked by dependency
  - Area: design / frontend / iOS
  - Finding Type: integration dependency
  - Reason: Make-only mode is enough for reconciliation and candidate mapping, but
    node-level Code Connect cannot be activated without Design file key and node IDs.
  - Links:
    - `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
    - `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
    - `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
    - `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
  - DoD:
    - Figma Design file URL is recorded in repo docs
    - P0 CTA nodes have non-TBD `fileKey` and `nodeId`
      (`web.home.open_setup`, `web.plate.premium_gate_cta`,
      `web.progress.export_pdf`, `ios.plate.issue_action_dynamic`)
    - `get_code_connect_map` returns expected active mappings for P0 set
    - Matrix `Figma Node ID` column updated for activated rows

### Multimodal / CV / measurement (future, contract-first)

- [ ] CV (photo → food): contract schema + uncertainty/degrade UX states + privacy packet
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: product / AI / contracts
  - Finding Type: future feature
  - Reason: If we add photo-based food recognition, it must be contract-first and uncertainty-aware
    (confidence fields, nullability, deterministic degrade states) with explicit privacy UX and retention rules.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (cv-contract-agent role; degrade-state expectations)
    - `app/schemas/` (canonical schema patterns)
    - `frontend/src/api/schema.ts` (OpenAPI consumer)
  - DoD:
    - Proposed response schema includes: items[], per-item confidence, portion estimate + uncertainty range, warnings[], metadata
    - Deterministic UX state mapping defined for confidence bands (show/confirm/suggest/manual entry)
    - Privacy packet drafted (consent copy, retention, opt-out) and reviewed for wellness-safe wording
    - Deterministic test plan exists (fixtures + expected ranges; no flake)

- [ ] Sensor invariants: physically-plausible bounds + calibration UX contract (no “magic sizing”)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: product / measurement / UX safety
  - Finding Type: future feature
  - Reason: Portion/measurement features must enforce physical constraints (units, bounds, drift) and communicate
    uncertainty explicitly; calibration UX must be deterministic and non-misleading.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (sensor-invariant-guard role)
  - DoD:
    - Measurement invariants documented (bounds, units, reject conditions)
    - Calibration UX steps defined (scale + camera reference object) with explicit failure modes
    - Guard policy defined: unphysical outputs rejected; uncertainty increases with degraded signals

- [ ] Algorithmic brand textures (seeded): generate onboarding/ASO backgrounds with reproducible seeds
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: design / marketing assets
  - Finding Type: tooling
  - Reason: Branded generative textures can speed up “polished but minimal” visuals for onboarding, empty states,
    and ASO packs, while staying reproducible via seeded parameters.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (how to add new specialist agents)
  - DoD:
    - A single seeded generator exists (deterministic for the same seed) with exportable PNG outputs
    - Output palette matches brand tokens and supports light/dark variants
    - Usage notes: never encode text in images; keep wellness-safe tone

### Orchestration Enhancements (follow-ups to PR-634)

- [ ] Agent Context Cache (avoid re-loading AGENTS.md)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: productivity
  - Reason: Coordinator repeatedly re-loads the same canonical context files (root/module `AGENTS.md`, runbook, orchestration docs).
  - Links:
    - docs/orchestration/AGENT_CONTEXT_MAP.md
    - docs/orchestration/workflow.md
  - DoD:
    - Coordinator has an explicit caching strategy (doc or lightweight tool) for stable context inputs
    - Cache invalidation rules documented (file change / branch change)

- [ ] Orchestration Telemetry (metrics)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: observability
  - Reason: We have no visibility into orchestration performance (agents used, iterations, sync points, end-to-end time).
  - Links:
    - docs/orchestration/PARALLEL_WORK_PROTOCOL.md
    - docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md
  - DoD:
    - Minimal telemetry spec defined (what metrics, where recorded, retention)
    - Metrics collection does not affect runtime product behavior

- [x] Dialogue Visualization (interaction graph)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #796
  - Status: ✅ Merged (PR #796, 2026-02-18)
  - Merge SHA: `fca3d6e7e2f2ab40a2cc4222e4330a30456e1a0b`
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: tooling
  - Reason: Multi-agent dialogue is hard to audit without a visual interaction graph.
  - Links:
    - PR #796: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/796>
    - docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md
    - docs/orchestration/workflow.md
    - docs/plan/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_TASK_ANALYSIS.md
    - docs/plan/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_EXECUTION_PLAN.md
    - docs/audit/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_BRAINSTORMING.md
    - docs/audit/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_AUDIT.md
    - docs/audit/PR_ORCHESTRATION_DIALOGUE_VISUALIZATION_PR_BODY_SKELETON.md
  - DoD:
    - Mermaid output format defined (inputs + expected diagram)
    - Example visualization added to orchestration docs or runbook

- [ ] Auto-verification script (Pre-flight Checklist)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: automation
  - Reason: Pre-flight Checklist is manual; automation can fail-fast on missing required context.
  - Links:
    - docs/orchestration/AGENT_CONTEXT_MAP.md
    - .cursor/agents/agent-coordinator.md
  - DoD:
    - A script/tool verifies required context files are present and referenced correctly
    - Failure mode is explicit and does not block unrelated tasks (scoped to orchestration workflow)

- [x] Test skips cleanup (low priority batch) — superseded by PR-728 classification
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-728
  - Priority: P2
  - Status: ✅ Superseded (2026-02-13)
  - Area: backend / tests
  - Finding Type: skip/xfail
  - Reason: Replaced by prioritized split into P0/P1 stabilization tracks and explicit product-decision backlog.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `docs/audit/PR_585_BACKLOG_SWEEP_AUDIT.md`
  - DoD:
    - Superseded by targeted items: PR-729, PR-730, PR-731, PR-732
    - Intentional product-scope skips tracked separately (no mixed bucket)

- [ ] P2: Product decision for removed/non-canonical optional fields in skip tests
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-749 (ui_labels contract), PR-733 (remaining fields)
  - Status: 🟡 In progress (PR-749)
  - Priority: P2
  - Area: backend / product contract
  - Finding Type: intentional-scope decision
  - Locations:
    - `tests/test_app_coverage_unit_combined.py:83`
    - `tests/test_app_coverage_unit_combined.py:88`
    - `tests/test_premium_targets_es_snapshots.py:453`
  - Reason: `ui_labels` contract is being promoted to required in PR-749; `interpret_group` / `estimate_level` still need explicit product-contract decisions.
  - Links:
    - `docs/audit/SKIPPED_TESTS_CLASSIFICATION_AUDIT_2026-02-13.md`
    - `app/schemas/premium_contracts.py:109`
  - DoD:
    - Product decision recorded for each field/function (restore canonical equivalent vs remove obsolete tests)
    - No ambiguous intentional skips remain without decision record

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
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (Migration status by domain)
  - DoD:
    - All clients migrated to canonical endpoints
    - Deprecated endpoints removed
    - OpenAPI updated (no deprecated paths)

- [ ] P2: Complete legacy_app.py migration (delete legacy endpoints)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (v2.0 timeline, after all migrations)
  - Priority: P2 (long-term cleanup)
  - Reason: After all critical security fixes and endpoint migrations complete, eventually delete `legacy_app.py` entirely. All logic should be in modular routers (`app/routers/*`) and core modules (`core/*`). Current state: 5382 lines, ~60% migrated.
  - Links:
    - docs/audit/LEGACY_APP_MIGRATION_STATUS.md (overall progress, migration status)
    - docs/pr/PR_THIN_PROXY_CLEANUP_PLAN.md
  - Prerequisites:
    - ✅ All P0 security fixes complete (rate-limiting, tier guards)
    - ✅ All P1 migrations complete (constants extracted, WebSocket secured)
    - ✅ All clients migrated to canonical endpoints
    - ✅ Legacy endpoint traffic < 1%
  - DoD:
    - All endpoints migrated to modular routers
    - All helpers moved to canonical modules
    - `legacy_app.py` deleted (or reduced to minimal compatibility shim)
    - Tests pass (no functionality broken)
    - OpenAPI unchanged (all canonical endpoints present)

- [x] PR-570 (Phase 3): Agent index + model selection rationale — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-570
  - Status: ✅ Merged
  - Links:
    - docs/audit/PR_567_AGENT_INDEX_AUDIT.md
    - docs/agents/index.md

- [ ] P2 Vision: Nutrition coaching (CBT in nutrition, weight loss/gain)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (product/feature design first)
  - Priority: P2 (product direction; preferred over ML training platform for current scope)
  - Reason (EN): Product differentiation via cognitive-behavioral psychology in nutrition: goals, reflection, habits, support for slips/weight gain. Does not require ML training platform; leverages LLM/RAG and existing user data. **Integration with philosophy and math:** CBT coaching flows can be validated through philosophical principles (syllogisms, verification) and enhanced with Bayesian predictions for proactive intervention. (RU: цели, рефлексия, привычки, поддержка при срывах/наборе веса. Не требует платформы для обучения моделей; опирается на LLM/RAG и существующие данные пользователя. **Интеграция с философией и математикой:** CBT coaching flows могут быть валидированы через философские принципы (силлогизмы, верификация) и улучшены байесовскими предсказаниями для проактивного вмешательства.)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified analysis: CBT + philosophy + Bayesian integration, structured coaching flows)
    - docs/design/NUTRITION_COACHING_DESIGN.md (component links, implementation approach)
    - core/insight/creative_scientific_innovations.md (FitChef, AI companion)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md (insight, RAG)
  - DoD:
    - Product spec: coaching scenarios (goals, weekly reflections, behavioral steps) — EN: structured scenarios (goal-setting dialogues, weekly reflections, slip analysis)
    - Component links documented in design doc (see NUTRITION_COACHING_DESIGN.md)
    - Implementation — separate PRs after backend/VIP stabilization

- [ ] P2 Vision: Future — social network for nutrition/weight/support
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: N/A (separate product/project in perspective)
  - Priority: P2 (long-term vision)
  - Reason (EN): Possible separate product: community around nutrition, weight goals, mutual support. Not in current PulsePlate scope; considered as prospect after strengthening coaching and core app. (RU: Возможный отдельный продукт: комьюнити вокруг питания, целей по весу, взаимоподдержка. Не входит в текущий scope PulsePlate; рассматривается как перспектива после укрепления коучинга и ядра приложения.)
  - Links:
    - docs/design/NUTRITION_COACHING_DESIGN.md (Future social network — links section)
    - BACKLOG_LEDGER (Nutrition coaching — natural predecessor)
  - DoD:
    - Decision "do / don't do" and product boundaries (separate app vs section in PulsePlate) — after coaching launch

- [ ] P2 Vision: Restaurant/chef integration (partners accept menus from our products, cook for users)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (separate product block; after VIP/export stabilization)
  - Priority: P2 (long-term product direction)
  - Reason (EN): Restaurants and individual chefs accept menus from our products (weekly plan, recipes, constraints) and cook food for users. Separate block from coaching and social network; requires clear "menu → partner" contract and technical prerequisites in program (see RESTAURANT_INTEGRATION_SPEC.md). (RU: Рестораны и индивидуальные повара принимают меню по нашим продуктам (недельный план, рецепты, ограничения) и готовят еду пользователям. Отдельный блок от коучинга и соцсети; требует чёткого контракта «меню → партнёр» и технических предпосылок в программе.)
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md (technical prerequisites, contract schema, implementation plan)
    - app/routers/plan_export.py, vip.py (weekly plan, recipes, export)
    - core/dietary_constraints.py, core/targets.py
  - Prerequisites:
    - ✅ VIP weekly plan stable (`vip.py`, `premium_week.py`)
    - ✅ Export infrastructure exists (`plan_export.py`, `shoplist_export.py`)
    - ✅ Dietary constraints module stable (`core/dietary_constraints.py`)
    - ⏳ Backend/VIP stabilization complete (P0)
  - DoD:
    - Product spec: scenario "user sends menu to restaurant/chef" (what partner sees, how confirms) — EN: documented user flow and partner UX
    - Technical prerequisites documented in design spec (export format, consent, contract schema)
    - Implementation — separate PRs (export format, partner API or signed link, optionally partner directory)

---

- [ ] P2: Cross-feature synergies implementation (real-time + automation + community)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (strategic integration)
  - Target PR: TBD (multiple PRs for different synergies)
  - Status: 📋 Planned
  - Reason: 12 new synergies identified between planned features (WebSocket + Coaching, CV + Restaurant, Bayesian + WebSocket, etc.). These create unified user experiences and competitive advantages. Implementation should follow recommended order: real-time foundation → coaching enhancement → automation pipeline → community features.
  - Links:
    - docs/insights/CROSS_FEATURE_SYNERGIES.md (synergy matrix, implementation order, expected impact)
    - docs/design/NUTRITION_COACHING_DESIGN.md
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/audit/WEBSOCKET_ANALYSIS.md
  - Prerequisites:
    - ✅ WebSocket implemented (P1)
    - ✅ Nutrition coaching implemented (P2)
    - ✅ Restaurant integration implemented (P2)
    - ✅ CV food recognition implemented (P1)
  - DoD:
    - Real-time foundation complete (WebSocket + Bayesian + Gamification)
    - Coaching enhancement complete (WebSocket + RAG + Causal Inference)
    - Automation pipeline complete (CV + Restaurant + Multi-Modal)
    - Community features complete (Social Network + Gamification + Restaurant)
    - End-to-end user journeys documented and tested

- [ ] P1: Philosophical logic principles for LLM reliability (Aristotelian, Analytical, Post-Analytical, Linguistic)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (high impact on reliability)
  - Target PR: TBD (implementation after design review)
  - Status: 📋 Design Complete
  - Reason (EN): Apply classical logic and philosophical principles to improve LLM response reliability and argumentative rigor. Expected impact: reduce contradictions from ~15% to <2%, unverifiable claims from ~30% to <5%, contextually irrelevant responses from ~25% to <10%. Four frameworks: Aristotelian logic (syllogisms, non-contradiction), Analytical philosophy (verification, falsification), Post-analytical philosophy (pragmatic validation, hermeneutics), Linguistic philosophy (speech acts, language games, meaning-as-use). **Speed optimization:** Philosophical principles also optimize speed (50-60% latency reduction) through adaptive depth, early stopping, and query classification. (RU: Применение классической логики и философских принципов для улучшения достоверности ответов LLM и доказательности аргументации. Ожидаемый эффект: снижение противоречий с ~15% до <2%, непроверяемых утверждений с ~30% до <5%, контекстуально нерелевантных ответов с ~25% до <10%. **Оптимизация скорости:** Философские принципы также оптимизируют скорость (снижение latency на 50-60%) через адаптивную глубину, раннее прекращение и классификацию запросов.)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified analysis: philosophy + math + CBT integration)
    - docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md (comprehensive design, code examples, implementation roadmap)
    - docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md (speed optimization using philosophical principles: speech acts, language games, early stopping, adaptive depth)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md (current LLM/RAG implementation)
    - core/insight/creative_scientific_innovations.md (AI assistant design)
  - Prerequisites:
    - ✅ Current LLM/RAG infrastructure stable (`llm.py`, `core/rag/simple_rag.py`)
    - ✅ Insight endpoints stable (`legacy_app.py`, `app/routers/vip.py`)
    - ⏳ Fact-checking system implemented (P0 from LLM_RAG_AI_ASSISTANT_ANALYSIS.md)
  - DoD:
    - Phase 1: Aristotelian logic implemented (syllogistic prompts, contradiction detection)
    - Phase 2: Analytical philosophy implemented (verification, falsification)
    - Phase 3: Post-analytical philosophy implemented (pragmatic validation, hermeneutics)
    - Phase 4: Linguistic philosophy implemented (speech acts, language games)
    - Phase 5: Integrated framework complete (unified prompt builder + validator)
    - **Speed Optimization Phase:** Speech act classification (50-70% reduction for commands), language game detection (50-60% reduction for medical), early stopping (30-50% reduction), adaptive depth (50-60% average reduction)
    - Validation metrics: contradiction rate <2%, verification rate >95%, pragmatic utility >90%
    - Performance metrics: latency reduction 50-60% average, quality maintained ≥95%
    - Integration tests pass (end-to-end philosophical validation + speed optimization pipeline)

- [ ] P1: Recursive methods for LLM/RAG/AI assistant (multi-hop retrieval, recursive reasoning, self-refinement, self-verification, learning)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (high impact on quality and accuracy)
  - Target PR: TBD (implementation after design review)
  - Status: 📋 Design Complete
  - Reason (EN): Implement recursive methods to dramatically improve LLM/RAG reliability and AI assistant capabilities. Five recursive techniques: recursive retrieval (multi-hop RAG with query refinement, 40-60% retrieval quality improvement), recursive reasoning (chain-of-thought, tree-of-thought, decomposition, 25-35% answer accuracy improvement), recursive refinement (self-critique and iterative improvement, 30-40% answer quality improvement), recursive verification (self-validation through recursive queries, reduces factual errors from ~15% to <5%), recursive learning (self-improvement from user feedback, adaptive personalization). Expected overall impact: retrieval quality 85-90%, answer accuracy 85-90%, factual errors <5%, user satisfaction 85-90%. (RU: Внедрение рекурсивных методов для значительного улучшения надежности LLM/RAG и возможностей AI ассистента. Пять рекурсивных техник: рекурсивный retrieval (multi-hop RAG с уточнением запросов, улучшение качества retrieval на 40-60%), рекурсивное рассуждение (chain-of-thought, tree-of-thought, декомпозиция, улучшение точности ответов на 25-35%), рекурсивное уточнение (самокритика и итеративное улучшение, улучшение качества ответов на 30-40%), рекурсивная верификация (самопроверка через рекурсивные запросы, снижение фактических ошибок с ~15% до <5%), рекурсивное обучение (самоулучшение на основе обратной связи пользователей, адаптивная персонализация).)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified analysis: philosophy + math + CBT integration, recursive methods with philosophical validation)
    - docs/insights/RECURSIVE_METHODS_LLM_RAG.md (comprehensive design, code examples, implementation roadmap, expected impact)
    - docs/insights/RECURSIVE_OPTIMIZATION_STRATEGY.md (optimization strategies: parallelization, caching, batching, open-source libraries)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md (current RAG implementation: `core/rag/simple_rag.py`)
    - docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md (complements recursive verification)
    - core/rag/simple_rag.py (current single-pass keyword-based RAG)
  - Prerequisites:
    - ✅ Current RAG infrastructure stable (`core/rag/simple_rag.py`)
    - ✅ LLM provider stable (`llm.py`)
    - ✅ Redis available in docker-compose (for caching optimization)
    - ⏳ Fact-checking system implemented (for recursive verification)
    - ⏳ User feedback storage implemented (for recursive learning)
  - DoD:
    - Phase 1: Recursive RAG implemented (multi-hop retrieval, query refinement)
    - Phase 2: Recursive reasoning implemented (decomposition, synthesis, tree-of-thought)
    - Phase 3: Recursive refinement implemented (self-critique, iterative improvement)
    - Phase 4: Recursive verification implemented (self-validation, claim checking)
    - Phase 5: Recursive learning implemented (feedback analysis, prompt refinement)
    - Phase 6: Integrated recursive framework complete (`RecursiveAIAssistant`)
    - **Optimization Phase:** Parallelization (asyncio.gather), GPTCache integration, Redis caching, batch verification (reduce latency from 2-3x to 1.2-1.5x)
    - Performance metrics: retrieval quality ≥85%, answer accuracy ≥85%, factual errors ≤5%, latency ≤1.5x baseline
    - Cost optimization: caching, parallelization, early stopping (3-5x LLM calls acceptable, reduced to 1.5-2x with caching)
    - Integration tests pass (end-to-end recursive pipeline)

- [ ] P2: Unified Framework implementation (UnifiedAICoach: Philosophy + Math + CBT integration)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (integration of all components after individual implementations)
  - Target PR: TBD (implementation after Phase 1-4 components are complete)
  - Status: 📋 Planned (depends on Philosophical logic + Recursive methods + CBT coaching)
  - Reason (EN): Integrate all components (Philosophical validation, Recursive methods, Bayesian personalization, CBT coaching) into a unified production-ready framework. Expected impact: multiplicative quality gains (70-80% improvement), latency optimization (50-60% reduction), unified user experience. **Production readiness:** Framework includes rate-limiting, caching, monitoring, error handling, privacy protection, and fallback mechanisms as documented in peer review analysis. (RU: Интеграция всех компонентов (философская валидация, рекурсивные методы, байесовская персонализация, CBT coaching) в единый production-ready фреймворк. Ожидаемый эффект: мультипликативное улучшение качества (70-80%), оптимизация latency (50-60%), единый пользовательский опыт. **Production readiness:** Фреймворк включает rate limiting, caching, monitoring, error handling, privacy protection и fallback механизмы, как документировано в peer review analysis.)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified framework architecture, Phase 5 roadmap, production deployment)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (production-ready architecture blueprint, implementation details, risk mitigations)
    - docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md (philosophical validation components)
    - docs/insights/RECURSIVE_METHODS_LLM_RAG.md (recursive methods components)
    - docs/design/NUTRITION_COACHING_DESIGN.md (CBT coaching flows)
  - Prerequisites:
    - ✅ Phase 1: Philosophical validation implemented (P1 backlog item)
    - ✅ Phase 2: Speed optimization implemented (LinguisticOptimizer, caching)
    - ✅ Phase 3: Recursive methods implemented (P1 backlog item)
    - ✅ Phase 4: CBT coaching implemented (P2 backlog item)
    - ⏳ All individual components tested and stable
  - DoD:
    - Phase 5: UnifiedAICoach class implemented (orchestrates all components)
    - All components integrated (PhilosophicalValidator, RecursiveRAG, RecursiveReasoner, Refiner, Verifier, BayesianPersonalizer, CBTCoachingFlow)
    - Production-ready features: rate-limiting, caching (GPTCache + Redis), monitoring (Prometheus), error handling, privacy protection, fallback mechanisms
    - End-to-end testing complete (all user query types: QUESTION, COMMAND, REQUEST, EXPRESSION)
    - Performance metrics: latency ≤0.8s (P95) for QUESTION queries, ≤0.3s for COMMAND/EXPRESSION, verification rate ≥95%, factual error rate <3%
    - Cost optimization: ≤$0.008 per query (VIP tier), cache hit-rate ≥50%
    - Documentation: production deployment guide, monitoring setup, troubleshooting runbook
    - **Production deployment:** Framework deployed to production with feature flag (gradual rollout)

- [ ] P2 Optional: Evaluate PEP 751 standard lock file (pylock.toml) and/or uv + Dependabot
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional tooling improvement)
  - Target PR: TBD (evaluation first, then migration if beneficial)
  - Status: 📋 Planned
  - Reason (EN): Python ecosystem 2026: PEP 751 defines standard lock format (pylock.toml); Dependabot now supports uv. Current repo uses pip-tools (requirements.txt as lock) and pip in Dependabot — no mandatory change. Optional: evaluate migrating to standard lock file and/or uv when tooling/CI support is stable. Setuptools: we use it only as pinned dependency (security); no setup.cfg — setuptools 78.x deprecations do not affect us. (RU: Экосистема Python 2026: PEP 751 — стандартный lock-файл; Dependabot поддерживает uv. Сейчас: pip-tools + requirements.txt как lock, Dependabot на pip. Опционально: оценить переход на pylock.toml и/или uv. Setuptools: только как зависимость в requirements; setup.cfg нет — депрекации 78.x нас не затрагивают.)
  - Links:
    - docs/audit/PYTHON_SETUPTOOLS_LOCKFILE_AUDIT.md (full audit: setuptools usage, lock file strategy, Dependabot/uv)
    - REQUIREMENTS.md (current pip-compile workflow)
    - .github/dependabot.yml (pip ecosystem)
  - DoD:
    - Decision documented: adopt / defer / won't do for PEP 751 and for uv
    - If adopt: migration PR with updated REQUIREMENTS.md and CI; Dependabot config updated if uv adopted

- [ ] P2 Optional: Evaluate NVIDIA PersonaPlex for voice persona layer (assistant / coach)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; depends on voice UX roadmap)
  - Target PR: TBD (evaluation first, then integration if approved)
  - Status: 📋 Planned
  - Reason (EN): PersonaPlex (open-source, NVIDIA) provides full-duplex speech-to-speech, persona switching, and backchannel for a "live" conversational feel. Fit: personalize AI assistant and nutrition coach by style (e.g. strict teacher, friendly consultant); optional voice mode. Current stack is text-only; PersonaPlex would be additive (voice layer). Prerequisites: NVIDIA GPU or hosted API, NVIDIA Open Model License, WebSocket/streaming for real-time audio. (RU: PersonaPlex (NVIDIA, open-source) — full-duplex S2S, переключение персон, поддакивания; можно использовать для персонализированного ассистента и коуча. Сейчас у нас только текст; голос — опционально.)
  - Links:
    - docs/audit/PERSONAPLEX_INTEGRATION_AUDIT.md (integration options, prerequisites, risks)
    - <https://huggingface.co/nvidia/personaplex-7b-v1>
    - <https://github.com/NVIDIA/personaplex>
    - docs/design/NUTRITION_COACHING_DESIGN.md (coach flows)
    - core/insight/creative_scientific_innovations.md (FitChef)
  - Prerequisites:
    - Voice UX / real-time audio on product roadmap (or explicit decision to prototype)
    - Inference option: GPU (A100/H100) or hosted API; license accepted
  - DoD:
    - Decision documented: adopt / defer / won't do for PersonaPlex voice layer
    - If adopt: persona prompts aligned with FitChef/coach; voice API (e.g. WebSocket) and security/privacy documented

- [ ] P2 Optional: Evaluate Lenny's Podcast Transcripts for insights, marketing, and Bayesian context
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; after P0/P1 hardening and insight/coach work stable)
  - Target PR: TBD (evaluation first: curated doc vs RAG subset vs MCP)
  - Status: 📋 Planned
  - Reason (EN): Lenny's Podcast Transcripts (269 episodes, 50+ topics) provide product/growth/PMF/leadership advice from world-class PM and growth experts. Fit: enrich insights docs, marketing-strategist playbooks, Bayesian business analyzer prior/context, FitChef RAG, and nutrition coaching design. Options: (1) curated references doc, (2) RAG subset with citation, (3) MCP or internal API. License: personal/educational; internal use with attribution is low risk. (RU: Транскрипты Lenny's Podcast — продукт/рост/PMF/лидерство; можно использовать для инсайтов, маркетинга, байесовского контекста и FitChef/коучинг.)
  - Links:
    - docs/audit/LENNYS_PODCAST_INTEGRATION_AUDIT.md (mapping to insights, Bayesian, marketing, FitChef; integration options)
    - <https://github.com/ChatPRD/lennys-podcast-transcripts>
    - core/insight/analysis_insights.md
    - core/insight/creative_scientific_innovations.md
    - .cursor/agents/marketing-strategist.md
  - DoD:
    - Decision documented: adopt one option (curated doc / RAG subset / MCP) or defer / won't do
    - If adopt: implementation steps and attribution policy documented; no scope creep into P0/P1

- [ ] P2 Optional: Use Loot Drop (Startup Graveyard) as periodic anti-pattern checklist
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; before major bets or post-launch reviews)
  - Target PR: N/A (process: run checklist, update audit if new risks)
  - Status: 📋 Planned
  - Reason (EN): Loot Drop (loot-drop.io) catalogs 925+ failed VC-backed startups with structured failure analysis (product, competition, pricing, lost focus, marketing, cash, legal/regulatory, etc.). Health/BioTech failures are 94% legal/regulatory. Use as anti-pattern checklist to avoid repeating epic fails: e.g. LLM cost burn, scope creep, wellness vs medical positioning. (RU: «Кладбище стартапов» — уроки провалов; чеклист по 10 категориям и revival themes для снижения рисков.)
  - Links:
    - docs/audit/LOOT_DROP_STARTUP_GRAVEYARD_AUDIT.md (risk matrix, PulsePlate mapping, recommendations)
    - <https://www.loot-drop.io/>
    - <https://www.loot-drop.io/insights.html>
    - core/insight/analysis_insights.md (Lessons from failed startups subsection)
  - DoD:
    - Before major product/GTM bets or post-launch review: run through Loot Drop 10 categories + revival themes
    - Update LOOT_DROP_STARTUP_GRAVEYARD_AUDIT.md if new risks or mitigations identified

- [ ] P2 Optional: Use curated repos (Frontend/UI, AI/LLM, RAG, Multimodal, MCP, ML/CV) as learning and reference
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; when implementing RAG upgrade, multimodal pipeline, or frontend components)
  - Target PR: N/A (reference only; adopt patterns/libraries via normal PR)
  - Status: 📋 Planned
  - Reason (EN): Curated set (22 repos): Flexbox Froggy, shadcn/ui, 50projects50days, Awesome React/CSS; LLaVA, CLIP, Transformers, Awesome Multimodal ML, RAG from Scratch, Awesome LLM Apps, LLM Engineer Handbook; MCP Python SDK; Awesome ML/CV, ZenML; Qwen/Qwen-Finetuning; Spinning Up, Sutton&Barto RL; PyTorch, Awesome Generative AI. Map to our vision: RAG (RAG from Scratch, Awesome LLM Apps), multimodal/FitChef (LLaVA, CLIP, Transformers), frontend (shadcn, Awesome React), MCP (python-sdk), CV (Awesome CV, PyTorch). (RU: Закладки для RAG, multimodal, фронта, MCP, ML/CV; использовать при реализации фич.)
  - Links:
    - docs/insights/CURATED_REPOS_REFERENCE.md (full mapping to LLM_RAG, CV_ML, creative_scientific_innovations, RECURSIVE_METHODS, COMPREHENSIVE)
    - core/insight/creative_scientific_innovations.md (Curated repos reference subsection)
  - DoD:
    - When designing RAG upgrade, multimodal pipeline, or UI: consult CURATED_REPOS_REFERENCE.md for relevant repos
    - No mandatory code dependency; adopt via normal PR/backlog

- [ ] P2: Bayesian adherence prediction and uncertainty quantification (VIP differentiator)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (after P0/P1 hardening; unique competitive advantage)
  - Target PR: TBD (design first: core/bayesian/adherence.py, uncertainty intervals)
  - Status: 📋 Planned
  - Reason (EN): Probabilistic personalization: P(adherence | user_context) for adaptive meal plans; confidence intervals for targets (e.g. "1800–2200 kcal, 90% confidence") instead of point estimates. Differentiator vs MyFitnessPal/Cronometer (static calculators). Prerequisites: Bayesian module design, calibration metrics (Brier score). (RU: Байесовская персонализация и доверительные интервалы для целей; уникальное конкурентное преимущество.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: Bayesian, uncertainty, roadmap)
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (Bayesian + CBT integration)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (uncertainty quantification gap)
    - core/insight/creative_scientific_innovations.md (FitChef personalization)
  - DoD:
    - Design: core/bayesian/adherence.py (or equivalent) with probabilistic adherence model
    - VIP targets expose confidence intervals where applicable (e.g. calorie range, 90% CI)
    - Calibration metric documented (e.g. Brier score); no regression on existing FREE/PRO contracts

- [ ] P2: Recursive optimization for weekly meal plans (speed + scalability)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (when VIP weekly plan performance is in scope)
  - Target PR: TBD (implementation after design)
  - Status: 📋 Planned
  - Reason (EN): Reduce weekly plan generation from 10–30s to 2–5s via divide-and-conquer (split week into halves, optimize recursively, merge with boundary constraints). Lazy day generation: first day instant, remaining days on-demand. Recursive nutrient aggregation O(n log n) for shoplist. (RU: Рекурсивная оптимизация недельных планов и агрегации нутриентов; скорость и масштабируемость.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: recursive week planning, lazy days)
    - docs/insights/RECURSIVE_OPTIMIZATION_STRATEGY.md (optimization strategies, code patterns)
    - docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md (bottlenecks: meal plan, shoplist)
    - docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md (lazy evaluation, early stopping)
    - app/routers/vip.py (current weekly plan flow)
  - DoD:
    - Design: recursive week planning and/or lazy day generation documented
    - Implementation: measurable latency improvement (e.g. time-to-first-day, full week)
    - No regression on constraint satisfaction or nutrition targets

- [ ] P2: Cross-feature integration tests (BMI → Sports → Shoplist flows)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality assurance; prevent regressions)
  - Target PR: TBD (tests only)
  - Status: 📋 Planned
  - Reason (EN): Unit tests exist; integration tests across feature boundaries are weak. Add end-to-end flows: BMI → sport nutrition → shoplist; recipe synthesis → regional catalog → shoplist. Aligns with CROSS_FEATURE_SYNERGIES and PEER_REVIEW_ANALYSIS gap. (RU: Интеграционные тесты кросс-фичевых сценариев.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: cross-feature flows)
    - docs/insights/CROSS_FEATURE_SYNERGIES.md (synergy matrix, flows)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (cross-feature testing gap)
    - tests/ (existing unit/integration structure)
  - DoD:
    - At least one cross-feature flow tested (e.g. BMI → sport targets → plan → shoplist)
    - Tests run in CI; no new flakiness; documented in tests/AGENTS.md or RUNBOOK

- [ ] P2 Optional: Evaluate scientific publication track (Bayesian, CBT, recursive algorithms)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional; credibility + PR; after core innovations shipped)
  - Target PR: N/A (decision + optional draft)
  - Status: 📋 Planned
  - Reason (EN): Optional papers: Bayesian adherence for personalized nutrition (NeurIPS/ML4H workshop), CBT-aligned gamification vs anxiety (CHI), recursive constraint satisfaction for meal planning (AAAI). Benefit: credibility, press, talent attraction. Effort: 3–6 months per paper; parallel to product. (RU: Опциональная научная публикация по байесовской персонализации, CBT-геймификации, рекурсивным алгоритмам планирования.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md (canonical scientific review: publication track, venues)
    - docs/insights/PEER_REVIEW_ANALYSIS.md (publishable insights)
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md
    - docs/insights/RECURSIVE_OPTIMIZATION_STRATEGY.md
  - DoD:
    - Decision documented: pursue / defer / won't do for publication track
    - If pursue: venue + outline for one paper; no mandatory timeline

---

**Last updated:** 2026-02-16 (SCIENTIFIC_INNOVATION_ANALYSIS.md canonical doc, backlog links)
**Maintainer:** @katsiaryna_kavaleuskaya
<!-- markdownlint-enable MD013 -->
