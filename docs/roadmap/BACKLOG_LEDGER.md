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

## Open Items

<!-- EXPERIMENT_BACKLOG_ENTRIES:INSERT BELOW -->

Entries are sorted by priority, then theme, then title. Theme uses `Area:` when present and a deterministic title/domain fallback otherwise.

### P0

<a id="ledger-p0-payments-ruby-ios"></a>
- [ ] P0: Payment rails for RU/BY + iOS-first monetization baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (revenue continuity)
  - Target PR: PR #983 (contract docs) -> PR #1095 (activation + persistence runtime) -> PR-TBD-BILLING-ENTITLEMENT-ROUTING
  - Status: 🟡 In progress (PR #1095 owns runtime Wave R1 activation + persisted subscription state; entitlement routing remains tracked in `ledger-p0-billing-entitlement-routing`)
  - Carryover: PR #1005 keeps only the `RUBY` -> `RU_BY` identifier cleanup so the ledger stays aligned with the existing payments contract naming.
  - Reason (EN): Current business reality requires region-adapted payment rails: iOS as primary automated channel, RU/BY payments via eRIP (QR to account) and SWIFT card transfer fallback. Canonical billing flow must support these rails before global providers expansion. (RU: Текущий источник оплат: iOS + RU/BY локальные каналы (ЕРИП/QR и SWIFT). Нужен канонический billing baseline под эту реальность до расширения на глобальные провайдеры.)
  - Links:
    - docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md
    - docs/contracts/API_CANONICAL_MAP.md
    - docs/IOS_API_INTEGRATION.md
    - docs/audit/PR_PAYMENTS_RUBY_IOS_CONTRACT_AUDIT.md
    - docs/contracts/PRODUCT_TIER_MAP.md
    - ios/PulsePlate/Services/ProKeyProvider.swift:1
    - app/routers/pro_registration.py:1
    - app/routers/pro_payments.py:1
    - app/schemas/payments.py:1
    - app/services/payments_activation.py:1
  - Prerequisites:
    - ✅ Tier activation contract exists (FREE/PRO/VIP)
    - ⏳ Unified billing activation service is finalized for source-specific receipts
  - DoD:
    - Canonical source model documented: `ios_app_store`, `erip_qr`, `swift_manual`
    - `activate_subscription()` contract supports all three sources with deterministic audit trail
    - iOS receipt verification remains automated path; RU/BY flows have explicit reconciliation status lifecycle
    - API/webhook/error contracts are tested and non-breaking for existing clients
    - Runtime test plan is locked before implementation (`test_payment_source_contract_api`, `test_subscription_activation_api`, `test_ios_receipt_verification_api`, `test_payment_webhook_signature_api`, `test_payment_reconciliation_api`)

<a id="ledger-p0-billing-activation-service"></a>
- [ ] P0: Billing activation service follow-through after Apple verify
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #1095
  - Area: backend / payments / activation
  - Finding Type: monetization chain gap
  - Reason: The verify-only PR intentionally stops before activation side effects, so the next runtime segment must consume the normalized Apple verification payload and activate paid access deterministically.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/routers/billing.py`
    - `app/services/payments_activation.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
  - DoD:
    - Activation service consumes the Apple verification contract without reintroducing client tier truth
    - Verify and activate remain separate runtime stages with deterministic handoff semantics
    - Activation-path tests cover success, replay, and failure transitions

<a id="ledger-p0-billing-subscription-persistence"></a>
- [ ] P0: Subscription persistence for billing activation outcomes
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #1095
  - Area: backend / payments / persistence
  - Finding Type: subscription state gap
  - Reason: Verification responses are activation-ready, but canonical subscription state still lacks durable persistence for user, tier, platform, expiry, and receipt-linked audit fields.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/services/payments_activation.py`
    - `app/schemas/payments.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
  - DoD:
    - Subscription state is persisted with deterministic idempotency semantics
    - Persistence schema stores canonical tier/platform/expires_at/receipt audit fields
    - Tests prove repeated activation cannot create duplicate subscription state

<a id="ledger-p0-billing-entitlement-routing"></a>
- [ ] P0: Entitlement-backed routing after billing activation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-TBD-BILLING-ENTITLEMENT-ROUTING
  - Area: backend / authz / routing
  - Finding Type: access-control gap
  - Reason: The release spine still needs entitlement truth and protected routing after activation so paid users reach the correct guarded surfaces without client-side unlock shortcuts.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/routers/billing.py`
    - `app/middleware/api_tiers.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
  - DoD:
    - Entitlement truth is derived from backend activation/subscription state
    - Route guards consume entitlement state instead of client-declared tier
    - Regression tests cover paid, expired, and missing-entitlement paths

<a id="ledger-p0-eu-compliance-control-plane-follow-through"></a>
- [ ] P0: EU-first compliance control plane follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-TBD-EU-COMPLIANCE-CONTROL-PLANE-FOLLOWTHROUGH
  - Area: backend / privacy / legal docs / AI governance
  - Finding Type: compliance program hardening
  - Reason: Foundation runtime/docs work now establishes a canonical compliance control plane (`docs/compliance/*`, `core/compliance/*`, additive `/privacy` sync), but rollout still needs one program-level epic so future privacy, transparency, DSAR, and regulated-lane work does not drift into isolated follow-ups. This epic supersedes fragmented treatment of the same theme.
  - Links:
    - `docs/compliance/README.md`
    - `docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`
    - `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
    - `docs/compliance/DSAR_AND_DELETION_MAP.md`
    - `docs/compliance/US_REGULATED_LANE_RFC_42_CFR_PART_2.md`
    - `core/compliance/privacy.py`
    - `legacy_app.py`
  - DoD:
    - `/privacy`, `docs/legal/Privacy.md`, and `core/compliance/*` remain synchronized for every new health-ish or AI surface
    - New AI or health-adjacent surfaces add transparency + minimization entries before release
    - Support-led DSAR workflow for direct-user artifacts is documented and used until a public auth-bound DSAR API is explicitly designed
    - The US regulated lane remains blocked from the wellness runtime until separate legal/compliance approval
    - Future public DSAR/export/delete endpoints are blocked until auth/ownership contract is explicit

<a id="ledger-p0-legal-policy-publish"></a>
- [ ] P0: Legal policy publish and client-link alignment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-TBD-LEGAL-POLICY-PUBLISH
  - Status: 📋 Planned
  - Area: docs / legal / release readiness
  - Finding Type: policy publication gap
  - Reason (EN): Privacy and Terms posture has been materially clarified in runtime and compliance docs, but canonical published policy paths and client references still need one explicit release-blocker item.
  - Links:
    - `docs/legal/Privacy.md`
    - `legacy_app.py`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
  - DoD:
    - Canonical privacy and terms publication paths exist in-repo
    - Web and iOS clients link to the published policy paths consistently
    - Published text stays aligned with runtime wellness/compliance posture
<a id="ledger-p0-insight-fallback-chain"></a>
- [ ] P0: Insight fallback chain + echo-mode readiness visibility
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (VIP reliability)
  - Target PR: PR-TBD-INSIGHT-FALLBACK-CHAIN
  - Status: 📋 Planned
  - Reason (EN): Master checklist items #2 and #4 require deterministic behavior when primary LLM/provider path is unavailable and explicit operator visibility for fallback/echo mode.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - llm.py
    - app/routers/vip.py
    - app/main.py
  - DoD:
    - Provider fallback order is deterministic and test-covered
    - `/ready` exposes fallback/echo-mode state without leaking secrets
    - Insight response contract remains backward-compatible under fallback


<a id="ledger-p0-master-checklist-triage"></a>
- [ ] P0: Master checklist phase-fit triage (PulsePlate_Master_Checklist v1.0)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (program alignment / scope control)
  - Target PR: PR-TBD-MASTER-CHECKLIST-TRIAGE
  - Status: 🟡 In progress (phase-fit matrix published; execution mapping in progress)
  - Reason (EN): External checklist contains valid launch concerns, but several items are release-phase only and can overload current execution wave. We need a canonical Now/Next/Later decision matrix tied to active implementation reality (food/restaurant hardening + quality-first AI track). (RU: Внешний чеклист полезен, но часть пунктов относится к релизной фазе и не должна ломать текущий execution flow. Нужна каноническая матрица Now/Next/Later по фактической стадии проекта.)
  - Links:
    - docs/roadmap/BACKLOG_LEDGER.md
    - docs/roadmap/PulsePlate_Master_Checklist_v1.0.md:1
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - [PulsePlate_Master_Checklist v1.0 source](https://docs.google.com/document/d/1FkHyYUwb8W8Rb-pTQE9OvqHUT5hZyaE2/edit)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
  - DoD:
    - Every checklist item is mapped to one of: `Now`, `Next`, `Later`, `Deferred`
    - Canonical triage matrix artifact exists in-repo and is versioned
    - `Now` items are represented by explicit backlog entries with owner + DoD + target PR
    - `Later/Deferred` items include re-activation trigger (release readiness / market / platform milestone)
    - No duplicate or conflicting ownership across active worktrees

### P1

<a id="ledger-p1-pr1-50-remediation-wave1"></a>
- [ ] P1: PR 1-50 remediation follow-through after Wave 1
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (audit debt / type-safety / test hygiene)
  - Target PR: PR-TBD-PR1-50-REMEDIATION
  - Status: 🟡 In progress
  - Area: frontend / tests / dev-scripts / audit debt
  - Finding Type: audit remediation carryover
  - Reason (EN): PR 1-50 remediation Wave 1 is intentionally scoped to unresolved P0/P1 findings in production code, tests, and dev scripts. Lower-priority cleanup stays deferred so the fix PR remains narrow enough to reach green CI without mixing audit documentation work into the implementation branch.
  - Links:
    - `frontend/src/features/plan/WeeklyPlanViewer.tsx`
    - `frontend/src/features/shoplist/ShoplistPreview.tsx`
    - `tests/test_llm_extras.py`
    - `tests/test_repo_policy_sys_modules.py`
    - `tests/core/catalog/test_sqlite_fk_integrity.py`
    - `tests/test_api.py`
    - `run_coverage_tests.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-sharefile-hardening`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-glasscard-cleanup`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-ollama-diagnostic-deps`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-ollama-monitor-deps`
  - Deferred / P2 carryover:
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-sharefile-hardening`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-glasscard-cleanup`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-ollama-diagnostic-deps`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1-50-ollama-monitor-deps`
  - DoD:
    - Wave 1 fixes all unresolved P0/P1 findings from the PR 1-50 audit
    - Deferred P2 items remain tracked here with explicit file targets
    - `pre-commit run --all-files` and `make verify` pass in PR scope
    - PR body includes a `Deferred / Follow-ups` section with ledger links to this ledger item

<a id="backlog-restore-signed-build-provenance"></a>
- [ ] P1: Restore signed build provenance after cache/buildx workaround is removed
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (supply-chain maturity after tooling-surface guard baseline)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason (EN): Workflow pinning and tooling-surface guards can be enforced immediately, but signed provenance and downstream verification remain intentionally deferred until the documented Docker/buildx cache seam is removed and attestation can be re-enabled without destabilizing the release path.
  - Links:
    - `.github/workflows/build.yml`
    - `docs/architecture/ADR_DOCKER_BUILD_PROVENANCE_WORKAROUND_2026-03-01.md`
    - `docs/security/TOOLING_SURFACE_POLICY.md`
  - DoD:
    - Build provenance is enabled again in the canonical image workflow
    - Signed provenance/SBOM verification is enforced before deploy
    - Follow-up docs and CI checks explicitly cover the restored path

<a id="ledger-p1-canonical-bootstrap-late-rehydration"></a>
- [ ] P1: Canonical app bootstrap late-rehydration hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (runtime reliability follow-up after `/metrics` hotfix)
  - Target PR: PR #1101 (`fix(metrics): restore late bootstrap route on main`) -> PR-TBD-CANONICAL-BOOTSTRAP-LATE-REHYDRATION
  - Area: backend / bootstrap / observability
  - Finding Type: import-order follow-up
  - Reason: The `/metrics` hotfix restores late route registration on already-built apps, but it intentionally does not attempt full middleware rehydration after `middleware_stack` exists. A follow-up is needed to define and harden the canonical behavior for late bootstrap/import-order paths without reintroducing unsafe post-start middleware mutation.
  - Links:
    - `docs/review/PR_1101_FIXED_MAPPING.md`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1101`
    - `app/main.py`
    - `app/bootstrap/metrics.py`
    - `tests/test_metrics.py`
    - `tests/test_no_direct_testclient.py`
  - DoD:
    - Canonical late-bootstrap contract is documented for route vs middleware behavior
    - Tests cover legacy/app-first import order for additive observability surfaces
    - Direct TestClient bypass debt is reduced or explicitly re-audited against the canonical bootstrap contract

<a id="ledger-p1-billing-activation-openapi-refinements"></a>
- [ ] P1: Billing activation OpenAPI refinements after PR #1095
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (contract-first clarity)
  - Target PR: PR-TBD-BILLING-ACTIVATION-OPENAPI-REFINEMENTS
  - Area: backend / frontend / payments / OpenAPI
  - Finding Type: contract refinement follow-up
  - Reason: PR #1095 intentionally keeps the runtime scope narrow around activation + persistence. The follow-up OpenAPI work should explicitly model source-specific activation variants, reuse canonical enums in Apple verify hints, and mark compatibility aliases as deprecated without expanding the current backend runtime PR.
  - Links:
    - `app/schemas/payments.py`
    - `frontend/src/api/openapi.json`
    - `frontend/src/api/schema.ts`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios`
  - DoD:
    - `ActivateSubscriptionRequest` is expressed as a discriminated `oneOf` keyed by `source`
    - Apple verify activation hints reuse canonical `PaymentPlatform`
    - Compatibility aliases in `SubscriptionActivationResponse` are explicitly deprecated in OpenAPI
    - `make openapi-check` passes with regenerated frontend artifacts

<a id="ledger-p1-dsar-direct-user-helper-contract"></a>
- [ ] P1: Internal DSAR direct-user helper contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1049
  - Area: backend / privacy
  - Finding Type: compliance runtime hardening
  - Reason: The compliance control plane now documents support-led DSAR handling, but the runtime still needs deterministic helper functions that export direct-user SQL artifacts and execute bounded deletion without exposing a public endpoint. This slice keeps DSAR execution consistent for `users`, `rag_feedback`, and `user_knowledge` while keeping account-row deletion on the dedicated existing path.
  - Links:
    - `core/compliance/dsar.py`
    - `core/compliance/dsar_service.py`
    - `docs/compliance/DSAR_AND_DELETION_MAP.md`
    - `docs/legal/Privacy.md`
  - DoD:
    - Internal helper functions export direct-user SQL artifacts in a deterministic, serializable format
    - Internal helper functions delete `rag_feedback` and `user_knowledge` idempotently and report per-artifact counts
    - Internal helper functions expose an explicit deletion plan for the `users` row instead of silently widening into full account deletion
    - No public DSAR endpoint is introduced before an explicit auth/ownership contract exists
    - Deterministic tests cover export + delete paths for `users`, `rag_feedback`, and `user_knowledge`

<a id="ledger-p1-telemetry-maturity-follow-through"></a>
- [ ] P1: Telemetry maturity follow-through for audited vault retrieval and budget dashboards
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (post-foundation observability maturity)
  - Target PR: TBD
  - Status: 📋 Planned
  - Reason (EN): The telemetry foundation PR intentionally stops at lightweight spans plus encrypted pointer storage. Audited decrypt workflow, detector budget dashboards, and retention/DSR operating hooks remain deferred so the first runtime slice stays additive and low-risk.
  - Links:
    - `docs/telemetry/TELEMETRY_POLICY.md`
    - `docs/telemetry/LLM_DETECTORS.md`
    - `docs/telemetry/TELEMETRY_FIELD_CLASSIFICATION.md`
    - `docs/compliance/DSAR_AND_DELETION_MAP.md`
    - `docs/legal/Privacy.md`
    - `deploy/otelcol/collector.yaml`
  - DoD:
    - Audited decrypt workflow exists for approved vault retrieval
    - Dashboards cover span volume, full-capture rate, and detector distribution
    - Retention and deletion hooks for telemetry vault references are documented and test-covered

<a id="ledger-p1-external-food-source-policy-enforcement"></a>
- [ ] P1: External food-source operating policy enforcement follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (data governance / legal-operating discipline)
  - Target PR: PR-TBD-FOOD-SOURCE-POLICY-ENFORCEMENT
  - Status: Not started
  - Area: backend / legal-compliance / data platform
  - Finding Type: provider operating-policy follow-up
  - Reason: ODbL attribution is canonical for Open Food Facts and the food
    platform strategy already names broader source tiers, but future ingestion
    work still needs one explicit enforcement lane across USDA, Open Food Facts,
    MenuStat-style datasets, and Nutritionix-style commercial providers so
    technically reachable data is not treated as automatically safe to cache or
    redistribute.
  - Links:
    - `docs/legal/EXTERNAL_FOOD_SOURCE_OPERATING_POLICY.md`
    - `docs/legal/ODbL_COMPLIANCE.md`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `app/routers/pro_food_attribution.py`
  - DoD:
    - New provider onboarding checklist references the operating matrix before
      runtime rollout
    - Provider-specific docs exist whenever stricter rules are needed
    - Attribution registry and docs stay aligned when new public-facing sources
      are added
    - No new external food/menu source ships without explicit cache and
      redistribution decisions

<a id="ledger-p1-token-expansion-activation"></a>
- [ ] P1: Semantic/product token expansion + Tokens Studio activation + optional figma-manifest schema unification
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-system governance)
  - Target PR: PR #1047 (`feat(design): add token pipeline foundation`) -> PR-TBD-TOKEN-EXPANSION-ACTIVATION
  - Status: 📋 Deferred after token-pipeline foundation
  - Foundation PR: PR #1047 (2026-03-08, `f272503c`)
  - Area: frontend / ios / design-system
  - Finding Type: governance follow-up
  - Reason: The repo now has a governed `/tokens -> generated runtime mirrors` pipeline for foundation and current semantic tokens. Deferred work remains for broader semantic/product layers (`tier`, `paywall`, `plate`, `bmi`, `coach`), controlled Tokens Studio activation beyond documentation-only support, and an explicit decision on whether `docs/design/figma-manifest.json` should stay informational or be unified with token-pipeline schema validation.
  - Links:
    - [PR #1047](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047)
    - `docs/design/TOKENS_SOT.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `docs/design/figma-manifest.json`
    - `frontend/src/styles/tokens.css`
    - `frontend/src/styles/tokens.ts`
    - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
    - `ios/PulsePlate/DesignSystem/DesignTokens.swift`
    - `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md`
  - DoD:
    - Semantic and product-token layers are explicitly named and promoted into web/iOS runtime mirrors where needed
    - Tokens Studio activation scope, export format, review gate, and ownership are documented before any runtime automation or commit contract is added
    - If figma-manifest unification is chosen, the schema/version/validation owner is documented; if not chosen, docs explicitly keep it informational
    - Active design-system docs continue to reference one governance path only

<a id="ledger-p1-design-token-lock-ci"></a>
- [ ] P1: Design-token lockfile and deterministic CI/build contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DESIGN-TOKEN-LOCK-CI
  - Status: 📋 Planned
  - Area: design-system / frontend / iOS / CI
  - Finding Type: deterministic build-governance gap
  - Reason (EN): The repo now has token-pipeline governance and generated runtime mirrors, but it still does not have a canonical build-from-lock contract. There is no enforced `tokens.lock.json`, no explicit artifact-from-lock-only rule, and no release/rollback playbook for token changes across web and iOS.
  - Links:
    - `docs/design/TOKENS_SOT.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `frontend/src/styles/tokens.css`
    - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
  - DoD:
    - Canonical token pipeline defines lockfile ownership, artifact generation from lock only, and CI drift policy
    - Release/rollback runbook exists for token builds across web/iOS surfaces
    - Existing semantic/token-governance docs link to the same deterministic build contract

<a id="ledger-p1-color-profile-automation-parity"></a>
- [ ] P1: Color-profile automation and parity evidence follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-system governance)
  - Target PR: PR-TBD-COLOR-PROFILE-AUTOMATION
  - Status: Not started
  - Area: frontend / ios / design-system / governance
  - Finding Type: color-space policy follow-up
  - Reason: Token governance and generated runtime mirrors are canonical, but
    the repo still lacks deterministic automation for asset-profile checks and
    screenshot parity evidence. This follow-through keeps the `sRGB` baseline
    and optional `Display P3` asset lane from drifting into ad-hoc review
    memory.
  - Links:
    - `docs/design/COLOR_PROFILE_GOVERNANCE.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `docs/design/TOKENS_SOT.md`
    - `ios/PulsePlate/Extensions/Color+Assets.swift`
  - DoD:
    - Deterministic asset/profile audit lane exists
    - Screenshot parity evidence contract is documented in an active design
      review runbook
    - `Display P3` exceptions require explicit fallback evidence
    - No new runtime component-level color-space logic appears outside the
      governed path

<a id="ledger-p1-ios-subscription-manager"></a>
- [ ] P1: iOS SubscriptionManager backend-driven integration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-IOS-SUBSCRIPTION-MANAGER
  - Status: 📋 Planned
  - Area: iOS / payments / thin-client policy
  - Finding Type: monetization runtime follow-through
  - Reason (EN): The monetization baseline is iOS-first, but thin-client-safe subscription orchestration still needs an explicit app-side integration item rather than staying implicit inside the broader payments wave.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
    - `ios/PulsePlate`
  - DoD:
    - iOS subscription orchestration remains thin and backend-driven
    - Product/state transitions are deterministic and test-covered
    - No client-side billing logic duplicates backend activation policy

<a id="ledger-p1-app-store-subscription-offers-governance"></a>
- [ ] P1: App Store subscription offers governance and StoreKit-truth pricing contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-IOS-SUBSCRIPTION-OFFERS-GOVERNANCE
  - Status: 📋 Planned
  - Area: iOS / billing / App Store / growth
  - Finding Type: release-governance gap
  - Reason (EN): App Store Connect introductory offers, offer codes, promotional offers, and win-back pricing are operationally separate from in-app UI, but the repo does not yet have a canonical contract that says pricing, trial duration, and eligibility copy must be StoreKit-truth rather than manually inferred in product copy.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `docs/roadmap/IOS_BACKEND_REALIZATION_ROADMAP.md`
    - `docs/MOBILE_API_MIGRATION_GUIDE.md`
  - DoD:
    - Canonical billing/release doc defines how introductory offers, offer codes, and promotional offers are configured and reviewed
    - UI copy contract says prices, trial duration, and eligibility messaging must come from StoreKit/App Store truth rather than manual hardcoding
    - App Store release-ops and compliance docs link back to the same monetization governance source

<a id="ledger-p1-release-env-security-contract"></a>
- [ ] P1: Release environment security contract for `API_KEY_REQUIRED` and tier-gating env truth
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-RELEASE-ENV-SECURITY-CONTRACT
  - Status: 📋 Planned
  - Area: deploy / security / release operations
  - Finding Type: runtime env contract gap
  - Reason (EN): Repo docs describe `API_KEY_REQUIRED` and related auth/tier env flags, but there is no canonical release contract that makes staging/production values explicit and auditable. Without that contract, a release can drift into a weaker env posture than local docs imply.
  - Links:
    - `.env.example`
    - `docker-compose.yaml`
    - `README.md`
    - `docs/deploy/OVERVIEW.md`
  - DoD:
    - Canonical release-env doc defines expected values for `API_KEY_REQUIRED` and other auth/tier-critical env flags across local, staging, and production
    - Verification path for staging/prod env truth is documented and linked from release runbooks
    - Security posture docs no longer rely on implied env defaults where release enforcement is required

<a id="ledger-p1-fastapi-compatibility-gates"></a>
- [ ] P1: FastAPI / Pydantic / Starlette compatibility gates for schema and TestClient drift
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-FASTAPI-COMPAT-GATES
  - Status: 📋 Planned
  - Area: backend / CI / contracts
  - Finding Type: dependency-compatibility gap
  - Reason (EN): The repo already depends on FastAPI, Pydantic v2, and Starlette/httpx behavior, but it has no canonical CI bundle that explicitly guards strict JSON content-type handling, OpenAPI/root_path drift, nullable-required schema semantics, and TestClient behavior changes during dependency bumps.
  - Links:
    - `README.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `tests/test_openapi_determinism.py`
    - `docs/audience_pack/FACTS_CANONICAL.md`
  - DoD:
    - Deterministic CI smoke/tests exist for strict content-type behavior, OpenAPI snapshot stability, and representative TestClient/runtime request paths
    - Schema checks explicitly cover Pydantic v2 nullable-required semantics where they affect API contracts
    - Dependency upgrade/runbook docs link to the same compatibility gate source

<a id="ledger-p1-search-observability-foundation"></a>
- [ ] P1: Search observability foundation with trace correlation, synthetic probes, and per-class SLOs
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-SEARCH-OBSERVABILITY-FOUNDATION
  - Status: 📋 Planned
  - Area: backend / observability / search
  - Finding Type: observability foundation gap
  - Reason (EN): Search and retrieval performance are still hard to diagnose end-to-end. The repo has tracing policy/docs, but it does not yet define a canonical package for correlated HTTP/DB/search traces, daily synthetic probes, and SLOs split by query class.
  - Links:
    - `docs/analytics/README.md`
    - `docs/analytics/METRICS_CATALOG.md`
    - `docs/plan/PR_WS_OBSERVABILITY_TASK_ANALYSIS.md`
  - DoD:
    - Canonical observability doc defines trace correlation, search/query-class tagging, and `X-Trace-Id` response contract if adopted
    - Synthetic probe workflow and per-class latency/error objectives are documented before rollout
    - Search performance debugging path is linked from ops/runbook docs

<a id="ledger-p1-usda-foundation-foods-preflight"></a>
- [ ] P1: USDA Foundation Foods update preflight and diff-based ingest guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-USDA-PREFLIGHT
  - Status: 📋 Planned
  - Area: data ingestion / food catalog / quality
  - Finding Type: upstream data-change readiness gap
  - Reason (EN): USDA Foundation Foods and related FoodData updates can change the shape and volume of ingestible records, but the repo does not yet have a canonical preflight contract for diffing new snapshots, catching dedupe/mapping collisions, and validating filter/key assumptions before updating the unified food catalog.
  - Links:
    - `scripts/build_food_db.py`
    - `docs/roadmap/GLOBAL_ROADMAP.md`
    - `app/services/food_store.py`
  - DoD:
    - Preflight workflow exists for diffing incoming USDA/Foundation Foods changes against the current catalog snapshot
    - Dedupe/mapping collision checks are defined before snapshot promotion
    - Data-ingest docs and runbooks point to the same preflight source of truth

<a id="ledger-p1-llm-reliability-security-gates"></a>
- [ ] P1: LLM reliability and security CI gates for retrieval, faithfulness, prompt-injection, and privacy
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-LLM-CI-GATES
  - Status: 📋 Planned
  - Area: AI runtime / security / evaluation
  - Finding Type: model-evaluation gate gap
  - Reason (EN): The repo has AI safety posture and tracing materials, but there is no canonical CI gate bundle for retrieval quality regressions, faithfulness checks, prompt-injection adversarial tests, and privacy-sensitive evaluation. Without that package, AI quality and safety can drift silently between releases.
  - Links:
    - `docs/security/SECURITY_POSTURE.md`
    - `docs/analytics/README.md`
    - `docs/innovation/INNOVATION_EVALUATION_FRAMEWORK.md`
    - `core/insight/philosophy_validator.py`
    - `AGENTS.md`
  - DoD:
    - Canonical evaluation package defines required retrieval/faithfulness/security/privacy checks and where they run
    - Prompt-injection and untrusted-context posture is covered by explicit CI or release-gate tests
    - LLM outputs used for product copy/coaching pass `philosophy_validator` (BLOCKER = rewrite)
    - AI runtime/runbook docs link to the same gate source instead of ad-hoc evaluation notes

<a id="ledger-p1-apple-server-api-migration"></a>
- [ ] P1: Apple receipt verification migration to App Store Server API
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-APPLE-SERVER-API-MIGRATION
  - Area: backend / payments / provider integration
  - Finding Type: provider modernization
  - Reason: The current PR uses classic `verifyReceipt` only as a transitional compatibility path; Apple-recommended signed transaction / App Store Server API validation remains mandatory follow-up work.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/services/payments_activation.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
  - DoD:
    - Apple verification moves off classic `verifyReceipt` onto the approved server-side successor flow
    - Existing verification contract remains backward-compatible for downstream activation
    - Provider migration paths are covered with deterministic tests and rollout notes

<a id="ledger-p1-ios-subscription-orchestration"></a>
- [ ] P1: iOS SubscriptionManager orchestration follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-IOS-SUBSCRIPTION-MANAGER
  - Status: 💤 Superseded by `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ios-subscription-manager`
  - Area: ios / payments / orchestration
  - Finding Type: client orchestration gap
  - Reason: Backend verify is now separated cleanly, but the iOS thin client still needs explicit orchestration for purchase -> verify -> activation handoff without embedding billing truth on-device. The canonical surviving tracker is `ledger-p1-ios-subscription-manager`; this entry remains as an audit bridge from the billing wave only.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `app/routers/billing.py`
    - `app/services/payments_activation.py`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-billing-apple-verify`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ios-subscription-manager`
  - DoD:
    - Follow the canonical DoD recorded under `ledger-p1-ios-subscription-manager`

<a id="ledger-p1-ios-storekit-products"></a>
- [ ] P1: iOS StoreKit products contract and setup baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-IOS-STOREKIT-PRODUCTS
  - Status: 📋 Planned
  - Area: ios / release / billing operations
  - Finding Type: store configuration readiness
  - Reason (EN): The monthly review and phase-fit checklist both treat StoreKit products setup as a distinct next-wave gate. It needs an explicit ledger item so release-ops work does not stay hidden inside broader iOS billing follow-through.
  - Links:
    - `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
  - DoD:
    - Canonical StoreKit product identifiers and setup checklist are versioned in-repo
    - Billing/runtime follow-through references the same product contract without client-side drift
    - Release checklist is explicit enough for future iOS submission work

<a id="ledger-p1-mobile-secret-conformance"></a>
- [ ] P1: Mobile secret storage conformance (iOS Keychain now, Android Keystore deferred)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (mobile security correctness)
  - Target PR: PR-TBD-IOS-KEYCHAIN-CONFORMANCE -> PR #1011 (`feat/p1-ios-keychain-conformance`) -> PR #1067 -> PR #1078 (`feat/p1-ios-keychain-conformance-pr2`)
  - Status: 🟡 In progress (runtime Keychain-only behavior is already on `main`; this follow-up tightens canonical test-surface coverage and current-state setup docs)
  - Reason (EN): Master checklist item #5 remains active until the repo's canonical iOS enforcement surfaces match runtime truth. The `ProcessInfo` fallback has already been removed from `ProKeyProvider`, but default iOS test lanes and current-state setup docs still need to encode the Keychain-only invariant so future drift is caught by default.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - ios/PulsePlate/Services/KeychainStore.swift
    - ios/PulsePlate/Services/ProKeyProvider.swift
    - ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift
    - ios/PulsePlateTests/Services/ProKeyProviderTests.swift
    - ios/PulsePlateTests/Services/KeychainStoreTests.swift
    - ios/SHOPPING_LIST_SETUP.md
  - DoD:
    - iOS runtime secret paths are verified to use Keychain storage only
    - Default local and CI iOS test surfaces include Keychain provider roundtrip/ignore-env coverage
    - Current-state iOS setup docs no longer advertise `PRO_API_KEY` or placeholder fallback as runtime auth truth
    - Guard tests prevent regression to insecure storage

<a id="ledger-p1-diet-flags-contract-sync"></a>
- [ ] P1: Diet flags contract sync across schemas and clients
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-DIET-FLAGS-CONTRACT-SYNC
  - Status: 📋 Planned
  - Area: frontend / backend / iOS contracts
  - Finding Type: contract consistency
  - Reason (EN): Diet-flag semantics are product-facing and cross-client. A dedicated sync item keeps the enum/normalization surface canonical instead of letting drift hide inside frontend or generated-type follow-ups.
  - Links:
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `frontend`
    - `ios/PulsePlate`
  - DoD:
    - One canonical diet-flags normalization table is used across backend schemas and clients
    - Generated or mirrored client types remain aligned with backend truth
    - Deterministic regression tests cover the shared contract

- [ ] P1: `vector_rag` SQL assembly refactor (remove raw SQL formatting debt)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security + maintainability)
  - Target PR: PR-TBD-VECTOR-RAG-SQL-REFACTOR
  - Status: 📋 Planned
  - Reason: Raw SQL string assembly in vector retrieval path increases maintenance and security review overhead; contract should move to parameterized/ORM-safe composition.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md`
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `core/rag/vector_rag.py`
    - `tests/test_vector_rag.py`
  - DoD:
    - Query assembly uses parameterized/ORM-safe path (no ad-hoc SQL string formatting)
    - Existing vector retrieval behavior remains contract-compatible
    - Security/static analysis checks pass without local suppressions for this path


<a id="ledger-p1-philosophical-logic"></a>
- [ ] P1: Philosophical logic principles for LLM reliability (Aristotelian, Analytical, Post-Analytical, Linguistic)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (high impact on reliability)
  - Target PR: PR #1024 (`feat: add philosophical runtime foundation for insight`) -> PR-TBD-LLM-PHILOSOPHY-ROLLOUT
  - Status: 🟡 In progress (foundation merged in PR #1024; rollout follow-ups remain)
  - Dependencies:
    - [P0 Master checklist phase-fit triage](#ledger-p0-master-checklist-triage)
    - [P0 Payment rails RU/BY + iOS baseline](#ledger-p0-payments-ruby-ios)
  - Reason (EN): Apply classical logic and philosophical principles to improve LLM response reliability and argumentative rigor. Hypothesized impact (to be benchmark-validated): reduce contradictions from ~15% to <2%, unverifiable claims from ~30% to <5%, contextually irrelevant responses from ~25% to <10%. Four frameworks: Aristotelian logic (syllogisms, non-contradiction), Analytical philosophy (verification, falsification), Post-analytical philosophy (pragmatic validation, hermeneutics), Linguistic philosophy (speech acts, language games, meaning-as-use). **Speed optimization:** Philosophical principles also optimize speed (50-60% latency reduction) through adaptive depth, early stopping, and query classification. (RU: Применение классической логики и философских принципов для улучшения достоверности ответов LLM и доказательности аргументации. Гипотеза (с обязательной валидацией бенчмарками): снижение противоречий с ~15% до <2%, непроверяемых утверждений с ~30% до <5%, контекстуально нерелевантных ответов с ~25% до <10%. **Оптимизация скорости:** Философские принципы также оптимизируют скорость (снижение latency на 50-60%) через адаптивную глубину, раннее прекращение и классификацию запросов.)
  - Links:
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md (unified analysis: philosophy + math + CBT integration)
    - docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md (comprehensive design, code examples, implementation roadmap)
    - docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md (speed optimization using philosophical principles: speech acts, language games, early stopping, adaptive depth)
    - docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md (current LLM/RAG implementation)
    - core/insight/creative_scientific_innovations.md (AI assistant design)
    - `docs/review/PR_1024_FIXED_MAPPING.md`
  - Prerequisites:
    - ✅ Current LLM/RAG infrastructure stable (`llm.py`, `core/rag/simple_rag.py`)
    - ✅ Insight endpoints stable (`legacy_app.py`, `app/routers/vip.py`)
    - ⏳ Master checklist phase-fit triage approved
    - ⏳ Fact-checking system implemented (P0 from LLM_RAG_AI_ASSISTANT_ANALYSIS.md)
  - DoD:
    - Phase 1: Aristotelian logic implemented (syllogistic prompts, contradiction detection)
    - Phase 2: Analytical philosophy implemented (verification, falsification)
    - Phase 3: Post-analytical philosophy implemented (pragmatic validation, hermeneutics)
    - Phase 4: Linguistic philosophy implemented (speech acts, language games)
    - Phase 5: Integrated framework complete (unified prompt builder + validator)
    - Hypothesis target (requires benchmark validation): Speech act classification (50-70% reduction for commands), language game detection (50-60% reduction for medical), early stopping (30-50% reduction), adaptive depth (50-60% average reduction)
    - Hypothesis target (requires benchmark validation): contradiction rate <2%, verification rate >95%, pragmatic utility >90%
    - Hypothesis target (requires benchmark validation): latency reduction 50-60% average, quality maintained ≥95%
    - Validation evidence owner: [P1 Scientific reliability publication pipeline](#ledger-p1-scientific-reliability-pipeline)
    - Integration tests pass (end-to-end philosophical validation + speed optimization pipeline)


- [ ] P1: PRO monthly quota for LLM endpoints (parity with VIP)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AGENTS.md requires monthly quota before any LLM provider call)
  - Target PR: TBD (infrastructure extension from PR-647 VIP quota)
  - Status: 📋 Planned
  - Reason (EN): PR-942 CBT insight endpoint added rate limiting but monthly quota enforcement exists only for VIP tier (PR-647). PRO-tier LLM endpoints (CBT insight, future agents) need equivalent quota infrastructure. Currently AGENTS.md mandates "All LLM endpoints MUST enforce server-side monthly hard quota before any provider call" but only VIP has implementation.
  - Links:
    - `app/security/llm_monthly_quota.py` (VIP-only implementation)
    - `docs/audit/PR_647_VIP_LLM_MONTHLY_QUOTA_AUDIT.md`
    - `app/routers/cbt_insight.py` (PRO endpoint without monthly quota)
  - DoD:
    - Extend llm_monthly_quota.py to support PRO tier (separate table or unified with tier column)
    - CBT insight endpoint calls quota check before provider.generate()
    - Deterministic tests for PRO quota enforcement


<a id="ledger-p1-recursive-methods"></a>
- [ ] P1: Recursive methods for LLM/RAG/AI assistant (multi-hop retrieval, recursive reasoning, self-refinement, self-verification, learning)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (high impact on quality and accuracy)
  - Target PR: PR-TBD-RECURSIVE-LLM-W1
  - Status: 🟡 Prioritized (quality wave W1-B)
  - Dependencies:
    - [P1 Philosophical logic principles](#ledger-p1-philosophical-logic)
  - Reason (EN): Implement recursive methods to dramatically improve LLM/RAG reliability and AI assistant capabilities. Five recursive techniques: recursive retrieval (multi-hop RAG with query refinement, 40-60% retrieval quality improvement), recursive reasoning (chain-of-thought, tree-of-thought, decomposition, 25-35% answer accuracy improvement), recursive refinement (self-critique and iterative improvement, 30-40% answer quality improvement), recursive verification (self-validation through recursive queries, reduces factual errors from ~15% to <5%), recursive learning (self-improvement from user feedback, adaptive personalization). Hypothesized overall impact (pending benchmark validation): retrieval quality 85-90%, answer accuracy 85-90%, factual errors <5%, user satisfaction 85-90%. (RU: Внедрение рекурсивных методов для значительного улучшения надежности LLM/RAG и возможностей AI ассистента. Пять рекурсивных техник: рекурсивный retrieval (multi-hop RAG с уточнением запросов, улучшение качества retrieval на 40-60%), рекурсивное рассуждение (chain-of-thought, tree-of-thought, декомпозиция, улучшение точности ответов на 25-35%), рекурсивное уточнение (самокритика и итеративное улучшение, улучшение качества ответов на 30-40%), рекурсивная верификация (самопроверка через рекурсивные запросы, снижение фактических ошибок с ~15% до <5%), рекурсивное обучение (самоулучшение на основе обратной связи пользователей, адаптивная персонализация).)
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
    - Hypothesis target (requires benchmark validation): Parallelization (asyncio.gather), GPTCache integration, Redis caching, batch verification (reduce latency from 2-3x to 1.2-1.5x)
    - Hypothesis target (requires benchmark validation): retrieval quality ≥85%, answer accuracy ≥85%, factual errors ≤5%, latency ≤1.5x baseline
    - Hypothesis target (requires benchmark validation): caching, parallelization, early stopping (3-5x LLM calls acceptable, reduced to 1.5-2x with caching)
    - Validation evidence owner: [P1 Scientific reliability publication pipeline](#ledger-p1-scientific-reliability-pipeline)
    - Integration tests pass (end-to-end recursive pipeline)


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


<a id="ledger-p1-ai-bounded-context-extraction"></a>
- [ ] P1: Extract AI runtime into a dedicated bounded context
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-AI-BOUNDED-CONTEXT
  - Area: backend / AI runtime / architecture
  - Finding Type: bounded-context hardening
  - Reason: AI logic, provider seams, and safety-related behavior are currently documented across runtime areas, but there is no canonical `core/ai/*` bounded context yet. This increases the risk of router/business-logic drift and makes AI safety ownership harder to enforce.
  - Links:
    - `docs/architecture/providers_implementation.md`
    - `AGENTS.md`
    - `docs/security/SECURITY_POSTURE.md`
    - `docs/runbooks/ENGINEER_QUICKPATH.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `docs/architecture/ADR_AI_RUNTIME_BOUNDED_CONTEXT_SEAM_2026-03-09.md`
  - DoD:
    - Canonical AI runtime package structure exists and is documented
    - Routers and client layers remain thin adapters around AI behavior
    - Safety/eval/provider ownership is mapped to the bounded context
    - AGENTS and architecture docs no longer need transitional wording about future extraction


<a id="ledger-p1-api-key-toggle-guard"></a>
- [ ] P1: Production fail-fast for anonymous/dev API key toggles
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-API-KEY-TOGGLE-GUARD
  - Area: backend / security / configuration
  - Finding Type: misconfiguration hardening
  - Reason: `ALLOW_ANONYMOUS_API_KEYS` and `ALLOW_DEV_API_KEY` remain env-driven escape hatches. The codebase documents that they must stay off in production, but startup/config guards are still too easy to misconfigure across `APP_ENV` and `ENVIRONMENT`.
  - Links:
    - `app/middleware/api_tiers.py`
    - `app/routers/vip.py`
    - `legacy_app.py`
    - `docs/deploy/VIP_API_KEYS.md`
    - `tests/test_vip_anonymous_api_key_safety.py`
  - DoD:
    - Production-like env detection is canonicalized (`APP_ENV` / `ENVIRONMENT` mismatch removed or documented)
    - App fails closed or logs explicit startup error when anonymous/dev API key toggles are enabled in production-like envs
    - Tests cover fail-closed behavior for production/staging settings
    - Deploy docs show the safe production values


<a id="ledger-p1-legacy-runtime-env-canonicalization"></a>
- [ ] P1: Canonicalize legacy runtime env gating
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR `#1072`
  - Status: 🟡 In progress (branch `feat/p1-legacy-runtime-env-canonicalization-pr`)
  - Follow-up from PR `#1054` (parent: `ledger-p1-api-key-toggle-guard`)
  - Area: backend / security / legacy compatibility
  - Finding Type: configuration drift
  - Reason: `legacy_app.py` still contains module-level `APP_ENV`-only gates for local `.env` loading, dev-only docs, test-router registration, and `/debug_env`. This drifts from the canonical `ENVIRONMENT`-first runtime helpers introduced by the API key toggle guard and can re-enable development-only surfaces when only `ENVIRONMENT` is set in production-like deployments.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1054`
    - `#ledger-p1-api-key-toggle-guard`
    - `legacy_app.py`
    - `settings.py`
    - `docs/deploy/VIP_API_KEYS.md`
    - `docs/review/PR_1054_FIXED_MAPPING.md`
  - DoD:
    - Module-level env gating in `legacy_app.py` uses canonical runtime helpers instead of raw `APP_ENV`
    - Local `.env` loading, test-router registration, and `/debug_env` gating follow the same environment semantics as startup guards
    - Tests cover `ENVIRONMENT` overriding `APP_ENV` for the remaining legacy surfaces


<a id="ledger-p1-openapi-decoupling-split"></a>
- [ ] P1: Split backend OpenAPI generation from frontend type generation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-OPENAPI-DECOUPLING-SPLIT
  - Area: build / contracts / developer workflow
  - Finding Type: workflow hardening
  - Reason: `make openapi` is the current canonical combined path, but backend-only schema generation and frontend type generation are still coupled in the active Make workflow. A dedicated split would reduce backend-only friction while preserving `make openapi-check` as the sync verifier.
  - Links:
    - `Makefile`
    - `AGENTS.md`
    - `docs/runbooks/ENGINEER_QUICKPATH.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `docs/architecture/ADR_OPENAPI_WORKFLOW_SPLIT_SEAM_2026-03-09.md`
  - DoD:
    - Dedicated backend schema target exists without frontend install dependency
    - Dedicated frontend type-generation target exists
    - `make openapi-check` remains the canonical sync verifier
    - `AGENTS.md`, runbooks, API map, and CI docs reflect the split workflow without ambiguity


- [ ] P1: Remove staging TLS fallback seam after full staging readiness
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-STAGING-SEAM-REMOVAL
  - Area: deploy / CD policy / staging runtime
  - Finding Type: temporary seam removal
  - Reason: Build-only mode keeps staging HTTPS alive via production Caddy fallback vhost. This is intentional temporary behavior and must be removed once staging runtime deploy is continuously enabled.
  - Links:
    - `docs/architecture/ADR_STAGING_TLS_FALLBACK_SEAM_2026-03-04.md`
    - `deploy/Caddyfile.production`
    - `deploy/docker-compose.production.yaml`
    - `docs/deploy/STAGING.md`
    - `.github/workflows/cd.yml`
  - DoD:
    - Staging stack in `/srv/pulseplate-staging` is primary runtime source for staging URL
    - `WEB_IOS_RELEASE_READY=true` and staging SSH deploy path is continuously enabled
    - Production Caddy fallback vhost for `STAGING_FALLBACK_DOMAIN` is removed
    - Runbook evidence updated with direct `file:line` anchors for non-fallback flow


- [ ] Design file URL + node IDs required for Code Connect activation (H+P+Pr)
  - Owner: @katsiaryna_kavaleuskaya (Design + FE + iOS)
  - Target PR: PR/Figma-CodeConnect-Activation
  - Priority: P1
  - Status: Optional follow-up (auxiliary to Penpot + Storybook)
  - Area: design / frontend / iOS
  - Finding Type: integration dependency
  - Reason: Web review is now canonical via Storybook + Penpot bridge, while
    Code Connect activation remains an optional auxiliary mapping path once the
    current P0 node set is complete/non-stale and the workspace has a Code
    Connect-capable seat.
  - Links:
    - `docs/figma/FIGMA_CODE_CONNECT_BRIDGE_HPP.md`
    - `docs/figma/FIGMA_DESIGN_URL_NODEID_CAPTURE_HPP.md`
    - `docs/figma/FIGMA_CODE_CONNECT_MAPPING_CANDIDATES_HPP.md`
    - `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md`
  - DoD:
    - Figma Design file URL is recorded in repo docs
    - P0 CTA nodes have current, non-stale `fileKey` and `nodeId`
      (`web.home.open_setup`, `web.plate.premium_gate_cta`,
      `web.progress.export_pdf`, `ios.plate.issue_action_dynamic`)
    - `get_code_connect_suggestions` is no longer plan-blocked for the workspace
    - `get_code_connect_map` returns expected active mappings for P0 set
    - Matrix optional design review references are updated for activated rows
    - Optional activation path does not redefine the canonical Storybook-first
      web review workflow


- [ ] P1: Explainer contract and payload design for FREE / PRO / VIP
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (contract-first unblocker)
  - Target PR: PR-TBD-EXPLAINER-CONTRACT-PAYLOADS
  - Status: 📋 Planned
  - Reason (EN): The first implementation slice should lock backend-owned payload shapes before any UI work. PulsePlate needs canonical response shapes for explainer cards that reuse current BMI, interpretation, adherence, and weekly-plan entities instead of inventing client heuristics. (RU: Сначала нужен каноничный backend contract для explainer payloads; UI не должен сам собирать бизнес-логику.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `app/schemas/`
    - `app/routers/`
  - DoD:
    - High-level contract documents backend-owned `explainer_card` fields for FREE / PRO / VIP
    - Existing product entities are mapped to explainer payload sources without client-side business logic duplication
    - No runtime implementation is required in the design PR


- [ ] Penpot + Storybook fallback bridge for design handoff
  - Owner: @katsiaryna_kavaleuskaya (Design + FE)
  - Target PR: PR/Penpot-Storybook-Bridge
  - Priority: P1
  - Status: ▶️ In progress (Primary web-review path)
  - Area: design / frontend / docs
  - Finding Type: fallback workflow
  - Reason: Storybook and token SoT already exist in repo, so this bridge is the
    canonical low-cost design review path for web. Figma Code Connect remains an
    optional auxiliary mapping workflow rather than a gating dependency.
  - Links:
    - `docs/architecture/ADR_PENPOT_STORYBOOK_BRIDGE_FALLBACK_SEAM_2026-03-07.md`
    - `docs/design/PENPOT_STORYBOOK_BRIDGE.md`
    - `docs/design/PENPOT_CTA_REVIEW_PACKET_TEMPLATE.md`
    - `docs/design/PENPOT_CTA_REVIEW_PACKET_WEB_HOME_OPEN_SETUP.md`
    - `docs/design/PENPOT_CTA_REVIEW_PACKET_WEB_PROGRESS_EXPORT_PDF.md`
    - `docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md`
    - `frontend/.storybook/main.ts`
    - `frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx`
  - DoD:
    - Penpot bridge is documented as the canonical minimal handoff path for web review
    - Storybook remains canonical web review surface
    - Seam ADR remains linked from this ledger item and owns explicit exit criteria
    - Token SoT linkage is explicit in the bridge doc
    - CTA/design review packet format is defined without Code Connect dependency
    - Tool-neutral design review reference replaces Figma-only required fields in handoff contracts

<a id="ledger-p1-frontend-ai-parity"></a>
- [ ] P1: Frontend parity for new AI-agent and LLM reliability features
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (quality visibility)
  - Target PR: PR-TBD (`feat/frontend-ai-reliability-parity-w1`)
  - Status: 🟡 In progress (wave 1: Home + iOS Home entry + typed `/api/v1/pro/cbt/insight` parity)
  - Reason (EN): Backend quality features (RAG confidence, verification pipeline, recursive/philosophical controls) must be visible in web/iOS UX; otherwise quality work remains opaque and user trust/conversion suffers. (RU: Новые quality-фичи ИИ должны быть отражены во фронтенде; иначе улучшения качества не видны пользователю и не влияют на доверие/конверсию.)
  - Links:
    - frontend/src/api/openapi.json
    - frontend/src/api/schema.ts
    - frontend/src/api/premium/cbt-insight.ts
    - frontend/src/pages/Home.tsx
    - ios/PulsePlate/Views/HomeView.swift
    - ios/PulsePlate/Views/AIInsightView.swift
    - docs/design/NUTRITION_COACHING_DESIGN.md
    - docs/contracts/RAG_CONTRACT.md
  - DoD:
    - [ ] UI contracts for `sources[]`, confidence, verification state are aligned with backend schema
    - [ ] Frontend/iOS screens for AI assistant reflect reliability state (validated / partial / fallback)
    - [ ] Thin-client guards remain green; no business logic duplication on clients
    - [ ] Deterministic contract tests added for new AI-quality response fields


- [ ] P1: Phase 2 — Remove nosec allowlist by migrating legacy suppressions
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-NOSEC-ALLOWLIST-PHASE2
  - Area: guards / security policy / tech-debt
  - Finding Type: allowlist TTL enforcement follow-up
  - Reason: Nosec policy allowlist (Phase 1) has TTL per line; entries must be migrated to full nosec format or removed so allowlist shrinks to zero and guard does not rely on allowlist.
  - Links:
    - `tests/guards/test_nosec_policy_guard.py`
    - `tests/guards/fixtures/nosec_policy_allowlist.txt`
    - `AGENTS.md` (Bandit / nosec policy)
  - DoD:
    - Allowlist reduced to 0 entries (or removed)
    - Each legacy `# nosec` either removed (fix) or converted to full format (Bxxx:, remove-by: date, ref:)
    - Guard no longer uses allowlist (or allowlist file removed)


<a id="ledger-p1-compose-v2-migration"></a>
- [ ] P1: Migrate command surface to `docker compose` v2 only
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-COMPOSE-V2-MIGRATION
  - Area: infra / docs / operator workflow
  - Finding Type: command-surface consistency
  - Reason: Repo command surfaces are mixed: some docs use `docker compose`, while `Makefile` and several runbooks still use `docker-compose`. This creates onboarding ambiguity and toolchain drift.
  - Links:
    - `Makefile`
    - `docs/deploy/README.md`
    - `docs/runbooks/ENGINEER_QUICKPATH.md`
    - `AGENTS.md`
    - `docs/architecture/ADR_COMPOSE_V2_COMMAND_SURFACE_SEAM_2026-03-09.md`
  - DoD:
    - Makefile targets use `docker compose`
    - Active runbooks/docs no longer recommend `docker-compose` as the target state
    - Transitional fallback language is removed from `AGENTS.md` and quick-path docs
    - Grep-based verification for `docker-compose` is documented or automated


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


- [ ] P1: iOS open-source implementation gate (repo-wide scan + thin-client conformance)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-IOS-OSS-IMPLEMENTATION-GATE
  - Status: 🟡 Prioritized
  - Reason: Product quality now depends on deterministic iOS conformance checks before merge; Swift guard tests exist, but we need a repo-wide open-source gate that validates implementation patterns and prevents silent drift.
  - Links:
    - docs/audit/PR_559_ANTI_DUPLICATION_GUARDS.md
    - ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift
    - docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md
  - DoD:
    - GH Actions step scans iOS app Swift sources for forbidden patterns
    - Excludes fixtures/mocks
    - Thin-client/APIClient invariants are enforced in CI for changed iOS files
    - Documented in ios/AGENTS.md


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


- [ ] P1: `user_knowledge` DB-level RLS / policy hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (security / defense-in-depth)
  - Target PR: PR #1089 (`feat/p1-user-knowledge-rls`)
  - Status: 🟡 In progress (active PR `#1089`)
  - Reason (EN): Application-layer tenant scoping prevents cross-tenant leaks in runtime retrieval, but Postgres still needed explicit DB-level RLS/policy enforcement plus a canonical session-context bridge to make the policy enforceable in runtime paths.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md` (§7, §8)
    - `app/models/rag_feedback.py`
    - `core/rag/vector_rag.py`
    - `core/db_rls.py`
    - `alembic/versions/202603100101_enable_rag_user_rls.py`
  - DoD:
    - Postgres RLS policies exist for both `user_knowledge` and `rag_feedback`
    - User-bound rows use a bigint subject principal compatible with runtime-derived API-key subject isolation (no stale `users.id` FK contract)
    - Canonical transaction-local session context is set before RAG retrieval, feedback writes, and DSAR helper queries
    - Migration + rollback path documented
    - Tests or audit evidence cover deny-by-default cross-tenant access at DB layer
    - Runtime app-layer filtering remains in place (no regression to code-level scoping)


<a id="ledger-p1-scientific-reliability-pipeline"></a>
- [ ] P1: Scientific reliability publication pipeline (blog + evidence artifacts)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (trust + GTM)
  - Target PR: PR-TBD-SCIENTIFIC-RELIABILITY-BLOG
  - Status: 📋 Planned
  - Reason (EN): Product differentiation requires public, evidence-based communication of reliability methods (RAG grounding, philosophical validation, recursive verification) with reproducible metrics and no medical overclaiming. (RU: Для дифференциации нужен публичный научно-достоверный контент по quality-подходу без медикал-оверклеймов.)
  - Links:
    - docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md
    - docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md
    - docs/insights/RECURSIVE_METHODS_LLM_RAG.md
  - DoD:
    - Editorial plan and evidence format are documented (metrics, caveats, claim boundaries)
    - At least one canonical article draft is mapped to verifiable repo artifacts
    - Marketing copy checklist includes wellness-safe and evidence-only claims


- [ ] P1: Agent knowledge library template packs (domain-specific)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (process scalability)
  - Target PR: PR_TBD_AGENT_LIBRARY_TEMPLATE_PACKS
  - Status: 📋 Planned
  - Reason (EN): Bootstrap library artifacts are in place, but recurring cycles
    need reusable, domain-specific packs (security, RAG, UX, DS) to keep
    brainstorm-to-PR flow fast and deterministic without policy drift.
  - Links:
    - `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
    - `docs/library/index.md`
    - `docs/library/promotion/2026-02-19_agent-library-bootstrap_promotion-log.md`
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
  - DoD:
    - Add template packs under `docs/library/templates/` for at least 4 tracks:
      security, RAG, UX/accessibility, data/evaluation
    - Each template includes routing card, evidence section, promotion target,
      and deferred-item ledger block
    - Add one worked example cycle using one template pack
    - `ReadLints` clean for all new docs


- [ ] P1: Classify CI checks as hard / soft / external in AGENTS or CI governance
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Explicit classification (hard gate / soft gate / external flaky) prevents ambiguous merge decisions; external tools do not block unless marked required.
  - Links:
    - `AGENTS.md:31` (merge readiness), `:39` (checklist)
    - `.github/workflows/` (CI job definitions)
  - DoD:
    - AGENTS.md or dedicated CI governance doc defines hard gate (blocks merge), soft gate (warn only), external (never blocks unless manually promoted)
    - Examples listed per type


- [ ] P1: Disposition guard — ban mapping to trigger-only commits
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD (fix/orch-ban-trigger-commit-mapping)
  - Area: orchestration / review governance
  - Finding Type: process hardening
  - Reason: Prevent FIXED proof bypass via empty or CI rerun/trigger commits. Mapping `- <url> -> <sha>` must not accept empty commits or commits whose subject matches trigger/rerun patterns.
  - Links:
    - `scripts/orchestration/check_review_threads_disposition.py`
    - `tests/test_review_threads_disposition_strict.py`
    - `AGENTS.md` (Review Governance)
  - DoD:
    - Gate fails when mapping SHA is empty commit (no changed files)
    - Gate fails when commit subject matches trigger/rerun patterns (trigger ci, re-run ci, re-run checks)
    - Tests cover deny (empty, trigger subject) and allow (normal commit)
    - AGENTS.md updated with FIXED proof quality (trigger-only ban) rule
    - Optional allowlist with TTL remains empty by default (P2 if needed)


- [ ] P1: PR #1013 sandbox hardening follow-ups
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-SANDBOX-HARDENING-FOLLOWUPS
  - Status: Open
  - Area: security / agent control plane / sandbox runtime
  - Finding Type: follow-up hardening
  - Locations:
    - `app/security/execution_sandbox.py`
    - `tests/test_execution_sandbox.py`
    - `docs/orchestration/LOCAL_EXECUTION_SANDBOX_RUNBOOK.md`
  - Reason: PR #1013 lands the local sandbox foundation, but two higher-cost hardening items remain intentionally deferred: output-budget enforcement must move from post-capture truncation to streaming enforcement, and the explicit binary allowlist should be re-minimized after initial developer-machine adoption evidence is collected.
  - Links:
    - `app/security/execution_sandbox.py`
    - `tests/test_execution_sandbox.py`
    - `docs/orchestration/LOCAL_EXECUTION_SANDBOX_RUNBOOK.md`
    - `docs/review/PR_1013_FIXED_MAPPING.md`
  - DoD:
    - Sandbox stdout/stderr budget is enforced during process execution instead of after full `capture_output=True` buffering
    - Default and runbook binary allowlists are reviewed against real usage and reduced to the smallest stable set
    - Deterministic tests cover stream-budget enforcement and minimized allowlist behavior
    - `pre-commit run --all-files` and `make verify` pass in follow-up PR
  - Blockers: None (deferred by scope, not blocked)

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


- [ ] Security suppression expiry monitoring
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: N/A (ongoing)
  - Priority: P1
  - Area: security
  - Finding Type: policy exception
  - Locations:
    - `trivy/ignore-policy.rego` — Suppression expires: 2026-05-27
    - `.trivyignore` — CVE-2026-0861 expires: 2026-05-27
  - Reason: Upstream glibc CVEs unfixed; suppressions have expiry dates
  - Links:
    - docs/security/CVE-2026-0861-glibc.md
    - docs/security/CVE-2025-15281-glibc.md
  - DoD:
    - Weekly monitoring for upstream fixes
    - Remove suppressions when fixed versions available
    - Update base image when fixes land
  - **Last reviewed: 2026-02-27**
    - PR #929: Removed 4 upstream-fixed CVE suppressions (gpgv, gnutls, p11-kit)
    - PR #930: Extended review-by dates to 2026-05-27 for unfixed CVEs

---


### P2

<a id="ledger-p2-pr1-50-sharefile-hardening"></a>
- [ ] P2: PR 1-50 follow-up for shareFile browser hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-PR1-50-SHAREFILE-HARDENING
  - Area: frontend / export UX
  - Finding Type: deferred browser fallback hardening
  - Reason: `frontend/src/lib/shareFile.ts` still needs explicit `anchor.click()` fallback hardening and a targeted dead-code review, but that cleanup is intentionally deferred out of Wave 1 to keep the remediation PR focused on unresolved P0/P1 findings.
  - Links:
    - `frontend/src/lib/shareFile.ts`
    - `frontend/src/lib/shareFile.test.ts`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1-50-remediation-wave1`
  - DoD:
    - `anchor.click()` fallback behavior is hardened or explicitly justified with tests
    - Dead-code review for non-browser fallback paths is completed
    - Any behavior changes are covered by focused frontend tests

<a id="ledger-p2-pr1-50-glasscard-cleanup"></a>
- [ ] P2: PR 1-50 follow-up for GlassCard redundant guard cleanup
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-PR1-50-GLASSCARD-CLEANUP
  - Area: frontend / component hygiene
  - Finding Type: deferred type-driven cleanup
  - Reason: `frontend/src/components/GlassCard.tsx` still contains redundant typed-union undefined checks that are low-risk cleanup only and therefore intentionally excluded from Wave 1 remediation scope.
  - Links:
    - `frontend/src/components/GlassCard.tsx`
    - `frontend/src/components/__tests__/GlassCard.test.tsx`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1-50-remediation-wave1`
  - DoD:
    - Redundant undefined checks are removed or justified against a concrete runtime contract
    - Component tests stay green after cleanup
    - No visual or accessibility regressions are introduced

<a id="ledger-p2-pr1-50-ollama-diagnostic-deps"></a>
- [ ] P2: PR 1-50 follow-up for ollama_diagnostic dependency handling
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-PR1-50-OLLAMA-DIAGNOSTIC-DEPS
  - Area: scripts / diagnostics
  - Finding Type: deferred script portability
  - Reason: `ollama_diagnostic.sh` still assumes `jq` and `free` are present. The script needs explicit dependency handling or documentation, but this is intentionally deferred because it does not block Wave 1 P0/P1 remediation.
  - Links:
    - `ollama_diagnostic.sh`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1-50-remediation-wave1`
  - DoD:
    - Script checks for required external tools or documents prerequisites clearly
    - Failure mode is deterministic when dependencies are missing
    - Any documentation updates stay aligned with actual script behavior

<a id="ledger-p2-pr1-50-ollama-monitor-deps"></a>
- [ ] P2: PR 1-50 follow-up for ollama_monitor dependency handling
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-PR1-50-OLLAMA-MONITOR-DEPS
  - Area: scripts / diagnostics
  - Finding Type: deferred script portability
  - Reason: `ollama_monitor.sh` still assumes `bc` is available. This portability/documentation cleanup remains deferred so Wave 1 stays limited to unresolved P0/P1 findings.
  - Links:
    - `ollama_monitor.sh`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1-50-remediation-wave1`
  - DoD:
    - Script checks for `bc` or documents the dependency explicitly
    - Missing-dependency behavior is deterministic and user-readable
    - Follow-up changes preserve current monitoring semantics

<a id="ledger-p2-openai-docs-freshness-pilot"></a>
- [x] P2: Govern the OpenAI external docs freshness pilot lifecycle
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1100 -> PR #1108
  - Status: ✅ Closed after merged PR #1100; recorded in PR #1108 (`keep narrow`; review-cycle close-out only)
  - Area: docs / orchestration / dev-agent tooling
  - Finding Type: pilot lifecycle governance
  - Reason: PR #1100 introduces an optional external-docs lane for OpenAI-first
    dev-agent work. The pilot must have explicit graduation and rollback gates
    so it does not drift into hidden repo policy or CI/runtime scope.
  - Links:
    - `docs/audit/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT_DECISION_2026-03-10.md`
    - `docs/audit/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT_REVIEW_CYCLE_DECISION_2026-03-11.md`
    - `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md`
    - `docs/dev/CODEX_SKILLS.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
    - `docs/review/PR_1100_FIXED_MAPPING.md`
    - `docs/review/PR_1108_FIXED_MAPPING.md`
  - Blockers:
    - Need one full review cycle of real OpenAI-first usage evidence
    - Need confirmation that external-docs guidance stays accurate without CI
      coupling
  - DoD:
    - A follow-up decision records keep, adjust, or stop for the pilot after one
      review cycle
    - At least one durable workflow insight is either promoted through KPP or
      explicitly marked as non-canonical
    - The runbook stays aligned with the chosen auth model for Context7 and the
      preferred invocation model for Context Hub
    - No CI/runtime/production integration is introduced under this ledger item

<a id="ledger-p2-dsar-transaction-neutral-helper"></a>
- [ ] P2: Make internal DSAR delete helper transaction-neutral
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-DSAR-TRANSACTION-NEUTRAL-HELPER
  - Area: backend / privacy
  - Finding Type: transaction-boundary hardening
  - Reason: `delete_direct_user_artifacts()` currently owns `commit()` / `rollback()` while accepting a caller-provided SQLAlchemy `Session`. That is acceptable for the current support-led standalone helper contract, but a future support/admin workflow may batch DSAR artifact deletion with other writes on the same session. The helper should eventually declare or narrow its transaction ownership explicitly instead of implicitly committing caller-owned work.
  - Links:
    - `core/compliance/dsar_service.py`
    - `tests/test_compliance_control_plane.py`
    - `docs/compliance/DSAR_AND_DELETION_MAP.md`
  - DoD:
    - The DSAR helper either becomes transaction-neutral or moves to an explicit session/transaction ownership contract
    - Tests cover caller-owned session behavior for batched writes and rollback semantics
    - Support-led DSAR docs stay aligned with the final ownership contract

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


- [ ] P2: Rename legacy `vip_llm_monthly_usage` table to tier-neutral name
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR TBD
  - Status: Planned
  - Reason (EN): The monthly quota model is tier-scoped, but the persisted table name remains VIP-specific for backward compatibility and needs a dedicated migration.
  - Links:
    - `app/models/llm_quota_usage.py`
    - `app/security/llm_monthly_quota.py`
    - `docs/audit/PR_647_VIP_LLM_MONTHLY_QUOTA_AUDIT.md`
  - DoD:
    - Add DB migration from `vip_llm_monthly_usage` to a tier-neutral table name
    - Keep backward-compatible rollout/rollback notes linked from audit/docs evidence
    - Update ORM/model references and deterministic quota tests


<a id="ledger-p2-unified-aicoach"></a>
- [ ] P2: Unified Framework implementation (UnifiedAICoach: Philosophy + Math + CBT integration)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (integration of all components after individual implementations)
  - Target PR: PR-TBD-UNIFIED-AICOACH-PHASE5
  - Status: 📋 Planned (integration wave)
  - Dependencies:
    - [P1 Philosophical logic principles](#ledger-p1-philosophical-logic)
    - [P1 Recursive methods](#ledger-p1-recursive-methods)
    - [P1 Frontend parity for AI reliability](#ledger-p1-frontend-ai-parity)
    - [P0 Payment rails RU/BY + iOS baseline](#ledger-p0-payments-ruby-ios)
  - Reason (EN): Integrate all components (Philosophical validation, Recursive methods, Bayesian personalization, CBT coaching) into a unified production-ready framework. Hypothesized impact (pending benchmark validation): multiplicative quality gains (70-80% improvement), latency optimization (50-60% reduction), unified user experience. **Production readiness:** Framework includes rate-limiting, caching, monitoring, error handling, privacy protection, and fallback mechanisms as documented in peer review analysis. (RU: Интеграция всех компонентов (философская валидация, рекурсивные методы, байесовская персонализация, CBT coaching) в единый production-ready фреймворк. Гипотеза (с обязательной валидацией бенчмарками): мультипликативное улучшение качества (70-80%), оптимизация latency (50-60%), единый пользовательский опыт. **Production readiness:** Фреймворк включает rate limiting, caching, monitoring, error handling, privacy protection и fallback механизмы, как документировано в peer review analysis.)
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
    - Hypothesis target (requires benchmark validation): latency ≤0.8s (P95) for QUESTION queries, ≤0.3s for COMMAND/EXPRESSION, verification rate ≥95%, factual error rate <3%
    - Hypothesis target (requires benchmark validation): ≤$0.008 per query (VIP tier), cache hit-rate ≥50%
    - Validation evidence owner: [P1 Scientific reliability publication pipeline](#ledger-p1-scientific-reliability-pipeline)
    - Documentation: production deployment guide, monitoring setup, troubleshooting runbook
    - **Production deployment:** Framework deployed to production with feature flag (gradual rollout)


- [ ] P2: Vector retrieval for RAG (pgvector + sentence-transformers)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (AI / RAG)
  - Target PR: PR-next-6 (runtime)
  - Status: Planned
  - Reason (EN): Replace Jaccard-only retrieval with semantic search; pgvector already in W4 food search. Improves retrieval quality 40–60% per audit.
  - Links:
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md` (sect. 4.1, 5.1)
    - `core/rag/simple_rag.py`, W4 semantic search implementation
  - DoD:
    - Feature-flagged vector retrieval; fallback to current Jaccard path
    - Latency and recall documented; `make verify` passes


- [ ] P2: Wave 3 RAG v2 + safety evals + reliability game days
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-W3-RAG-SAFETY
  - Status: Planned (Wave 3 / day 91-180)
  - Area: AI platform / security / reliability
  - Finding Type: modernization / risk reduction
  - Locations:
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
  - Reason: scale AI capability with explicit safety gates and degraded-mode confidence before broad autonomy.
  - Links:
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
  - DoD:
    - RAG v2 capability scope and citation/eval expectations documented
    - Safety regression gate classes documented (jailbreak/policy bypass)
    - Reliability game day scenarios and ownership defined


<a id="ledger-p2-android-keystore-conformance"></a>
- [ ] P2: Android Keystore secret storage conformance (deferred track)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (deferred until Android monetization activation)
  - Target PR: PR-TBD-ANDROID-KEYSTORE-CONFORMANCE
  - Status: ⏸️ Deferred
  - Reason (EN): Master checklist item #6 remains deferred because current monetization baseline is iOS-first + RU/BY manual rails; Android billing/runtime is not in active delivery scope yet.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-mobile-secret-conformance
    - docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-payments-ruby-ios
  - DoD:
    - Resume trigger is explicit: Android billing tasks (`#9/#23/#24/#32`) move from `Deferred` to `Now/Next`
    - Android app storage layer documents and enforces Keystore-only secret handling
    - Guard tests prevent insecure storage fallback on Android


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


<a id="ledger-p2-rag-feedback-pii-minimization"></a>
- [ ] P2: Reassess feedback and RAG preview minimization beyond regex redaction
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-RAG-FEEDBACK-PII-MINIMIZATION
  - Area: backend / privacy / RAG
  - Finding Type: privacy hardening follow-up
  - Reason: Regex-based redaction exists, but feedback storage and RAG source previews still rely on best-effort masking. A focused review should decide whether previews/queries need stronger minimization or retention tightening.
  - Links:
    - `app/routers/feedback.py`
    - `core/pii_redaction.py`
    - `core/rag/simple_rag.py`
    - `tests/test_feedback_api.py`
    - `tests/test_cbt_insight_api.py`
  - DoD:
    - Sensitive feedback fields and RAG previews are classified by retention/need-to-store level
    - Any fields not required for product analytics are minimized or removed
    - Tests cover the chosen minimization/redaction contract
    - Security posture doc reflects the final storage policy


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


- [ ] P2: Orchestration — agent clusters (scaling for 40+ agents)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD (future)
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: scalability
  - Reason: 26 agents; coordinator routes to each. At scale (40+ agents) routing becomes unwieldy. Cluster-first routing (backend, frontend, ml, research, security) scales better.
  - Links:
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Cluster definitions documented
    - Routing logic updated or documented for future adoption


- [ ] P2: Canary / disclaimer for published agent evals
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD (if we publish)
  - Status: Planned
  - Area: docs / compliance
  - Finding Type: process
  - Reason: If we ever publish agent prompts or evaluation snippets, add canary or disclaimer per EVMbench ("Internal evaluation artifact; do not use for training").
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
  - DoD:
    - Policy or template added; apply only when publishing evals


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


- [ ] P2: Stabilize nosec allowlist keys (path + token/hash, not line)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: guards / tech-debt
  - Finding Type: robustness
  - Reason: Line-based allowlist entries drift on any file edit; allowlist should key by path + code-fragment hash or token so refactors do not require allowlist updates.
  - Links: `tests/guards/fixtures/nosec_policy_allowlist.txt`, `tests/guards/test_nosec_policy_guard.py`
  - DoD: Allowlist format supports path + stable identifier (hash/snippet); guard matches by identifier; line number optional or derived.


- [ ] P2: Subprocess guard — multiline and indirection-aware (AST-based) detection
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: guards / security policy
  - Finding Type: optional improvement (Cubic suggestion)
  - Reason: Current guard scans single-line subprocess calls; multiline invocations (e.g. `subprocess.run([\n  "gh", ...])`) and simple indirection (e.g. `cmd = [...]` then `subprocess.run(cmd)`) may escape detection. Extend to multiline or AST-based scan.
  - Links:
    - `tests/guards/test_subprocess_uses_absolute_binaries.py`
    - `AGENTS.md` (subprocess absolute path policy)
  - DoD:
    - Guard detects banned binaries when call spans multiple lines, or document limitation
    - Guard catches simple indirection (e.g. cmd = [...] then subprocess.run(cmd)); AST-based scan preferred
    - Success criterion: no new failures on current main; no false negatives on existing codebase


- [ ] P2: Frontend and iOS explainer surfaces on current journey pages
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (rendering follow-up)
  - Target PR: PR-TBD-EXPLAINER-SURFACES
  - Status: 📋 Planned
  - Reason (EN): After the backend contract exists, explainers should be rendered on existing BMI, PRO interpretation, progress, and weekly-plan surfaces. Delivery must remain thin-client on web and iOS. (RU: После contract phase explainers нужно отрисовать на текущих user journey surfaces без дублирования бизнес-логики на клиентах.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `frontend/`
    - `ios/`
    - `docs/product/FREE_PRO_CONTRACT.md`
  - DoD:
    - Surface map is defined for web and iOS on current FREE / PRO / VIP pages
    - Rendering remains presentation-only; business logic stays on backend
    - Copy stays wellness-safe and aligned with the trust-based funnel


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


- [ ] P2: Execution Wave 3-R4 — Export adapter + deterministic contract tests
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #TBD-W3-R4-EXPORT-TESTS (`feat/restaurants-w3-r4-observability-rollback`)
  - Status: 🟡 In progress
  - Reason: Guarantee stable mapping from weekly plan artifacts to partner payloads.
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md
    - app/routers/plan_export.py
    - tests/test_pro_restaurant_partner_api.py
  - DoD:
    - Mapping rules from weekly plan/recipes/constraints to partner payload documented
    - Deterministic contract tests defined and passing
    - Rollback-safe rollout notes captured in audit artifact

---


- [ ] P2: Explainer progress telemetry and experimentation package
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (measurement follow-up)
  - Target PR: PR-TBD-EXPLAINER-TELEMETRY
  - Status: 📋 Planned
  - Reason (EN): Explainers and learning cycles need completion and unlock telemetry so the product can measure trust, retention, and progression. This should reuse existing progress/live-indicator patterns instead of creating a parallel growth system. (RU: Для explainers и learning cycles нужна телеметрия completion/unlock, но она должна переиспользовать текущие progress patterns и оставаться privacy-safe.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `frontend/src/features/progress/`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - DoD:
    - Canonical `explainer_progress_event` fields are documented
    - Telemetry design is low-cardinality and privacy-safe
    - Experimentation scope is additive and does not introduce a new gamification system in MVP


- [ ] P2: Optional interactive simulator micro-surfaces for wellness understanding
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional product clarity)
  - Target PR: PR-TBD-WELLNESS-SIMULATOR-MICRO-SURFACES
  - Status: 📋 Planned
  - Reason (EN): TensorTonic's strongest reusable learning mechanic is the combination of explanation, scenario, pitfalls, and interactive simulation. PulsePlate can selectively adapt this for wellness-safe cases such as adherence confidence stability or interpretation confidence with more data, but only as deterministic micro-surfaces grounded in current product logic. (RU: Самая полезная механика для адаптации — explanation + scenario + pitfalls + simulator; у нас это допустимо только для wellness-safe и rules-first micro-surfaces.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md`
    - `core/`
  - DoD:
    - Candidate simulator cases are documented and validated as wellness-safe
    - Simulator logic is deterministic and local to existing product rules
    - No new heavy LLM endpoint or public gamification mechanics are introduced


- [ ] P2: Rules-first learning-cycle engine and unlock semantics
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (product behavior foundation)
  - Target PR: PR-TBD-LEARNING-CYCLE-ENGINE
  - Status: 📋 Planned
  - Reason (EN): PulsePlate needs deterministic unlock rules based on current BMI, interpretation, adherence, and weekly-plan signals. The cycle model must reward understanding and adjustment, not streak preservation or social pressure. (RU: Нужны детерминированные unlock rules для learning cycles без streak-shame и без social ranking.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `core/`
    - `app/routers/pro.py`
    - `app/routers/vip.py`
  - DoD:
    - Canonical `learning_cycle_state` fields are documented
    - Unlock rules use existing backend signals only
    - Design explicitly bans public leaderboards, addictive streak loops, and ranking mechanics in MVP


- [ ] P2: Stage-4 query-aware contradiction detection alignment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality improvement)
  - Target PR: PR-TBD-RAG-STAGE4-QUERY-AWARE
  - Status: 📋 Planned
  - Reason: Contradiction checks in Stage-4 should explicitly incorporate active user query semantics to reduce context-irrelevant flags and improve reliability scoring fidelity.
  - Links:
    - `docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md`
    - `docs/contracts/RAG_CONTRACT.md`
    - `core/rag/philosophy_pipeline.py`
    - `core/rag/validation.py`
    - `tests/test_philosophy_validation_integration.py`
  - DoD:
    - Stage-4 contradiction detection consumes query-aware context deterministically
    - Validation tests cover relevant/irrelevant contradiction scenarios
    - Reliability fields (`verification_state`, `confidence`) remain backward-compatible


<a id="ledger-p2-wellness-explainers-learning-cycles"></a>
- [ ] P2: Wellness Explainers + Learning Cycles MVP (rules-first, trust-first)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (product differentiation + trust/retention)
  - Target PR: PR-TBD-WELLNESS-EXPLAINERS-MVP
  - Status: 📋 Planned
  - Reason (EN): Adapt the strongest publicly visible product patterns from TensorTonic without turning PulsePlate into an ML academy. The fit is deterministic explainers, learning-cycle progression, interactive confidence/progress framing, and practice loops tied to existing wellness outputs. This work must remain wellness-safe, backend-owned, and free from streak-shame, leaderboards, or new heavy LLM surface area. (RU: Интегрировать explainers и learning cycles поверх текущих wellness-сущностей; без ML-куррикулума, public leaderboard и без нового дорогого AI-контура.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_LEARNING_CYCLES_MINI_PRD.md`
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `docs/product/FREE_PRO_SOFT_PAYWALL.md`
    - `docs/audience_pack/FACTS_CANONICAL.md`
    - `docs/analysis/SCIENTIFIC_INNOVATION_ANALYSIS.md`
    - `core/insight/philosophy_validator.py`
    - `docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md`
    - `https://www.tensortonic.com/`
    - `https://www.tensortonic.com/ml-math`
    - `https://www.tensortonic.com/ml-math/statistics/ab-testing`
  - DoD:
    - Backend-owned explainer and learning-cycle direction is documented against existing FREE / PRO / VIP entities
    - MVP scope explicitly bans ML curriculum, browser IDE, public leaderboard, and streak-pressure mechanics
    - Follow-up execution is split into contract, engine, UI, telemetry, and simulator slices
    - Follow-up items reference `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md` for canonical explainer guardrails instead of restating them in parallel
    - MVP path introduces no new heavy LLM endpoint; any optional AI-assisted copy remains guarded by existing safety/economics rules
    - Product copy remains wellness-safe and evidence-aligned
    - GTM framing stays clarity-first and wellness-safe

- [ ] P1: Explainer contract and payload design for FREE / PRO / VIP
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (contract-first unblocker)
  - Target PR: PR-TBD-EXPLAINER-CONTRACT-PAYLOADS
  - Status: 📋 Planned
  - Reason (EN): The first implementation slice should lock backend-owned payload shapes before any UI work. PulsePlate needs canonical response shapes for explainer cards that reuse current BMI, interpretation, adherence, and weekly-plan entities instead of inventing client heuristics. (RU: Сначала нужен каноничный backend contract для explainer payloads; UI не должен сам собирать бизнес-логику.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `app/schemas/`
    - `app/routers/`
  - DoD:
    - High-level contract documents backend-owned `explainer_card` fields for FREE / PRO / VIP
    - Existing product entities are mapped to explainer payload sources without client-side business logic duplication
    - No runtime implementation is required in the design PR

- [ ] P2: Rules-first learning-cycle engine and unlock semantics
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (product behavior foundation)
  - Target PR: PR-TBD-LEARNING-CYCLE-ENGINE
  - Status: 📋 Planned
  - Reason (EN): PulsePlate needs deterministic unlock rules based on current BMI, interpretation, adherence, and weekly-plan signals. The cycle model must reward understanding and adjustment, not streak preservation or social pressure. (RU: Нужны детерминированные unlock rules для learning cycles без streak-shame и без social ranking.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `core/`
    - `app/routers/pro.py`
    - `app/routers/vip.py`
  - DoD:
    - Canonical `learning_cycle_state` fields are documented
    - Unlock rules use existing backend signals only
    - Design explicitly bans public leaderboards, addictive streak loops, and ranking mechanics in MVP

- [ ] P2: Frontend and iOS explainer surfaces on current journey pages
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (rendering follow-up)
  - Target PR: PR-TBD-EXPLAINER-SURFACES
  - Status: 📋 Planned
  - Reason (EN): After the backend contract exists, explainers should be rendered on existing BMI, PRO interpretation, progress, and weekly-plan surfaces. Delivery must remain thin-client on web and iOS. (RU: После contract phase explainers нужно отрисовать на текущих user journey surfaces без дублирования бизнес-логики на клиентах.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `frontend/`
    - `ios/`
    - `docs/product/FREE_PRO_CONTRACT.md`
  - DoD:
    - Surface map is defined for web and iOS on current FREE / PRO / VIP pages
    - Rendering remains presentation-only; business logic stays on backend
    - Copy stays wellness-safe and aligned with the trust-based funnel

- [ ] P2: Explainer progress telemetry and experimentation package
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (measurement follow-up)
  - Target PR: PR-TBD-EXPLAINER-TELEMETRY
  - Status: 📋 Planned
  - Reason (EN): Explainers and learning cycles need completion and unlock telemetry so the product can measure trust, retention, and progression. This should reuse existing progress/live-indicator patterns instead of creating a parallel growth system. (RU: Для explainers и learning cycles нужна телеметрия completion/unlock, но она должна переиспользовать текущие progress patterns и оставаться privacy-safe.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `frontend/src/features/progress/`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - DoD:
    - Canonical `explainer_progress_event` fields are documented
    - Telemetry design is low-cardinality and privacy-safe
    - Experimentation scope is additive and does not introduce a new gamification system in MVP

- [ ] P2: Optional interactive simulator micro-surfaces for wellness understanding
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (optional product clarity)
  - Target PR: PR-TBD-WELLNESS-SIMULATOR-MICRO-SURFACES
  - Status: 📋 Planned
  - Reason (EN): TensorTonic's strongest reusable learning mechanic is the combination of explanation, scenario, pitfalls, and interactive simulation. PulsePlate can selectively adapt this for wellness-safe cases such as adherence confidence stability or interpretation confidence with more data, but only as deterministic micro-surfaces grounded in current product logic. (RU: Самая полезная механика для адаптации — explanation + scenario + pitfalls + simulator; у нас это допустимо только для wellness-safe и rules-first micro-surfaces.)
  - Links:
    - `docs/product/WELLNESS_EXPLAINERS_TENSORTONIC_ADAPTATION_NOTE.md`
    - `docs/product/FREE_PRO_CONTRACT.md`
    - `docs/insights/PERFORMANCE_ANALYSIS_AND_NEW_INSIGHTS.md`
    - `core/`
  - DoD:
    - Candidate simulator cases are documented and validated as wellness-safe
    - Simulator logic is deterministic and local to existing product rules
    - No new heavy LLM endpoint or public gamification mechanics are introduced

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


- [ ] P2: Add runbook or CLI helper for resolving review threads
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: orchestration / CI / review governance
  - Finding Type: operational clarity
  - Reason: Resolving threads via GraphQL is non-obvious for agents and new contributors; one-command helper or runbook section reduces operator friction.
  - Links:
    - `RUNBOOK_AGENT.md` (pre-merge readiness, merge-readiness script)
    - `scripts/orchestration/check_review_threads_disposition.py:444` (CLI entry)
  - DoD:
    - RUNBOOK_AGENT.md section with exact commands for thread resolution, or script scripts/orchestration/resolve_review_threads.py (or equivalent) with documented usage


- [ ] P2: Agent run summary artifact (checklist or JSON)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-ORCHESTRATION
  - Status: Planned
  - Area: orchestration / agents
  - Finding Type: observability
  - Reason: Lightweight artifact (checklist/JSON) produced by coordinator or runner for high-value tasks to support future metrics.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
  - DoD:
    - Design doc or ADR: format and when to produce; no implementation required in this item


- [ ] P2: Extend trigger-only ban with optional allowlist TTL (if needed)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: orchestration / review governance
  - Reason: If an exception is ever needed for a trigger-only mapping, add TTL allowlist (same style as nosec: remove-by, ref); empty by default.
  - DoD: Allowlist file exists (or doc); format documented; guard consults allowlist when present.


- [ ] P2: Integrate review-thread disposition guard into pre-flight
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #986 or PR-TBD
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Make disposition check always-on by calling `check_review_threads_disposition.py` from `scripts/orchestration/check_preflight.py` and documenting in `workflow.md`.
  - Links:
    - `scripts/orchestration/check_review_threads_disposition.py`
    - `scripts/orchestration/check_preflight.py`
    - `docs/orchestration/workflow.md`
  - DoD:
    - Pre-flight runs disposition guard when in PR context (or always)
    - workflow.md updated with required step
    - No regression in pre-flight runtime


- [ ] P2: Invariant-only prompt for fix-CI / fix-guard tasks
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-ORCHESTRATION
  - Status: Planned
  - Area: orchestration / agents
  - Finding Type: process
  - Reason: In agent prompts for "fix CI" or "fix guard", explicitly add "do not change invariants; only fix the failing check".
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
  - DoD:
    - Coordinator or ci-watcher prompt template updated with invariant-preservation instruction
    - No code change to guards themselves


- [ ] P2: Make trigger-only mapping ban path-aware for file-scoped review comments
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD
  - Area: orchestration / review governance
  - Finding Type: process hardening
  - Reason: Current empty/rerun checks are heuristic; if thread is file-scoped, mapped SHA should touch same file for stronger proof.
  - Links:
    - `scripts/orchestration/check_review_threads_disposition.py:170` (trigger-only check), `:518` (guard)
    - `tests/test_review_threads_disposition_strict.py`
    - `AGENTS.md:106` (FIXED proof quality, trigger-only ban)
  - DoD:
    - If thread comment is tied to a file path, mapping SHA must change that file
    - Tests cover allow (SHA touches file) and deny (SHA does not touch file)


- [ ] P2: RAG for agent context (explore)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-RAG
  - Status: Research
  - Area: orchestration / RAG
  - Finding Type: exploration
  - Reason: Explore retrieval-augmented context for coordinator/specialist agents (e.g. retrieve AGENTS.md sections by path); keep full SoT as baseline.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `docs/orchestration/workflow.md`
  - DoD:
    - Decision: adopt or decline; if adopt, document in orchestration and one pilot use case


- [ ] P2: Skill routing wave 2 — compositional task semantics + approved research connectors
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-SKILL-ROUTING-WAVE2
  - Area: orchestration / research / product governance
  - Finding Type: capability expansion
  - Reason: PR #1022 establishes deterministic weighted skill routing and explicit scraping blocks. The next wave should deepen routing quality without breaking explainability: compositional task semantics, bounded telemetry feedback, and research-only connectors approved for PulsePlate.
  - Links:
    - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
    - `scripts/orchestration/skill_router.py`
    - `scripts/orchestration/task_bootstrap.py`
    - `docs/dev/CODEX_SKILLS.md`
  - DoD:
    - Task packets expose a stable skill-routing explanation schema with compact per-skill evidence
    - Routing model adds compositional lexeme groups or ontology tags without introducing nondeterministic scoring
    - Approved research-only connector policy is implemented for narrow sources only: YouTube transcripts, X/Twitter official API or compliant exports, Google Trends
    - No runtime scraping surface is added to product endpoints
    - Deterministic tests cover allowlisted research connectors and blocked low-fit scraping requests
    - `make verify` and `pre-commit run --all-files` pass in PR scope

<a id="ledger-p2-fitchef-sandbox-phase-2-deferred-scope"></a>
- [ ] P2: FitChef sandbox Phase 2 deferred scope
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1064 (`docs(ledger): freeze fitchef mascot phase 2 contract`)
  - Status: Open
  - Area: orchestration / product runtime / sandbox integration
  - Finding Type: scope control
  - Locations:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
  - Reason: The original sandbox Phase 2 seam from PR #1013 now resolves into the mascot-coaching rollout contract. The current P2 execution family is limited to text-only FitChef coaching surfaces under the canonical `/api/v1/insight/fitchef*` namespace, while exports, realtime fan-out, image/CV ingestion, and broader autonomy remain explicitly deferred beyond this wave.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
    - `docs/review/PR_1013_FIXED_MAPPING.md`
  - DoD:
    - Phase 2 mascot scope is frozen in a current-repo contract doc with canonical routes under `/api/v1/insight/fitchef*`
    - Product/runtime docs link the same mascot plan and do not describe exports, realtime progress, or autonomy as already live
    - Security review confirms each mascot endpoint keeps policy/quota/audit gates ahead of execution
  - Blockers: None (deferred by scope, not blocked)

- [ ] P2: Violations-addressed list in security/guard remediation PRs
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD (optional per-PR)
  - Status: Planned
  - Area: process / PR template
  - Finding Type: auditability
  - Reason: Optional "violations addressed" list in PR description for guard/security remediation makes coverage auditable (EVMbench-style).
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
  - DoD:
    - PR template or runbook suggests optional "Violations addressed" section for guard/security remediation PRs
    - Not mandatory; adopt when useful

<a id="ledger-p2-cv-photo-food"></a>
- [ ] CV (photo → food): contract schema + uncertainty/degrade UX states + privacy packet
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: TBD
  - Priority: P2
  - Area: product / AI / contracts
  - Finding Type: future feature
  - Reason: If we add photo-based food recognition, it must be contract-first and uncertainty-aware
    (confidence fields, nullability, deterministic degrade states) with explicit privacy UX and retention rules.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (`cv-agent`; degrade-state expectations)
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


- [ ] P2 Vision: Restaurant/chef integration (partners accept menus from our products, cook for users)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #TBD-W3-R1-CONTRACT (umbrella split into W3-R1..W3-R4)
  - Priority: P2 (long-term product direction)
  - Reason (EN): Restaurants and individual chefs accept menus from our products (weekly plan, recipes, constraints) and cook food for users. Separate block from coaching and social network; requires clear "menu → partner" contract and technical prerequisites in program (see RESTAURANT_INTEGRATION_SPEC.md). (RU: Рестораны и индивидуальные повара принимают меню по нашим продуктам (недельный план, рецепты, ограничения) и готовят еду пользователям. Отдельный блок от коучинга и соцсети; требует чёткого контракта «меню → партнёр» и технических предпосылок в программе.)
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md (technical prerequisites, contract schema, implementation plan)
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md (temporary seam + exit criteria)
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
    - Execution decomposition W3-R1..W3-R4 is recorded with per-wave DoD
    - Implementation — separate PRs (export format, partner API or signed link, optionally partner directory)


- [ ] P2: C4-b Sandboxed execution boundary for high-risk agent actions
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1013
  - Status: 🟡 In progress (local sandbox foundation implemented in PR #1013, pending merge)
  - Area: security / agent control plane
  - Finding Type: security hardening
  - Locations:
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md:73` (C4-b row)
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md:77` (`ExecutionSandbox` boundary)
    - `app/security/execution_sandbox.py`
    - `tests/test_execution_sandbox.py`
  - Reason: Local bounded sandbox execution is now implemented for developer-machine workflows, but the broader stronger-isolation boundary is not merged yet.
  - Links:
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
  - DoD:
    - ADR-003 updated with local sandbox boundary, resource limits, and follow-up stronger-isolation scope
    - Runtime sandbox enforcement implemented in `app/security/execution_sandbox.py`
    - Deterministic tests: allowlisted command allowed in sandbox, blocked mode/disallowed binary rejected
    - `.env.example` documents sandbox toggles and bounds
  - Blockers: None (pending PR merge, not blocked)


- [ ] P2: Scoped token nonce — replace deterministic HMAC tokens with nonce-bearing tokens
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-TOKEN-NONCE (Wave 2)
  - Status: Planned
  - Area: security / agent control plane
  - Finding Type: security hardening
  - Locations:
    - `app/security/agent_control_plane.py:276` (`issue_scoped_token`)
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md:84` (Wave 2 scope)
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md:273` ("Known limitation" note)
  - Reason: MVP scoped tokens are deterministic (HMAC without nonce); identical scope + timestamp produces identical tokens. Replay risk is bounded by short TTL but should be eliminated.
  - Links:
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
  - DoD:
    - Nonce/random component design approved in ADR-003 amendment or new ADR
    - Backward-compatible rollout plan documented (old tokens expire within TTL window)
    - Deterministic tests updated: same scope + timestamp produces distinct tokens
    - No performance regression: token issuing latency under 1 ms p99
  - Blockers: None (deferred by priority, not blocked)

## Completed Items

Entries are sorted by priority, then theme, then title. Theme uses `Area:` when present and a deterministic title/domain fallback otherwise.

### P0

<a id="ledger-p0-billing-apple-verify"></a>
- [x] P0: Apple receipt verification backend follow-through
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR `#1074` (`feat(billing): add Apple receipt verification endpoint`)
  - Status: ✅ Completed (Merged PR #1074 on 2026-03-10)
  - Merge SHA: `e0104c540bfb63cc2fd944090d293c7b751651e8`
  - Area: backend / payments / iOS monetization
  - Finding Type: payment integrity
  - Reason (EN): The iOS-first billing baseline now exists, but automatic activation remains incomplete until server-side Apple receipt verification is treated as a canonical follow-through item rather than an implied subtask.
  - Links:
    - `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
    - `app/routers/billing.py`
    - `docs/review/PR_1074_FIXED_MAPPING.md`
    - `app/services/payments_activation.py`
  - DoD:
    - Server-side Apple receipt verification normalizes into the canonical billing activation flow
    - Receipt verification failure modes are deterministic and test-covered
    - Activation/status contracts stay additive for existing clients

<a id="ledger-p0-session-cookie-hardening"></a>
- [x] P0: Web session token transport hardening (`localStorage` -> `httpOnly` cookie)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (security blocker)
  - Target PR: PR #1003 (`fix(auth): align web session UI gates`) -> PR #1030 -> PR #1063
  - Status: ✅ Merged evidence (web session migration delivered on `main`; audit trail reconciled in a later docs/security follow-up)
  - Reason (EN): Master checklist item #1 identified XSS exposure when auth/session keys were persisted in browser storage. That web runtime gap is now closed on `main`: PR #1003 moved route gating toward session-backed auth state, PR #1030 hardened the W1 migration path, and PR #1063 removed the remaining storage-seeded smoke/logout coupling while keeping cleanup semantics fail-closed in `frontend/src/auth/storage.ts`. This backlog item is therefore closed as delivered evidence rather than carried forward into a fake W2 runtime PR. The canonical closure was reconciled later in a docs/security follow-up so the ledger matches already-merged runtime evidence. (RU: Web runtime gap по browser-stored auth secrets уже закрыт в `main`: PR #1003 перевёл gate-логику на session truth, PR #1030 усилил W1 migration path, PR #1063 убрал оставшуюся storage-seeded smoke/logout связку и оставил cleanup fail-closed. Псевдо-carryover `PR-TBD-SESSION-COOKIE-HARDENING-W2` больше не нужен; поздний docs/security follow-up лишь синхронизировал ledger с уже смерженным runtime evidence.)
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - app/security/auth.py
    - app/routers/pro_registration.py
    - frontend/src/auth/storage.ts
    - frontend/src/components/TabBar.tsx
    - frontend/src/auth/__tests__/storage.test.ts
    - frontend/src/components/__tests__/TabBar.test.tsx
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1003
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1030
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1063
  - DoD:
    - No sensitive session/auth token persists in browser local storage, including cleanup-failure paths
    - Session issuance/refresh flow uses secure cookie attributes (`HttpOnly`, `Secure`, `SameSite`)
    - Regression tests cover authenticated flows, logout/invalidation, and cleanup-failure semantics

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


<a id="ledger-p0-pro-vip-depends-guard"></a>
- [x] P0: PRO/VIP route `Depends` coverage guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (access-control integrity)
  - Target PR: PR #994
  - Status: ✅ Merged (PR #994, 2026-03-06)
  - Reason (EN): Master checklist item #7 requires deterministic proof that all protected endpoints enforce explicit dependency gates and no silent bypass is introduced by future routing changes.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - app/security/api_tiers.py
    - app/routers
    - tests/test_pro_vip_route_dependency_guard.py
    - tests/test_api_tiers_db_lookup.py
  - DoD:
    - Guard test enumerates canonical PRO/VIP surfaces and fails on missing dependency gate
    - Legacy aliases are validated as non-bypass paths
    - CI gate is deterministic and documented in runbook


<a id="ledger-p0-rag-input-sanitizer"></a>
- [x] P0: RAG input sanitizer integration for markdown/knowledge ingestion
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (security + data quality)
  - Target PR: PR-TBD-RAG-INPUT-SANITIZER -> PR #1044
  - Status: ✅ Merged (PR #1044, 2026-03-08)
  - Reason (EN): Query-level AI input blocking already existed in `app/security/agent_input_guard.py`, but markdown/knowledge ingestion and retrieval content still lacked a canonical sanitizer seam. PR #1044 closed that gap by sanitizing markdown before indexing, sanitizing retrieved chunk content before prompt assembly, dropping sanitized-empty chunks, and surfacing an explicit CBT warning when source content was sanitized.
  - Links:
    - docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md
    - core/data_sanitizer.py
    - core/rag/simple_rag.py
    - core/rag/vector_rag.py
    - core/rag/formatting.py
    - core/rag/recursive_retrieval.py
    - app/routers/cbt_insight.py
    - app/security/agent_input_guard.py
    - tests/test_data_sanitizer.py
    - tests/test_rag_orchestration.py
    - tests/test_cbt_insight_api.py
    - https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1044
  - DoD:
    - ✅ Sanitization is applied deterministically before RAG indexing and retrieval
    - ✅ Injection-pattern regression tests are added and green
    - ✅ No contract break for current insight endpoints


- [x] P0: Growth telemetry canon and KPI dashboard baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #845 (Phase 1 merged); Phase 2 (eventRegistry.ts) after PR #825 merge
  - Status: Phase 1 ✅ Merged (PR #845, 2026-02-21); Phase 2 deferred
  - Area: analytics / frontend / growth
  - Finding Type: product optimization
  - Locations:
    - `docs/analytics/ANALYTICS_INDEX.md`
    - `docs/analytics/METRICS_CATALOG.md`
    - `frontend/src/lib/telemetry/eventRegistry.ts`
  - Reason: establish canonical funnel semantics and events for onboarding -> paywall -> conversion -> retention.
  - Links:
    - `docs/analytics/EXPERIMENT_REGISTRY.md`
    - [PR #845](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/845) (Phase 1 docs)
  - DoD:
    - Core funnel metrics defined with owner and update cadence (Phase 1 in PR #845)
    - Event taxonomy anchored in docs and frontend registry (docs in PR #845; frontend in Phase 2)
    - Dashboard baseline requirements documented (Phase 1 in PR #845)


- [x] P0: Agent Control Plane MVP (policy gate + signed audit + secrets boundary)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: #846
  - Status: ✅ Completed (Merged PR #846 on 2026-02-21)
  - Area: architecture / backend / security
  - Finding Type: platform hardening / modernization
  - Locations:
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `docs/roadmap/PROGRAM_6M_BALANCED_2026H1.md`
  - Reason: replace third-party local agent dependency with policy-first, vendor-independent control plane.
  - Links:
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `app/security/agent_control_plane.py`
    - `tests/test_agent_control_plane_mvp.py`
  - Evidence (2026-02-21, America/New_York):
    - `app/security/agent_control_plane.py:1` — MVP primitives implemented:
      deny-by-default policy gate, signed audit envelope, and short-lived scoped token issuing.
    - `tests/test_agent_control_plane_mvp.py:1` — deterministic coverage for
      allowlist parsing, fail-closed policy decisions, audit signature verification, and token TTL validation.
  - DoD:
    - [x] Control plane MVP contract documented and accepted
    - [x] Deny-by-default policy requirements and fail-closed semantics documented
    - [x] Signed audit trail requirements documented with verification checklist
    - [x] Initial runtime primitives implemented with deterministic tests
    - [x] Follow-up implementation PRs opened and linked (PR #846)


- [x] P0: Food Data Platform Foundation (snapshot-first, multi-source, low-API-cost)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #886
  - Status: ✅ Merged (PR #886, 2026-02-24)
  - Area: architecture / data platform / product database
  - Finding Type: financial + architecture gap closure
  - Reason: The largest current financial and architecture gap is food/menus data quality and coverage. USDA+OFF foundations exist, but snapshot governance, canonical confidence/provenance policy, and structured execution waves are not yet locked as a canonical strategy.
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/design/RESTAURANT_INTEGRATION_SPEC.md`
    - `core/food_apis/`
    - `core/food_sources/`
    - `app/routers/foods.py`
  - DoD:
    - Strategy SoT is merged in docs-only PR
    - Source tiering and update cadence are finalized
    - Execution is split into wave PRs with clear ownership
    - Carryover/deferred mapping is documented in this ledger


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


- [x] P0-1: API Surface Governance / Namespace guards
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #909 (`feat/pr-909-food-db-next`)
  - Status: ✅ Merged (PR #909, 2026-02-26)
  - Area: backend / API governance / OpenAPI contracts
  - Finding Type: architecture governance gap
  - Reason: Public OpenAPI surface drift must be locked to canonical FREE/PRO/VIP namespaces to prevent schema sprawl and tier-discipline erosion.
  - Links:
    - `docs/architecture/ADR_API_SURFACE_CONSOLIDATION_2026-02-26.md`
    - `tests/test_openapi_namespace_guards.py`
    - `legacy_app.py`
    - `frontend/src/api/openapi.json`
  - DoD:
    - OpenAPI namespace guard test is merged and enforced in CI
    - Legacy `/api/v1/foods*` and `/api/v1/restaurants*` are hidden from OpenAPI schema
    - Runtime compatibility for legacy routes remains intact
    - API surface consolidation ADR is merged


- [x] P0-2: WS namespace migration (`/ws` -> `/api/v1/pro/ws`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #919 (`feat/p0-2-ws-canonical-clean`)
  - Status: ✅ Merged (PR #919, 2026-02-26)
  - Area: backend / realtime transport / API governance
  - Finding Type: namespace consistency follow-up
  - Reason: WebSocket path still uses transitional root namespace (`/ws`) and must align with canonical PRO surface while preserving a deprecation window.
  - Links:
    - `app/routers/realtime_ws.py`
    - `app/main.py`
    - `frontend/src/api/wsClient.ts`
  - DoD:
    - Canonical WebSocket endpoint available at `/api/v1/pro/ws`
    - `/ws` compatibility alias is deprecated with removal window documented
    - OpenAPI/guard policy updated to remove transitional `/ws` allowance
    - Frontend ws client defaults to canonical path


- [x] P0: Execution Wave 1 — Snapshot manager + OFF delta + canonical merge contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #889
  - Status: ✅ Merged (PR #889, 2026-02-24)
  - Area: backend / data ingestion
  - Finding Type: runtime foundation
  - Reason: Runtime needs deterministic snapshot lifecycle and incremental OFF updates before expansion to search and restaurants.
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `core/food_sources/`
    - `core/food_apis/update_manager.py`
    - `scripts/build_food_db.py`
  - DoD:
    - Immutable raw snapshot layout is implemented
    - Manifest/checksum policy is enforced fail-closed
    - Deterministic OFF delta ingestion is in place
    - Existing `/api/v1/foods*` behavior remains compatible


- [x] P0: Food data licensing + attribution compliance package
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #915 (`feat/food-api-attribution-compliance`)
  - Status: ✅ Merged (PR #915, 2026-02-26)
  - Area: backend / legal-compliance / API contracts
  - Finding Type: legal + governance risk closure
  - Reason: Food data sources include ODbL-licensed datasets (Open Food Facts). Runtime surface needs a canonical attribution contract and documented policy to reduce legal/compliance risk before broader partner growth.
  - Links:
    - `docs/legal/ODbL_COMPLIANCE.md`
    - `app/routers/pro_food_attribution.py`
    - `app/services/food_store.py`
    - `tests/test_pro_food_attribution.py`
  - DoD:
    - PRO endpoint returns source-level license + attribution metadata
    - Source attribution registry is centralized server-side (no client hardcoding)
    - Deterministic tests cover auth gate + contract payload
    - Compliance policy doc is merged and linked in backlog


- [x] P0: GDPR retention cleanup implementation (replace stub with safe deletion)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (privacy/compliance)
  - Target PR: PR #978 (`fix/gdpr-log-retention-cleanup`)
  - Status: ✅ Merged (PR #978, 2026-03-05)
  - Area: backend / compliance / operations
  - Finding Type: compliance hotfix
  - Reason: `cleanup_expired_logs()` was a non-destructive stub; privacy posture requires real retention enforcement with path safety and deterministic dry-run checks.
  - Links:
    - `core/log_retention.py`
    - `tests/test_log_retention_coverage.py`
    - `tests/test_fingerprint_and_retention.py`
  - DoD:
    - Real mtime-based cleanup is implemented under bounded retention root
    - Dry-run mode is additive and non-breaking
    - Deletion outside configured root is blocked (path-safety guard)
    - Deterministic tests cover dry-run, class filter, stat/unlink errors, and path boundary
    - `pre-commit run --all-files` and `make verify` pass in PR scope


<a id="ledger-p0-export-signing-hardening"></a>
- [x] P0: Harden private export signing secret and signable-path scope
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR-TBD-EXPORT-SIGNING-HARDENING -> PR #1035 (`fix(export): harden signing secret access`)
  - Status: ✅ Merged (PR #1035, 2026-03-08)
  - Area: backend / security / export signing
  - Finding Type: auth/config hardening
  - Reason: Repo truth already contains signable-path allowlisting and production/staging placeholder rejection in `settings.py`, but `app/routers/plan_export.py` still imports a static `EXPORT_TOKEN_SECRET` at module load. That keeps signing/verification vulnerable to runtime config drift and leaves the canonical hidden-schema contract under-tested.
  - Links:
    - `app/routers/plan_export.py`
    - `settings.py`
    - `signed_links.py`
    - `frontend/src/features/plan/WeeklyPlanViewer.tsx`
    - `tests/test_export_signed.py`
    - `docs/review/PR_1035_FIXED_MAPPING.md`
  - DoD:
    - Signing and verification use `get_export_token_secret()` at request time instead of a stale imported constant
    - Private export signing fails closed when `EXPORT_TOKEN_SECRET` is default/empty in production-like envs
    - Allowed sign targets stay restricted to canonical export routes actually used by product flows
    - Canonical `app.openapi()` keeps export routes hidden while runtime route registration stays intact
    - Deterministic tests cover deny/default-secret, deny/non-allowlisted-path, and hidden-schema regression branches
    - `pre-commit run --all-files` and `make verify` pass in PR scope


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


- [x] P0: OFF Vitamin D unit normalization (µg -> IU) + nameless-row guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (data correctness)
  - Target PR: PR #976 (`fix/off-vitd-unit-conversion`)
  - Status: ✅ Merged (PR #976, 2026-03-05)
  - Area: backend / food data normalization
  - Finding Type: correctness hotfix
  - Reason: Open Food Facts normalization writes `vitamin-d_100g` without deterministic µg→IU conversion and may ingest nameless rows; this degrades canonical nutrition trust and search quality.
  - Links:
    - `core/food_sources/off.py`
    - `tests/test_food_sources_simple.py`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
  - DoD:
    - OFF `vitamin-d_100g` is normalized via deterministic `iu_vitd_from_ug(...)`
    - Nameless rows are skipped fail-closed during OFF import
    - Deterministic tests cover µg→IU mapping and nameless-row skip behavior
    - `pre-commit run --all-files` and `make verify` pass in PR scope


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


- [x] Retro-audit PR window #838-#842: merge/comment timing + tail closure
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (process reliability)
  - Target PR: #842, #843, #844
  - Status: ✅ Completed (2026-02-21)
  - Area: CI/process governance + docs follow-up
  - Finding Type: post-merge audit + governance hardening
  - Reason: Multiple PRs were merged before full bot/comment cycle completion; we needed deterministic evidence,
    explicit tail closure, and technical merge-blocking controls.
  - Findings:
    - PR #838: only post-merge Codecov report (no actionables).
    - PR #839: post-merge cubic "No issues found" + Codecov (no actionables).
    - PR #840: post-merge review events (no actionable inline findings to apply).
    - PR #841: post-merge Sourcery actionable found; fixed and merged via PR #842.
    - PR #842: held until full green + bot pass; merged only after final CI completion.
    - PR #833 doc comment tail: no longer relevant on current `main` (already reflected in `AGENTS.md`).
    - PR #835 doc comment tail: still relevant; addressed via docs follow-up PR #843.
  - Links:
    - PR #842: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/842`
    - PR #843: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/843`
    - PR #844: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/844`
  - DoD:
    - ✅ Retro-audit evidence recorded for each PR in scope
    - ✅ Missed actionable from PR #841 remediated and merged
    - ✅ Docs tail from PR #835 moved to follow-up PR (#843)
    - ✅ Merge-readiness process hardened with CI policy gate PR (#844)


- [x] HPP Web visual workflow: Playwright deterministic smoke lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (frontend quality guardrail)
  - Target PR: #828, #840
  - Status: ✅ Merged (2026-02-21)
  - Area: frontend / HPP / e2e visual smoke
  - Finding Type: execution foundation
  - Reason: HPP route changes need deterministic browser smoke checks to catch critical UI regressions
    (`/`, `/plate`, `/progress`, `/pro`) before broader CI hardening.
  - Links:
    - `docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md`
    - `frontend/playwright.config.ts`
    - `frontend/e2e/`
  - DoD:
    - Playwright config and smoke specs exist for canonical HPP routes
    - `npm run test:e2e` and headed variant are available in `frontend/package.json`
    - Smoke checks run with deterministic local web server settings
    - Runbook contains npm-first execution commands


- [x] HPP Web visual workflow: Storybook bootstrap + first tokenized stories
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (frontend delivery accelerator)
  - Target PR: #828, #839
  - Status: ✅ Merged (2026-02-21)
  - Area: frontend / HPP / design-system tooling
  - Finding Type: execution foundation
  - Reason: HPP UI currently lacks isolated component review. Adding Storybook enables deterministic visual
    review of tokenized primitives before route-level integration and reduces regressions during rapid UI iteration.
  - Links:
    - `frontend/package.json`
    - `frontend/src/components/ui/`
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
  - DoD:
    - Storybook is wired in `frontend` (`storybook`, `build-storybook` scripts)
    - HPP stories exist for `SegmentedControl`, `Toggle`, `FormField`, and page-card shell
    - Token usage guidelines page exists for HPP states (default/realtime/fallback/conversion)
    - Storybook build passes in local verification


- [x] Web design-token hardening: Token SoT + palette switch + runtime raw-hex guard
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0 (frontend stability / drift prevention)
  - Target PR: #835, #837
  - Status: ✅ Merged (2026-02-21)
  - Area: frontend / design-system governance
  - Finding Type: policy hardening + runtime guard
  - Reason: Token drift risk and hardcoded runtime colors were allowing visual inconsistency. We fixed
    source-of-truth ownership, activated canonical palette tokens, and added deterministic guardrails
    to prevent future raw-hex regressions in runtime UI paths.
  - Links:
    - `docs/design/TOKENS_SOT.md`
    - `frontend/src/styles/tokens.css`
    - `frontend/src/styles/tokens.ts`
    - `tests/test_frontend_raw_hex_guard.py`
    - PR #835, PR #837
  - DoD:
    - ✅ Token SoT documented and merged
    - ✅ Canonical palette values active in web tokens
    - ✅ Plate chart raw hex replaced with token variables
    - ✅ Runtime raw-hex guard test merged with explicit allowlist

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


- [x] P0: Security hardening wave for agent automation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0
  - Target PR: PR #848 (docs/agent-sec-hardening-wave)
  - Status: ✅ Completed (PR #848, 2026-02-21, merge SHA `e7a58fb2`)
  - Area: security / runbooks / operations
  - Finding Type: incident prevention
  - Locations:
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
    - `RUNBOOK_AGENT.md`
  - Reason: enforce short-lived credentials, rotation protocol, and secret persistence bans after local-agent incident.
  - Links:
    - `docs/runbooks/README.md`
  - DoD:
    - [x] Rotation protocol documented and adopted for bot/API/webhook credentials
    - [x] Security release gate conditions documented
    - [x] Mandatory controls mapped to owner and verification evidence
  - Evidence (2026-02-21): PR #848 merged
  - Blockers: None (closed)


### P0-A / P0-B

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

- [x] P0-A: Stabilize web + iOS UX after Figma AI component integration regression
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P0-A (product works)
  - Target PR: PR #820 (Step 3 remediation)
  - Status: ✅ Merged (PR #820, 2026-02-19)
  - Reason: After recent Figma AI component/code updates, web UX quality regressed ("site looks bad"), and iOS app launch/open flow is broken. This blocks core product readiness and must be fixed before P1 work.
  - Links:
    - [PR #819](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/819)
    - [PR #818](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/818)
    - docs/runbooks/FIGMA_MCP_DESIGN_SYSTEM_RULES.md
    - frontend/ (affected UI surfaces, to be narrowed in triage)
    - ios/ (app-open failure triage scope)
  - Evidence (2026-02-19, America/New_York):
    - Step 1 (repro/verification):
      - `npm run test -- src/pages/__tests__/Home.test.tsx src/pages/__tests__/Plate.test.tsx src/pages/__tests__/Profile.test.tsx` -> `3 passed`
      - `npm run build` -> success (Vite build green)
      - `xcodebuild build -project PulsePlate.xcodeproj -scheme PulsePlate -destination "platform=iOS Simulator,id=8B9BF341-A44D-4BB0-A898-EC8CFEE56B79" -configuration Debug -derivedDataPath ../.derivedData` -> success
      - `xcodebuild test -project PulsePlate.xcodeproj -scheme PulsePlate -destination "platform=iOS Simulator,id=8B9BF341-A44D-4BB0-A898-EC8CFEE56B79" -configuration Debug -derivedDataPath ../.derivedData -skip-testing:PulsePlateUITests -only-testing:PulsePlateTests/PlateViewTests` -> success
    - Step 2 (root-cause isolation):
      - Web quality drift traced to presentation-layer style pattern drift in `frontend/src/pages/Home.tsx`, `frontend/src/pages/Plate.tsx`, `frontend/src/pages/Profile.tsx` (inline card styles / inconsistent CTA treatment vs tokenized runbook rules)
      - iOS "app does not open" not reproduced in deterministic simulator build/test path; high-risk touchpoints remain `ios/PulsePlate/Views/RootTabs.swift`, `ios/PulsePlate/Views/HomeView.swift`, `ios/PulsePlate/Views/ProgressView.swift`
  - Fixes applied by fact (merged remediation):
    - ✅ Web presentation fix merged: card/token class unification + CTA consistency updates in `frontend/src/pages/Home.tsx`, `frontend/src/pages/Plate.tsx`, `frontend/src/pages/Profile.tsx`
    - ✅ Step 3 implementation merged: [PR #820](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/820)
    - ✅ CI/checks and review-thread gate closed before merge
  - DoD:
    - ✅ Repro steps captured for both regressions (web visual + iOS open failure)
    - ✅ Root cause identified with evidence (`file:line` + failing test/log)
    - ✅ Web UX restored to canonical design-system quality on affected screens
    - ✅ iOS app opens and core navigation works (Root/App entry flow validated in deterministic simulator flow)
    - ✅ Deterministic regression tests added/updated (web + iOS where applicable)
    - ✅ CI checks for touched surfaces pass; no unresolved review threads


### P1

<a id="ledger-p1-worker-proxy-hardening"></a>
- [x] P1: Lock down Cloudflare worker proxy before any public deployment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #1082 (`feat/p1-worker-proxy-hardening-pr`)
  - Related follow-up: PR #1087 (`fix/p0-app-package-bootstrap-alignment`)
  - Related follow-up status: ✅ Merged (PR #1087, 2026-03-10)
  - Related follow-up SHA: `4e5ce31a08ec03393f70b59d3c93b811edb43633`
  - Status: ✅ Merged evidence (PR #1082 bounded the worker runtime to first-party `/api/*` proxy use only; PR #1087 then re-aligned the `app` package bootstrap on `main` so additive public runtime/OpenAPI surfaces stay visible through `import app`)
  - Area: edge / Cloudflare / security
  - Finding Type: proxy abuse prevention
  - Reason: `worker.js` previously forwarded arbitrary paths with wildcard CORS and passed through `Authorization`. That edge gap is now closed on `main` by PR #1082: the worker remains supported, but is hardened into a bounded first-party API proxy with `/api/*` allowlisting, `GET/POST/OPTIONS` method scope, explicit `TARGET_BASE`, trusted origins via `WORKER_ALLOWED_ORIGINS`, bounded header forwarding, stripping/ignoring spoofable client-IP headers, and no wildcard CORS. This ledger item is therefore closed as merged evidence rather than carried as an active runtime lane.
  - Links:
    - `worker.js`
    - `docs/security/SECURITY_POSTURE.md`
    - `docs/deploy/PRODUCTION.md`
    - `tests/test_worker_proxy_contract.py`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1087`
    - `docs/review/PR_1087_FIXED_MAPPING.md`
  - DoD:
    - Worker path scope is allowlisted to `/api/*`
    - Worker method scope is allowlisted to `GET`, `POST`, and `OPTIONS`, with tests proving other verbs are rejected
    - Worker proxy tests prove `redirect: "manual"` remains enforced for upstream fetches
    - Wildcard CORS and header pass-through are removed or bounded to trusted origins
    - Authorization forwarding policy is documented and tested, and spoofable client-IP headers are stripped or ignored fail-closed
    - Deployment docs state that worker runtime is supported only as a bounded first-party proxy

<a id="ledger-p1-fitchef-phase1-wrapper"></a>
- [x] P1: FitChef Phase 1 wrapper
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-1055
  - Status: ✅ Merged (PR-1055, 2026-03-09)
  - Area: orchestration / backend runtime / coaching insight
  - Finding Type: execution anchor
  - Locations:
    - `app/services/fitchef_runtime.py`
    - `app/schemas/fitchef.py`
    - `app/routers/cbt_insight.py`
  - Reason: The approved FitChef rollout order keeps `cbt_insight` as the first surface, but Phase 1 still needs one internal orchestration source of truth before weekly-plan and shopping-list bindings can reuse it.
  - Links:
    - `docs/orchestration/FITCHEF_SANDBOX_INTEGRATION_PLAN.md`
    - `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`
    - `docs/review/PR_1013_FIXED_MAPPING.md`
    - `docs/review/PR_1042_FIXED_MAPPING.md`
    - `docs/review/PR_1055_FIXED_MAPPING.md`
  - DoD:
    - Internal `fitchef-agent` wrapper exists under backend runtime with typed internal task envelope only
    - Existing `cbt_insight` public route delegates through the wrapper for `task_type=coach_insight`
    - Current request/response contracts remain unchanged for clients
    - Policy, quota, audit, RAG, and timeout ordering remain unchanged and regression-tested
  - Blockers: None

<a id="ledger-p1-fitchef-weekly-plan-binding"></a>
- [x] P1: FitChef weekly-plan task binding
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-1057
  - Status: ✅ Merged (PR-1057, 2026-03-09)
  - Area: orchestration / backend runtime / weekly planning
  - Finding Type: execution anchor
  - Locations:
    - `app/services/fitchef_runtime.py`
    - `app/schemas/vip.py`
    - `app/routers/vip.py`
    - `core/menu_engine.py`
  - Reason: After the internal FitChef wrapper lands, weekly-plan generation is the second approved Phase 1 task type and should reuse the same orchestration runtime instead of keeping planner orchestration embedded in the route layer.
  - Links:
    - `docs/orchestration/FITCHEF_SANDBOX_INTEGRATION_PLAN.md`
    - `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`
    - `docs/review/PR_1042_FIXED_MAPPING.md`
    - `docs/review/PR_1057_FIXED_MAPPING.md`
  - DoD:
    - FitChef runtime supports `task_type=weekly_plan`
    - Existing weekly-plan VIP route delegates through the wrapper and stays thin
    - Current `WeeklyPlanRequest` and `WeeklyPlanResponse` contracts remain unchanged
    - VIP gate and planner behavior remain deterministic and regression-tested
  - Blockers: Depends on [P1: FitChef Phase 1 wrapper](#ledger-p1-fitchef-phase1-wrapper)

<a id="ledger-p1-fitchef-shopping-list-follow-up-binding"></a>
- [x] P1: FitChef shopping-list follow-up binding
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-1058
  - Status: ✅ Merged (PR-1058, 2026-03-09)
  - Area: orchestration / backend runtime / shopping list
  - Finding Type: execution anchor
  - Locations:
    - `app/services/fitchef_runtime.py`
    - `app/routers/shopping_list_pro.py`
    - `app/schemas/shopping_list.py`
    - `app/core/shopping_list/generator.py`
  - Reason: The third approved Phase 1 task type is shopping-list follow-up, and the canonical integration target is `shopping_list_pro.py`, not the echo-style shoplist path under `vip.py`.
  - Links:
    - `docs/orchestration/FITCHEF_SANDBOX_INTEGRATION_PLAN.md`
    - `docs/orchestration/FITCHEF_SANDBOX_PHASE2_CONTRACT.md`
    - `docs/review/PR_1042_FIXED_MAPPING.md`
    - `docs/review/PR_1058_FIXED_MAPPING.md`
  - DoD:
    - FitChef runtime supports `task_type=shopping_followup`
    - Canonical shopping-list route delegates through the wrapper and preserves `ShoppingListRequest -> ShoppingListDTO`
    - XOR validation, unsupported-preferences handling, and tier-gate behavior remain unchanged and regression-tested
    - Legacy echo-style shoplist handling under `app/routers/vip.py` stays out of scope for this Phase 1 binding unless a follow-up PR explicitly promotes it
  - Blockers: Depends on [P1: FitChef Phase 1 wrapper](#ledger-p1-fitchef-phase1-wrapper)

<a id="ledger-p1-users-surface-hardening"></a>
- [x] P1: Public users CRUD surface must be authenticated or explicitly retired
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-TBD-USERS-SURFACE-HARDENING -> PR #1038 (`fix/security-users-surface-hardening`)
  - Status: ✅ Merged (PR #1038, 2026-03-08)
  - Area: backend / auth / data protection
  - Finding Type: access-control gap
  - Reason: Docs-only closure after PR #1038. Repo truth is now explicit: `app/routers/users.py` retained internal app-level protection while PR #1038 hid `/api/v1/users*` from the canonical public OpenAPI/schema surface and added deny-path regression coverage for unauthenticated access.
  - Links:
    - `app/routers/users.py`
    - `app/main.py`
    - `tests/test_users_api.py`
    - `tests/test_users_router.py`
    - `docs/security/SECURITY_POSTURE.md`
    - `docs/review/PR_1038_FIXED_MAPPING.md`
  - DoD:
    - Route policy is decided explicitly: protect with admin/API-key dependency, move behind internal-only surface, or remove if unused
    - OpenAPI and tests reflect the chosen access contract
    - Destructive operations require authenticated/authorized access
    - Docs-only closure keeps ledger state aligned with merged repo truth

- [x] P1: `simple_rag` shared index thread-safety hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (runtime reliability)
  - Target PR: PR #1010
  - Status: Done (merged in PR #1010)
  - Reason: Thread-safe initialization/refresh semantics and regression coverage were implemented and merged with the Wave 4 runtime closure.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md`
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `core/rag/simple_rag.py`
    - `tests/test_rag_simple.py`
    - `tests/test_insight_rag_response_fields.py`
  - DoD:
    - Deterministic thread-safe index initialization strategy is implemented (no double-init races)
    - Concurrency tests cover parallel read/init behavior
    - No regression in insight response contract or latency envelope


- [x] P1: RAG contract implementation (sources[], confidence, budget constants)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI / RAG)
  - Target PR: PR #935
  - Status: ✅ Merged (PR #935, 2026-02-27)
  - Reason (EN): Implement response schema and internal RAGContext/RAGChunk per `docs/contracts/RAG_CONTRACT.md`; add `sources[]`, `confidence`, `rag_used`, `hops`, `latency_ms` to Insight response; add `core/rag/contracts.py` and `rag_constants.py`.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md`
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `legacy_app.py` (InsightResponse, insight_v1/insight)
  - DoD:
    - InsightResponse (or extended schema) includes sources, confidence, rag_used, hops, latency_ms
    - RAGChunk/RAGContext dataclasses in core/rag; constants in core/rag
    - Deterministic tests for new response fields; `make verify` passes


- [x] P1: RAG feedback storage (prerequisite for recursive learning)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI / RAG / DB)
  - Target PR: PR #937 (merged)
  - Status: ✅ Merged (PR #937, 2026-02-28)
  - Reason (EN): Recursive learning and adaptive personalization in BACKLOG require persistent feedback. Add `rag_feedback` table (and `user_knowledge` for VIP); application-layer RLS; migration.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md` (Feedback Schema)
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md` (sect. 5.2, 6.2)
    - `docs/db/rag_feedback_schema.md` (schema documentation)
  - DoD:
    - Migration for rag_feedback and user_knowledge tables
    - PII redaction via `core/pii_redaction.py` before storage
    - Application-layer security (user_id filtering); DB RLS deferred to project-wide PR
    - docs/db schema doc created
    - `make verify` passes


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


- [x] P1: Extract import-safe ORM model helper for OpenAPI path (dedupe lazy-import pattern)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintainability / import hygiene)
  - Target PR: PR #746 (merged `5ccf83f5`)
  - Status: ✅ Completed (PR #746)
  - Resolution: PR-746 extracted `app/openapi/orm_imports.py` with `get_nutrition_event_model()`,
    `_lazy_import_attr()` helper, and `_ORM_IMPORT_CACHE` (idempotent, lock-free).
    `nutrition_log.py` now uses a single `_nutrition_event_model()` wrapper that delegates to
    the centralized helper. Guard test `test_openapi_import_safe_orm_guard.py` validates
    import-safety and caching behavior.
  - Evidence:
    - `app/openapi/orm_imports.py:43-60` — `get_nutrition_event_model()` with lazy cache
    - `app/routers/nutrition_log.py:19` — `from app.openapi.orm_imports import get_nutrition_event_model`
    - `app/routers/nutrition_log.py:41-47` — `_nutrition_event_model()` typed wrapper
    - `tests/test_openapi_import_safe_orm_guard.py` — guard test for import-safety + cache
  - DoD:
    - [x] Add a single helper (import-safe) for model retrieval used by `nutrition_log` (and any similar routers)
    - [x] Unit test that validates helper is import-safe (no import-time `app.models.*` in OpenAPI path)
    - [x] No runtime behavior change (pure refactor)


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


- [x] P1: Execution Wave 2 — Search modernization (Meili/TypeSense) + API compatibility
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #891, PR #893, PR #898, PR #900
  - Status: ✅ Merged (W2-A/W2-B/W2-C + barcode hit contract in PR #900, 2026-02-25)
  - Area: backend / search / API
  - Finding Type: performance and UX improvement
  - Reason: Local-first indexed search is required for predictable low latency and better discoverability while preserving client compatibility.
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/audit/PR_898_FOOD_DB_W2_C_LATENCY_BENCHMARK.md`
    - `scripts/benchmarks/food_api_latency_benchmark.py`
    - `app/routers/foods.py`
    - `app/services/food_store.py`
    - `tests/test_food_store_service.py`
    - `tests/test_foods_router_additional.py`
  - DoD:
    - Existing `/api/v1/foods` contracts remain stable
    - New search backend is integrated behind compatibility layer
    - New endpoints contract for barcode/search filters is documented and tested
    - Target local-first search latency budget (<50ms p50) is measured and reported


- [x] P1: Execution Wave 3 — Restaurant menus + controlled user submissions
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #895 (+ follow-up PR #901, `feat/food-db-w3b-menustat-provenance-closure`)
  - Status: ✅ Merged (W3-A in PR #895 + W3-B closure in PR #901, 2026-02-25)
  - Area: backend / data model / partner enablement
  - Finding Type: product coverage expansion
  - Reason: Product/restaurant database coverage and controlled data intake are required to reduce manual entry and support partner menu flows.
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/design/RESTAURANT_INTEGRATION_SPEC.md`
    - `docs/roadmap/BACKLOG_LEDGER.md` (P2 Vision: Restaurant/chef integration)
    - `app/routers/restaurants.py`
    - `app/services/restaurant_store.py`
    - `app/schemas/restaurants.py`
  - DoD:
    - MenuStat baseline ingestion is operational
    - Restaurant menu schema and endpoints are documented
    - Moderated user submission workflow is implemented (`pending/approved/rejected`)
    - Source audit trail persists provenance for imported and moderated records


- [x] P1: Execution Wave 3-C — operational MenuStat bootstrap importer
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #904 (`feat/food-db-w3d-menustat-importer`)
  - Status: ✅ Merged (PR #904, 2026-02-25)
  - Area: backend / ingestion operations / restaurant coverage
  - Finding Type: operational gap closure
  - Reason: Restaurant endpoints and storage contracts exist, but local environments need a deterministic, repeatable import command to seed menu data from MenuStat-style snapshots without manual DB editing.
  - Links:
    - `scripts/import_restaurant_menu.py`
    - `data/restaurant_menu_sample.csv`
    - `tests/test_import_restaurant_menu_script.py`
    - `app/services/restaurant_store.py`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
  - DoD:
    - CLI importer loads MenuStat-style CSV with alias mapping into canonical restaurant tables
    - Importer supports explicit snapshot date and source name for provenance
    - Deterministic sample dataset exists for local bootstrap and tests
    - End-to-end test verifies import command populates searchable chain/menu records


- [x] P1: Execution Wave 3-E — approved submission promotion to canonical restaurant menu
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #908 (`feat/food-db-wave3e-submission-promotion`)
  - Status: ✅ Merged (PR #908, 2026-02-25)
  - Area: backend / moderation workflow / restaurant coverage
  - Finding Type: correctness gap closure
  - Reason: Moderated submissions reached `approved`, but approved restaurant-menu submissions were not deterministically promoted into canonical `restaurant_menu_items`, creating a product/database gap for local-first lookup.
  - Links:
    - `app/services/restaurant_store.py`
    - `tests/test_restaurant_store_service.py`
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
  - DoD:
    - `approved` submissions with `entity_type=restaurant_menu` are promoted into canonical menu rows in the same transaction scope
    - Re-approving already approved submissions is idempotent (no duplicate promoted menu rows)
    - `rejected` submissions do not create menu rows
    - Promotion failures remain fail-closed (no partial moderation/audit state persisted)
    - Deterministic tests cover approved/rejected/idempotency/rollback behavior


- [x] P1: Feature TODO from runtime SKIPPED suites (optional modules manifest)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #873 (merged `ab0b7cc1`)
  - Status: ✅ Completed (PR #873)
  - Resolution: PR-873 delivered `tests/feature_manifest.py` with `FEATURE_TODO_KEYS` frozenset,
    `require_feature()` and `require_feature_or_raise()` helpers, and migrated 22 ad-hoc
    `pytest.skip()` calls to standardized `feature_disabled:<key>` format across 3 test files.
    Two modules (`shoplist_helpers`, `aliases_module`) were enabled and removed from gated keys.
    Remaining 16 gated keys are tracked in the "Unimplemented feature keys backlog" item below.
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
    - `planner_engines`: ✅ Enabled (see entry below); renamed residual key to `planner_engines_advanced`
    - `planner_engines_advanced`: ✅ Enabled (see entry below)
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
    - [x] `tests/feature_manifest.py` exists with SoT feature keys and env opt-in
      (`PULSEPLATE_FEATURES=all` or CSV list).
    - [x] High-noise suites use shared helper instead of custom ad-hoc skip strings.
    - [x] Runtime `pytest -q -rs` output shows standardized skip reasons with feature keys.
    - [x] Feature keys in tests and ledger remain one-to-one mapped.
  - Evidence:
    - `tests/feature_manifest.py` — `FEATURE_TODO_KEYS` frozenset + `require_feature()` + `require_feature_or_raise()`
    - `tests/test_simple_coverage_fixed.py` — 8 calls migrated to `require_feature_or_raise()`
    - `tests/test_specific_core_modules.py` — 2 calls migrated; `aliases_module` gates removed
    - `tests/test_plate_targets_micro_coverage.py` — 11 calls migrated (`plate_day_micros` key)


- [x] P1: Food barcode hit contract normalization for canonical FoodItem response
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #900 (`fix/food-barcode-hit-contract`)
  - Status: ✅ Merged (PR #900, 2026-02-25)
  - Area: backend / API contract / data normalization
  - Finding Type: correctness and reliability gap
  - Reason: `GET /api/v1/foods/barcode/{barcode}` can fail on hit-path serialization when persisted `flags` payload is string-encoded instead of a list, causing non-deterministic hit-path behavior in benchmark and runtime.
  - Links:
    - `app/routers/foods.py`
    - `app/schemas/food.py`
    - `docs/audit/PR_898_FOOD_DB_W2_C_LATENCY_BENCHMARK.md`
  - DoD:
    - Barcode hit path returns `200` with valid `FoodItem` serialization on canonical seeded DB
    - `flags` storage/parse contract is normalized and backward-compatible
    - Deterministic tests cover hit/miss/malformed barcode paths


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


- [x] P1: Unimplemented feature keys backlog (SoT = tests/feature_manifest.py)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR-748
  - Status: ✅ Complete (22 total enabled, 0 remaining)
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
    - `shoplist_helpers` -> ✅ Merged (PR-764, 2026-02-16, `48c87f39`); gate removed in PR-748
    - `aliases_module` -> ✅ Enabled (PR-748); core/aliases.py fully implemented
    - `update_manager` -> ✅ Enabled (PR-761, `0aa3c51b`); Path wrapper .path exposed in core/food_apis/update_manager.py; gates removed from 4 test locations (test_database_apis_coverage.py, test_final_coverage_97_boost.py, test_update_manager_fixed.py); key removed from FEATURE_TODO_KEYS
    - `region_catalog` -> ✅ Enabled (PR-762, `abed9a48`); stale feature gate removed from test_direct_core_functions.py; 1 test location cleaned; key removed from FEATURE_TODO_KEYS
    - `targets_fixture_data` -> ✅ Enabled (PR-877); gates removed from 3 test files (test_targets_coverage_97.py, test_core_coverage_97_final.py, test_simple_coverage_fixed.py)
    - `i18n_advanced` -> ✅ Enabled (PR-877); thin facades added to core/i18n.py (TranslationManager + 8 functions); gates removed from 4 test files
    - `rag` -> ✅ Enabled (PR-877); thin facades added to core/rag/simple_rag.py (RAGEngine/SimpleRAG + 6 functions); gates removed from 4 test files
    - `core_db` -> ✅ Enabled (PR-879); thin facades added to core/db.py (get_db, create_tables, init_database, get_unified_food_db); gates removed from 9 test files
    - `food_apis` -> ✅ Enabled (PR-879); thin facades added to core/food_apis/ (base.py, usda.py, openfoodfacts.py, scheduler.py); gates removed from 9 test files
    - `unified_db` -> ✅ Enabled (PR-879); thin facades added to core/food_apis/unified_db.py (UnifiedFoodDB, FoodSource, merge_food_sources, update_unified_db); gates removed from 9 test files
    - `utils_pack` -> ✅ Enabled (PR-880); thin facades added to core/utils.py (safe_float, safe_int, slugify, format_number, generate_id, sanitize_html, validate_email) and core/time_utils.py (parse_datetime, format_datetime, get_timezone_offset, is_valid_date, format_time, human_delta); gates removed from 4 test files
    - `weekly_plan_helpers` -> ✅ Enabled (PR-881); thin facades added to core/weekly_plan.py (calculate_weekly_nutrition, optimize_weekly_variety, validate_weekly_plan); gates removed from test_remaining_modules.py; 31 coverage tests added
    - `food_apis_error_injection` -> ✅ Enabled (PR-885, 2026-02-24, `2b724190`); fixed 5 test mocks in test_food_apis_coverage_errors.py (correct mock targets, UnifiedFoodItem constructors, errors list assertions); fixed _Sched2 global state leak in test_food_apis_push95.py; added USDA search error handling in unified_db.py; key removed from FEATURE_TODO_KEYS
    - `premium_week_router_mocking` -> ✅ Enabled (PR-888, 2026-02-24, `96c72345`); implemented 2 gated tests (503 make_weekly_menu unavailable, 500 exception handling); fixed PEP 562 `__getattr__` mock residual in `app.__dict__`; key removed from FEATURE_TODO_KEYS
    - `legacy_bmi_removed` -> ✅ Enabled (PR-891, 2026-02-24); implemented canonical PRO BMI functions in `core/bmi/engine.py`: `estimate_level()` (fitness experience level), `interpret_group()` (group interpretation with notes), `build_premium_plan()` (premium plan with nutrition/activity tips), `PremiumPlanResult` dataclass; added i18n keys for action/activity tips (ru/en/es); updated `bmi_core.py` shims to delegate; comprehensive tests added in `test_app_coverage_unit_combined.py`, `test_level_es.py`, `test_bmi_core_shim_diffcover.py`; key removed from FEATURE_TODO_KEYS
    - `nutrient_recommendations` -> ✅ Enabled (PR-894, 2026-02-25); added `get_nutrient_recommendations()` facade in `core/recommendations.py` wrapping `build_nutrition_targets()` with simplified API (age/gender/weight/height/activity_level); activity level mapping (low/moderate/high/very_high); 2 gated tests ungated + 1 edge-case test added in `test_final_coverage_97_boost.py`; key removed from FEATURE_TODO_KEYS
    - `nutrition_api_pr2_pro_endpoints` -> ✅ Enabled (PR-903, 2026-02-25, `aeb1b49a`); added 3 PRO endpoints under `/api/v1/pro/nutrition/`: `POST /deficiency-recommendations` (food-based recs for deficient nutrients, en/ru/es), `POST /micronutrient-targets` (extended micro targets with min/target/max per WHO/EFSA/DRI), `POST /safety-check` (validates nutrition targets against safety bounds); extended `ProfileInput` with optional fields (`goal`, `diet_flags`, `life_stage`, `deficit_pct`, `surplus_pct`, `bodyfat`); added Spanish (es) language support in food sources; 38 new tests (77 total) covering tier guards, contract assertions, validation errors; OpenAPI + TypeScript types regenerated
    - `planner_engines` -> ✅ Enabled (2026-02-25); added ~25 thin facade functions across 4 core modules: `core/targets.py` (calculate_bmr, calculate_tdee, validate_user_data + 4 stubs), `core/auto_repair.py` (analyze_deficiencies, get_repair_suggestions, calculate_repair_priority + 2 stubs), `core/menu_engine.py` (calculate_nutrition_totals, generate_shopping_list, optimize_meals, validate_meal_plan, suggest_meal_improvements), `core/plate.py` (create_nutrition_plate, analyze_plate_balance, get_plate_recommendations, calculate_plate_score, visualize_plate_data); rewrote `test_direct_core_functions.py` to remove feature gates (10 tests import directly); added 61 coverage tests in `test_planner_engines_facades.py`; renamed residual advanced key to `planner_engines_advanced`; key removed from FEATURE_TODO_KEYS
    - `planner_engines_advanced` -> ✅ Enabled (2026-02-25); added 2 new modules: `core/nutrition_analysis.py` (analyze_nutrition, calculate_nutrition_score, get_nutrition_recommendations, validate_nutrition_data), `core/config.py` (load_config, get_config_value, set_config_value, validate_config); removed feature gates from 6 tests in `test_final_core_coverage.py`; fixed test signatures to match implementations; added 26 coverage tests in `test_planner_engines_advanced_facades.py`; key removed from FEATURE_TODO_KEYS
    - `plate_day_micros` -> ✅ Enabled (PR-912, 2026-02-26); day_micros aggregation from meals already implemented in `legacy_app.py:_aggregate_day_micronutrients()` with fallback mechanism for missing recipe ingredients; removed 10 feature gates from `test_plate_targets_micro_coverage.py`; key removed from FEATURE_TODO_KEYS
    - `exports_recipes_products` -> ✅ Enabled (PR-TBD, 2026-02-26); added 24 thin facade functions across 5 core modules: `core/exports.py` (export_meal_plan, export_nutrition_report, generate_pdf_report, export_to_csv, export_shopping_list), `core/recipe_synth.py` (generate_recipe, synthesize_meal, create_recipe_variations, optimize_recipe_nutrition, suggest_substitutions), `core/product_finder.py` (find_products, search_by_nutrition, filter_by_criteria, get_product_info, compare_products), `core/product_varieties.py` (get_varieties, find_alternatives, group_by_category, suggest_similar, analyze_variety_nutrition), `core/exports_simple.py` (simple_csv_export, simple_json_export, simple_text_export, quick_meal_export); removed 5 feature gates from `test_zero_coverage_modules.py`; key removed from FEATURE_TODO_KEYS
    - `sports_disclaimers_lifestage` -> ✅ Enabled (PR-916, 2026-02-26); added 13 thin facade functions across 3 core modules: `core/sports_nutrition.py` (calculate_sports_targets, get_athlete_nutrition, adjust_for_training, hydration_needs), `core/lifestage_nutrition.py` (get_lifestage_requirements, adjust_for_age, pregnancy_nutrition, elderly_nutrition, child_nutrition), `core/disclaimers.py` (get_disclaimer, get_medical_disclaimer, get_nutrition_disclaimer, get_liability_disclaimer); removed 3 feature gates from `test_zero_coverage_modules.py`; key removed from FEATURE_TODO_KEYS; **last feature key enabled - FEATURE_TODO_KEYS now empty**
  - Keys still gated (module exists but tested API surface incomplete):
    - (none - all feature keys enabled)
  - Ad-hoc skip migration (PR-748):
    - 22 ad-hoc pytest.skip() calls migrated to require_feature() in 3 test files
    - 2 new feature keys added: `plate_day_micros`, `aliases_module` (then enabled)


- [x] P1: Wave 2 contract governance v2 + CI throughput program
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #850 (docs/wave2-contract-governance-ci-throughput)
  - Status: ✅ Completed (PR #850, 2026-02-21, merge SHA `411c3159`)
  - Area: backend / frontend / ios / devex
  - Finding Type: maintainability / delivery speed
  - Locations:
    - `docs/contracts/CONTRACT_GOVERNANCE_V2_CHECKLIST.md`
    - `docs/policy/CI_THROUGHPUT_AND_FLAKE_BUDGET.md`
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/roadmap/PROGRAM_6M_BALANCED_2026H1.md`
  - Reason: reduce contract drift and CI critical-path latency while preserving quality gates.
  - Links:
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/roadmap/PROGRAM_6M_BALANCED_2026H1.md`
    - `docs/contracts/CONTRACT_GOVERNANCE_V2_CHECKLIST.md`
    - `docs/policy/CI_THROUGHPUT_AND_FLAKE_BUDGET.md`
  - DoD:
    - [x] Contract governance checklist with OpenAPI diff risk labels documented
    - [x] CI throughput baseline and target defined with flake budget owner
    - [x] Follow-up implementation PRs linked (deferred to Wave 2 CI enforcement phase)


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


- [x] P1: Orchestration — document worktree isolation policy (agent worktree immutable to humans)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #963
  - Status: merged 2026-03-04 (79024d70)
  - Priority: P1
  - Area: dev-process / orchestration
  - Finding Type: operational policy
  - Reason: Agent works in its own worktree; a human edits the same files → merge conflicts → orchestration chaos. No explicit rule "human cannot edit agent worktree." Integration flow exists (PR promotion) but operational law is missing.
  - Links:
    - `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Policy section added to runbook (worktree states: active/abandoned/merged; allowed human intervention via new branch)
    - Short hard-rule excerpt in root `AGENTS.md` (do not edit inside worktrees/; integration only via PR)
    - Example "human intervention via new branch" documented


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


- [x] P1: PR #825 bot-comments + CI green closure checklist (matrix)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #825 (`chore/6m-balanced-program-agent-control-plane-pr`)
  - Status: ✅ Merged (PR #825, 2026-02-20)
  - Area: docs / frontend / ci / review-ops
  - Finding Type: review remediation / quality-gate closure
  - Locations:
    - `frontend/src/lib/telemetry/eventRegistry.ts`
    - `frontend/src/lib/__tests__/telemetry.test.ts`
    - `docs/architecture/ADR-003-agent-control-plane-mvp.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
  - Reason: close all bot actionables and reach zero unresolved review threads with full CI green.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/825`
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
  - Checklist (Matrix):
    - [x] Sourcery actionables addressed with commit mapping in PR body
    - [x] CodeRabbit actionables addressed with file-level fixes and thread replies
    - [x] PR Body Phase2 gates passed after checklist/mapping update
    - [x] Docs Phase1 gates passed with evidence anchors in audit/security docs
    - [x] Required CI checks are green (`gh pr checks 825`)
    - [x] Unresolved review threads count is zero
  - DoD:
    - Sourcery actionables addressed with commit mapping in PR body
    - CodeRabbit actionables addressed with file-level fixes and thread replies
    - PR Body Phase2 gates pass after checklist/mapping update
    - Docs Phase1 gates pass with evidence anchors in audit/security docs
    - Required CI checks are green (`gh pr checks 825`)
    - Unresolved review threads count is zero


- [x] P1: RAG implementation audit — baseline (docs-only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (AI / RAG / docs)
  - Target PR: PR #928 (merged)
  - Status: Done
  - Area: docs / audit
  - Reason (EN): Establish evidence-based baseline for current RAG (insight-only, Jaccard), backlog gaps (sources[], confidence, multi-hop, feedback storage, agent RAG), and prioritized follow-up. No runtime changes in this PR.
  - Links:
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `docs/contracts/RAG_CONTRACT.md`
    - `core/rag/simple_rag.py`, `legacy_app.py` (insight RAG paths)
  - DoD:
    - Audit and RAG contract docs merged in docs-only PR
    - BACKLOG_LEDGER updated with follow-up items below
    - Branch follows PR scope guard (docs only)


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


- [x] P1: Home/Plate/Progress live indicator A/B variant + telemetry enrichment
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #803 (`feat/hpp-live-indicator-ab-variant`)
  - Status: ✅ Merged (PR #803, 2026-02-19)
  - Merge SHA: d1e2fa1668156b8621557daee235844bd4703ced
  - Area: frontend / product-metrics / experimentation
  - Finding Type: user-visible experiment package
  - Reason: Extend the shipped live-indicator package with deterministic A/B variant
    assignment (`compact`/`emphasized`) and enriched telemetry needed to measure
    variant-level CTA and paywall-open behavior without expanding backend scope.
  - Experiment Window:
    - Start: 2026-02-20
    - End: 2026-03-05
    - Guardrails: websocket connect success >= 99%, no JS runtime error increase,
      no layout-shift regressions on Home/Plate/Progress
  - Metric Tracking:
    - Primary KPI: `hpp_live_cta_click_rate_by_variant`
    - Secondary KPI: `paywall_open_from_live_by_variant`
    - Supporting Signals:
      - `hpp_live_indicator_impression`
      - `hpp_cta_impression`
      - `hpp_cta_click`
      - `hpp_paywall_open_from_live`
  - Links:
    - PR #803
    - `frontend/src/features/progress/useHppLiveIndicator.ts`
    - `frontend/src/features/progress/LiveProgressIndicator.tsx`
    - `frontend/src/lib/hppTelemetry.ts`
    - `frontend/src/features/progress/__tests__/useHppLiveIndicator.test.ts`
    - `frontend/src/features/progress/__tests__/LiveProgressIndicator.test.tsx`
    - `frontend/src/features/progress/__tests__/hppTelemetry.test.ts`
  - DoD:
    - Deterministic variant assignment implemented (`userId hash % 2`, fallback `compact`)
    - UI variant rendering validated for `compact` and `emphasized`
    - Telemetry payload includes `placement` and `variant` across impression/click events
    - Paywall-open event from live indicator is emitted with stable payload shape
    - Deterministic tests and snapshots cover variant logic and telemetry shape


- [x] P1: Telemetry API normalization (`trackVipEvent` -> generic `trackEvent`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #863 (feat/telemetry-api-normalization)
  - Status: ✅ Completed (PR #863, 2026-02-22, merge SHA `f5b7d299`)
  - Area: frontend / analytics / architecture
  - Finding Type: naming/abstraction hygiene
  - Locations:
    - `frontend/src/lib/telemetry.ts`
    - `frontend/src/lib/telemetry/eventRegistry.ts`
  - Reason: growth events currently use `trackVipEvent`; rename to a generic API surface and keep compatibility wrapper to avoid VIP-specific naming leakage in broader telemetry families.
  - Links:
    - `docs/roadmap/WAVE_2_3_EXECUTION_PACK.md`
    - `docs/analytics/ANALYTICS_INDEX.md`
    - [PR #863](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/863)
  - DoD:
    - [x] Generic telemetry entrypoint (`trackEvent`) introduced with deterministic validation path
    - [x] Backward-compatible wrapper for existing `trackVipEvent` callers (deprecation marker only)
    - [x] Enum constraints documented for shared growth fields where runtime validation is required
    - [x] Tests updated for both legacy and new entrypoints
    - [x] `make verify` and required CI checks pass


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


- [x] Cross-platform Design System: define tokens + UI primitives (Web + iOS)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design consistency / velocity)
  - Target PR: PR #870 (`feat/cross-platform-design-system-tokens-primitives`)
  - Status: ✅ Merged (PR #870, 2026-02-22)
  - Merge SHA: 3f5481d8
  - Area: ios / frontend / design-system
  - Reason: Web has initial brand colors in `frontend/src/styles/tokens.ts`, but iOS lacks a centralized token mirror
    (colors/spacing/typography/motion). Without a minimal design system, UI work drifts, is slower to delegate, and is
    harder to review consistently across platforms.
  - Links:
    - [PR #870](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/870)
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md` (design canon + agent roster + checklists)
    - `frontend/src/styles/tokens.ts` (Web token SoT)
    - `ios/PulsePlate/DesignSystem/DesignTokens.swift` (iOS token SoT)
    - `ios/PulsePlate/DesignSystem/PPButton.swift`
    - `ios/PulsePlate/DesignSystem/PPCard.swift`
    - `ios/PulsePlate/DesignSystem/PPInput.swift`
    - `ios/PulsePlate/DesignSystem/PPTypography.swift`
    - `frontend/AGENTS.md`, `ios/AGENTS.md` (thin-client + CI invariants)
  - Review remediations:
    - Cubic P2: sync `textValue` when bound value changes externally (commit `90f8c181`)
    - CodeRabbit Major: use `NumberFormatter` for locale-aware parsing (commit `0a720f78`)
    - CodeRabbit Nitpick: reduce duplicated card styling via `.ppCardStyle()` (commit `0a720f78`)
  - DoD:
    - ✅ Token canon defined (colors + spacing + typography + motion + elevation) with explicit names
    - ✅ iOS has a single source for tokens (`DesignTokens.swift`, SwiftUI-friendly) and uses it in new components
    - ✅ Web components consume tokens (no hardcoded brand colors/spacing in new primitives)
    - ✅ Minimal primitives exist on both platforms: Button, Card, Input, Typography
    - ✅ Locale-aware numeric input via `NumberFormatter` (iOS PPInput)
    - ✅ All bot review comments addressed and mapped in PR body
    - ✅ CI checks green; merge readiness gate passed


- [x] P1: Design token pipeline foundation (`/tokens` authoring to generated runtime mirrors)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-system governance / drift prevention)
  - Target PR: PR #1047 (`feat(design): add token pipeline foundation`)
  - Status: ✅ Merged
  - Merge SHA: f272503c
  - Area: frontend / ios / design-system / governance
  - Finding Type: tooling foundation + parity enforcement
  - Reason: Earlier token work established web SoT, raw-hex guards, Storybook review, and an iOS token facade, but runtime mirrors still depended on manual sync. PR #1047 adds a governed `/tokens` authoring source, Style Dictionary generation into the existing web/iOS runtime contracts, parity guards, CI wiring, and review-governed documentation without breaking current consumers.
  - Links:
    - [PR #1047](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1047)
    - `tokens/`
    - `docs/design/TOKENS_SOT.md`
    - `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
    - `frontend/src/styles/tokens.css`
    - `frontend/src/styles/tokens.ts`
    - `ios/PulsePlate/DesignSystem/DesignTokens.generated.swift`
    - `ios/PulsePlate/DesignSystem/DesignTokens.swift`
    - `tests/test_design_token_parity.py`
    - `docs/review/PR_1047_FIXED_MAPPING.md`
  - DoD:
    - ✅ `/tokens` is the governed authoring source for stable, already-live token values
    - ✅ Existing runtime contracts remain intact for `tokens.css`, `tokens.ts`, and `PPDesignTokens`
    - ✅ Generated iOS mirror exists as `DesignTokens.generated.swift` behind the stable public facade
    - ✅ Parity and determinism checks cover `/tokens -> web/iOS mirrors`
    - ✅ CI token pipeline lane and merge-governance documentation are merged and review-mapped


- [x] P1: Weekly-plan VIP alias hygiene and schema visibility
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (API contract hygiene / OpenAPI surface discipline)
  - Target PR: PR #1061 (`refactor(weekly-plan): thin legacy VIP weekly alias`)
  - Status: ✅ Merged
  - Merge SHA: 174a7bdb
  - Area: backend / OpenAPI / legacy compatibility
  - Finding Type: legacy alias delegation + schema visibility cleanup
  - Reason: `/api/v1/premium/plan/week` was a VIP weekly-plan compatibility route living under the deprecated `/premium/*` namespace with its own legacy shaping path. PR #1061 reduced it to a thin compatibility alias over `/api/v1/vip/menu/weekly/plan`, kept runtime backward compatibility, hid the broken-name route from public OpenAPI, and added parity/normalization regressions for weekly-plan numeric fields.
  - Links:
    - [PR #1061](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061)
    - `legacy_app.py`
    - `tests/test_legacy_weekly_plan_alias_api.py`
    - `tests/test_app_openapi_coverage.py`
    - `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md`
    - `docs/contracts/OPENAPI_PATHS_AUDIT.md`
    - `docs/review/PR_1061_FIXED_MAPPING.md`
  - DoD:
    - ✅ `/api/v1/premium/plan/week` delegates to `/api/v1/vip/menu/weekly/plan` without retaining VIP business logic in the legacy shim
    - ✅ Runtime compatibility preserved for existing callers of the legacy VIP alias
    - ✅ Public OpenAPI no longer exposes `/api/v1/premium/plan/week`
    - ✅ Parity tests prove legacy alias responses match the canonical VIP weekly-plan route
    - ✅ Weekly-plan numeric normalization covers malformed, non-finite, and overflow-prone values with deterministic regressions


<a id="ledger-p1-weekly-plan-openapi-parity-wave"></a>
- [x] P1: Weekly-plan OpenAPI and web parity wave
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (OpenAPI reconciliation / frontend thin-client parity)
  - Target PR: PR #1068 (`docs(openapi): reconcile weekly-plan contract truth`), PR #1069 (`refactor(vip): thin premium weekly alias`), PR #1070 (`refactor(frontend): normalize weekly plan consumers`), PR #1075 (`fix(frontend): gate weekly plan initial load`)
  - Ledger closure PR: PR #1077 (`docs(ledger): record weekly-plan wave hotfix`)
  - Related follow-up PR: PR #1079 (`fix(ci): bound trivy image scan`)
  - Status: ✅ Merged (runtime wave and post-merge hotfix); closure synchronized in PR #1077 with Trivy workflow split traced through PR #1079
  - Merge SHAs:
    - PR #1068: `888dc69a`
    - PR #1069: `68fe8d57`
    - PR #1070: `eff51947`
    - PR #1075: `b57333be`
  - Area: backend / OpenAPI / frontend weekly-plan runtime
  - Finding Type: schema reconciliation + legacy alias cleanup + normalized web consumer parity
  - Reason:
    - The repo had already moved to the canonical PRO route `POST /api/v1/pro/meal/weekly` and shared backend DTO normalization, so the remaining work was reconciliation and finishing rather than route migration.
    - The wave locked `WeeklyMealPlanResponse` as the generated OpenAPI truth, kept `/api/v1/premium/plan/week-flexible` as a hidden runtime-compatible alias, and moved web weekly-plan consumers to one normalized UI view-model instead of ad-hoc raw payload assumptions.
    - A follow-up hotfix then closed the initial-render regression where `WeeklyPlanViewer` could briefly flash the empty summary before the first fetch transitioned into loading.
  - Links:
    - [PR #1068](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1068)
    - [PR #1069](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1069)
    - [PR #1070](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1070)
    - [PR #1075](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1075)
    - [PR #1077](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1077)
    - [PR #1079](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1079)
    - `app/schemas/weekly_plan.py`
    - `app/routers/pro.py`
    - `app/routers/premium_week.py`
    - `legacy_app.py`
    - `frontend/src/api/openapi.json`
    - `frontend/src/api/schema.ts`
    - `frontend/src/features/plan/WeeklyPlanViewer.tsx`
    - `frontend/src/features/plan/__tests__/WeeklyPlanViewer.test.tsx`
    - `frontend/src/hooks/useWhoTargetsWithWeeklyPlan.ts`
    - `docs/review/PR_1068_FIXED_MAPPING.md`
    - `docs/review/PR_1069_FIXED_MAPPING.md`
    - `docs/review/PR_1070_FIXED_MAPPING.md`
    - `docs/review/PR_1075_FIXED_MAPPING.md`
    - `docs/review/PR_1077_FIXED_MAPPING.md`
  - DoD:
    - ✅ `WeeklyMealPlanResponse` remains the single canonical weekly-plan response shape for backend normalization and generated OpenAPI artifacts
    - ✅ Public OpenAPI exposes `POST /api/v1/pro/meal/weekly` and keeps `POST /api/v1/premium/plan/week-flexible` hidden as a deprecated runtime alias
    - ✅ Legacy VIP alias cleanup stays thin and schema-hidden without reintroducing separate weekly-plan business logic
    - ✅ Web weekly-plan consumers render a normalized weekly-plan view-model instead of depending on raw response shape details, including initial-load gating that treats `data == null && err == null` as loading instead of flashing the empty summary
    - ✅ Regression coverage exists for malformed payload normalization, schema visibility, legacy alias parity, and normalized weekly-plan web consumption


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
    - iOS uses `APIClient` and calls canonical `GET /api/v1/pro/nutrition/daily` with `X-API-Key` sourced from the app's secure key provider
    - UX: explicit states for missing PRO key / missing profile / 422 validation errors
    - Tests:
      - unit test for building daily nutrition request query (deterministic)
      - `make ios-test` passes


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

- [x] core/db.py vs core/db/ collision resolved (TP2 amendment 2026-01-28)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #617 (amendment)
  - Reason: TP2 originally used `core/db/fallback.py` which caused `core.db` to resolve as package in CI. Resolved by moving fallback to `core/db_fallback.py` (flat module) and removing `core/db/` package; no guard exception needed.
  - DoD: Done. Fallback in `core/db_fallback.py`; AGENTS.md rule: never add `core/<name>/` when `core/<name>.py` exists.


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


- [x] Generalize dependency vulnerability guards beyond single-CVE floors (merged 2026-02-27)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #923
  - Status: ✅ Closed
  - Reason: Current guard test enforces a floor for one high-risk dependency (`cryptography`). Preventing future
    regressions at scale needs a deterministic allow/deny schema for multiple packages/CVEs.
  - Links:
    - `tests/test_dependency_security_guard.py`
    - `tests/fixtures/dependency_security_schema.json`
    - `docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md`
  - DoD:
    - [x] Introduce a centralized guard schema (`package -> min_safe_version` or denylist) for key dependencies
    - [x] Deterministic CI/pytest check validates all relevant requirement surfaces
    - [x] Developer docs explain how to update schema when new CVEs are triaged


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

- [x] P1 (maintenance): Type-hints carryover cleanup (tests)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (maintenance)
  - Target PR: PR #642
  - Status: ✅ Done (merged via PR #642)
  - Reason: Previously-agreed test typing/hygiene changes were missed in a prior PR and intentionally carried over to keep bots/review consistent. Non-functional change (tests only).
  - Notes: Missed in prior PR; carried over intentionally.
  - Links: PR #642; policy: AGENTS.md (carryover rule); related: PR #640/#641 (context)
  - DoD: Done. CI green; reviewers' sign-off; PR #642 merged; no new skips; only tests/docs changed


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


- [x] P1: Fact-check closure for stale critical claims in external roadmap snapshot (2026-03-05)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (program governance)
  - Target PR: PR #972, PR #973, PR #974
  - Status: ✅ Merged (all listed PRs merged on 2026-03-04)
  - Reason: External document snapshot contained stale “P0 missing” claims for controls that were already implemented in runtime. Ledger now anchors these as completed facts to prevent duplicate emergency scope.
  - Links:
    - `app/security/rate_limit.py` (rate limiting baseline)
    - `app/routers/realtime_ws.py` (WebSocket auth/policy-close baseline)
    - PR #972 (Philosophy validator core)
    - PR #973 (Recursive RAG W1 core)
    - PR #974 (orchestration telemetry/spec package)
  - DoD:
    - Stale claims are marked as implemented with repository evidence
    - Remaining open items track only fact-valid deltas (RAG technical debt + runtime governance follow-ups)


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


- [x] P1: Unify `TargetsIn` schemas (legacy_app ↔ `app.schemas.nutrition_targets`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (drift prevention)
  - Target PR: PR #633 (merged `29546992`, 2026-02-03)
  - Status: ✅ Merged (PR #633, 2026-02-03)
  - Resolution: PR-633 unified TargetsIn by making `legacy_app.TargetsIn` a thin alias to canonical
    `app.schemas.nutrition_targets.TargetsIn`. Guard test `test_legacy_targets_in_is_canonical_alias()`
    in `tests/test_targets_in_parity.py` prevents future drift.
  - Links:
    - PR #631 (remediation): full OpenAPI without import-time `app.models.*` along OpenAPI path
    - PR #633 (unification): thin alias + parity tests
  - Evidence:
    - `app/schemas/nutrition_targets.py:37-58` (canonical TargetsIn, import-safe)
    - `legacy_app.py:126-127` (`TargetsIn = CanonicalTargetsIn`, PR-633 alias)
    - `tests/test_targets_in_parity.py:28-32` (`assert legacy_app.TargetsIn is CanonicalTargetsIn`)
  - DoD:
    - ✅ One canonical schema (single source of truth) with a thin wrapper/alias where needed
    - ✅ Parity tests that prevent schema drift (fields + validation behavior for structured targets payloads)
    - ✅ No contract break for legacy endpoints (explicitly verified in tests)


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


- [x] P1: Add canonical orchestration contract matrix for PR governance
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #996 (`docs(orchestration): add canonical PR orchestration contract matrix`)
  - Status: ✅ Merged (PR #996, 2026-03-06)
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Rules are split across check_pr_body_phase2_gates.py, check_pr_merge_readiness.py, check_review_threads_disposition.py and AGENTS.md; single source of truth reduces drift.
  - Links:
    - `scripts/ci/check_pr_body_phase2_gates.py:11` (Phase 2 contract config)
    - `scripts/ci/check_pr_merge_readiness.py:337` (unresolved threads), `:350` (actionable items)
    - `scripts/orchestration/check_review_threads_disposition.py:27` (FIXED/NOT-A-BUG/DEFERRED), `:170` (trigger-only ban)
    - `AGENTS.md:42` (Review Governance), `:103` (FIXED proof), `:418` (Fixed in Commit Mapping)
  - DoD:
    - Single doc (e.g. docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md) is the canonical SoT; AGENTS.md only links to it
    - Doc defines Phase 2 body contract, merge readiness contract, FIXED/NOT-A-BUG/DEFERRED proof rules, required-check truth for current HEAD, hard/soft/external CI check classes
    - Linked from AGENTS.md as canonical orchestration governance reference
  - Artifact: `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`


- [x] P1: Agent task evaluation contract (success criteria per task class)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #866 (docs/agent-task-evaluation-contract)
  - Status: ✅ Completed (PR #866, 2026-02-22, merge SHA `fdd31e21`)
  - Area: orchestration / agents / quality
  - Finding Type: process / evaluation
  - Reason: EVMbench-style evaluation requires explicit success criteria and optional recall checklist per task class (CI fix, security remediation, docs-only). Define contract and link to existing gates.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
    - `docs/orchestration/AGENT_TASK_EVALUATION_CONTRACT.md`
    - [PR #866](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/866)
  - DoD:
    - [x] Doc defines success criteria for at least: "CI fix", "security remediation", "docs-only"
    - [x] Optional recall-style checklist per class; linked from RUNBOOK or AGENTS


- [x] P1: Document required-check truth for merge (current HEAD only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #996 (`docs(orchestration): add canonical PR orchestration contract matrix`) + PR #1010 (`fix(orchestration): close runtime wave 4 drift`)
  - Status: ✅ Merged (governance rule codified by PR #996 and refreshed in PR #1010)
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Merge decision must be based on latest required checks for current HEAD only; cancelled/stale runs ignored to avoid confusion and extra iterations.
  - Links:
    - `AGENTS.md:31` (PR merge readiness), `:39` (merge checklist)
    - `scripts/ci/check_pr_merge_readiness.py:337` (unresolved_threads), `:344` (errors)
  - DoD:
    - Canonical rule documented: merge decision based on latest required checks for current HEAD only; cancelled runs ignored; non-required external reviews do not block unless explicitly required
    - Referenced from AGENTS.md or orchestration contract doc (single canonical name for governance doc)


- [x] P1: Hint levels for coordinator and fix-CI tasks
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #866 (docs/agent-task-evaluation-contract)
  - Status: ✅ Completed (PR #866, 2026-02-22, merge SHA `fdd31e21`)
  - Area: orchestration / agents
  - Finding Type: process
  - Reason: EVMbench shows hints (low/medium/high) materially improve outcomes. Document hint levels for "fix CI" and coordinator tasks (e.g. low = branch + run link; medium = failed job + log; high = exact assertion + location).
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `docs/orchestration/workflow.md`
    - [PR #866](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/866)
  - DoD:
    - [x] Orchestration doc or coordinator prompt template includes hint-level definitions
    - [x] ci-watcher / loop-on-ci prompts aligned where applicable


- [x] P1: Minimal agent metrics (fix rate / first-run pass)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - Status: ✅ Completed (PR #868, 2026-02-22)
  - Merge SHA: bb7b0c619c7fd88b1dd729a7ed9d34913e30292b
  - Area: orchestration / quality
  - Finding Type: metrics
  - Reason: Define minimal agent metrics (e.g. "CI fix: pass within N iterations"; "merge readiness: first run vs after edits") and record in ledger or audit when relevant.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - DoD:
    - [x] Doc or ledger section defines at least 2 agent task metrics and when to record them
    - [x] No dashboard required; manual or opportunistic recording is acceptable


- [x] P1: Move Fixed in Commit Mapping source-of-truth from PR body to repo file
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #998 (`fix/orch-move-fixed-mapping-sot-to-repo-file`)
  - Status: ✅ Merged (PR #998, 2026-03-07)
  - Area: orchestration / CI / review governance
  - Finding Type: process hardening
  - Reason: Eliminate PR body race/staleness and make governance deterministic on git SHA.
  - Links:
    - `scripts/orchestration/review_mapping_artifact.py` (canonical artifact helper)
    - `docs/review/PR_<N>_FIXED_MAPPING.md` (artifact format)
    - `scripts/ci/check_pr_body_phase2_gates.py`, `scripts/ci/check_pr_merge_readiness.py`, `scripts/orchestration/check_review_threads_disposition.py` (artifact-first)
  - DoD:
    - [x] Merge readiness/disposition reads mapping from `docs/review/PR_<N>_FIXED_MAPPING.md`
    - [x] PR body optional summary/mirror only
    - [x] Tests added (`tests/test_review_mapping_artifact.py`, Phase2 artifact test)

<a id="ledger-p1-compliance-runtime-slice-2"></a>
- [ ] P1: Compliance runtime slice 2 for AI wellness consent orchestration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (privacy/compliance)
  - Target PR: PR-TBD (`feat/compliance-runtime-slice-2-consent-dsar`)
  - Status: Planned
  - Area: backend / compliance / legal-runtime
  - Finding Type: deferred follow-up
  - Reason: Compliance Runtime Slice 1 ships transparency, privacy payload assembly, and minimization only. This follow-up is intentionally narrowed to AI wellness consent context/orchestration so it does not duplicate the broader P0 EU-first compliance control plane epic.
  - Carryover From:
    - PR `#1046` (`feat: EU-first compliance control plane`)
    - `docs/review/PR_1046_FIXED_MAPPING.md`
  - Carryover Note: Public DSAR/export/delete boundaries and regulated/provider-lane separation remain tracked by the P0 epic at `#ledger-p0-eu-compliance-control-plane-follow-through`; this P1 item owns only the next tactical consent slice for wellness AI surfaces.
  - Links:
    - `#ledger-p0-eu-compliance-control-plane-follow-through`
    - `core/compliance/privacy.py`
    - `core/compliance/dsar.py`
    - `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
    - `docs/legal/Privacy.md`
  - DoD:
    - Backend consent context is defined for AI wellness surfaces without changing deterministic wellness calculations
    - AI wellness routes expose explicit consent-context requirements in runtime/docs without introducing a regulated/clinical lane
    - DSAR/export/delete public-surface decisions remain linked to the P0 epic and are not duplicated in this slice
    - `pre-commit run --all-files` and `make verify` pass in PR scope


- [x] P1: Orchestration — add `AGENT_KNOWLEDGE_MAP.md` (agent → RAG corpus / index policy SoT)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #963
  - Status: merged 2026-03-04 (79024d70)
  - Priority: P1
  - Area: orchestration / RAG
  - Finding Type: policy gap
  - Reason: AGENT_CONTEXT_MAP and AGENT_CAPABILITY_MATRIX exist; AGENT_CORPUS_MAP exists in core/rag/contracts.py. No docs-level SoT for agent → corpus → RAG index policy. Security posture (retrieved content untrusted) needs policy clarity.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md`
    - `core/rag/contracts.py` (AGENT_CORPUS_MAP)
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Document `docs/orchestration/AGENT_KNOWLEDGE_MAP.md` created
    - References AGENT_CORPUS_MAP policy; boundaries + indexing scope + security posture described
    - If RAG deprioritized: close as WONTFIX with explicit reason


- [x] P1: Wave 2 experimentation framework and paywall optimization loop
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #852 (docs/wave2-experimentation-framework)
  - Status: ✅ Completed (PR #852, 2026-02-21, merge SHA `851f1728`)
  - Area: product / growth / analytics
  - Finding Type: growth optimization
  - Locations:
    - `docs/analytics/EXPERIMENTATION_FRAMEWORK.md`
    - `docs/analytics/EXPERIMENT_REGISTRY.md`
    - `docs/analytics/ANALYTICS_INDEX.md`
  - Reason: establish repeatable A/B lifecycle with measurable guardrails for onboarding and paywall conversion.
  - Links:
    - `docs/analytics/EXPERIMENT_REGISTRY.md`
    - `docs/analytics/ANALYTICS_INDEX.md`
    - `docs/analytics/EXPERIMENTATION_FRAMEWORK.md`
    - [PR #852](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/852)
  - DoD:
    - [x] Experiment lifecycle states documented
    - [x] Initial prioritized growth experiments registered with owners and dates
    - [x] Guardrail metrics required for promotion decisions


- [x] P1: Implement WebSocket endpoint with security from start
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (feature + security)
  - Target PR: PR #818
  - Status: ✅ Merged (PR #818, 2026-02-19)
  - Reason: Canonical `/ws` endpoint and security behavior are now validated with deterministic tests. Authentication and rate-limit close behavior are covered to prevent drift.
  - Links:
    - [PR #818](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/818)
    - tests/test_realtime_ws_security.py
    - app/routers/realtime_ws.py
    - docs/rfc/TON_RFC.md (WebSocket mentioned as requirement for real-time functions)
    - docs/design/NUTRITION_COACHING_DESIGN.md (potential use case: real-time coaching)
  - Prerequisites:
    - ✅ Security requirements defined (auth + rate-limiting)
    - ✅ Use cases defined (what real-time features need WebSocket)
  - DoD:
    - ✅ WebSocket endpoint `/ws` available with FastAPI WebSocket support
    - ✅ Authentication required (token in query params or headers)
    - ✅ Rate-limiting implemented (per-user message limits in router policy)
    - ✅ Tests verify unauthenticated connections are rejected (close code policy)
    - ✅ Tests verify rate-limiting closes connection when the limit is exceeded
    - ✅ CI checks green on merged PR (#818)


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


- [x] P1: Oracle / known-good gate behavior documentation
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - Status: ✅ Completed (PR #868, 2026-02-22)
  - Merge SHA: bb7b0c619c7fd88b1dd729a7ed9d34913e30292b
  - Area: runbooks / CI gates
  - Finding Type: process
  - Reason: EVMbench validates graders on oracle solutions. Document expected behavior of merge_readiness_gate and dependency_security_guard on known-good input (e.g. PR with all checkboxes and mapping → pass).
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `scripts/ci/check_pr_merge_readiness.py`
    - `tests/test_dependency_security_guard.py`
    - [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - DoD:
    - [x] RUNBOOK or test doc: "Expected: PR body with [x] and mapping → merge_readiness passes"
    - [x] Optional: deterministic test that applies known-good PR body and asserts gate pass


- [x] P1: Runbook coverage step — full guard suite and no related violations
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: PR #866 (docs/agent-task-evaluation-contract)
  - Status: ✅ Completed (PR #866, 2026-02-22, merge SHA `fdd31e21`)
  - Area: runbooks / guards
  - Finding Type: process
  - Reason: EVMbench scores on comprehensive coverage. Before closing a guard/security PR, run full guard suite and ensure no related violations in changed modules.
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `RUNBOOK_AGENT.md`
    - [PR #866](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/866)
  - DoD:
    - [x] RUNBOOK step added: "Run full guard suite; confirm no related violations in changed modules"
    - [x] Referenced from PR template or merge checklist where applicable


- [x] P1: Agent-as-attacker threat model section in security baseline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1
  - Target PR: [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - Status: ✅ Completed (PR #868, 2026-02-22)
  - Merge SHA: bb7b0c619c7fd88b1dd729a7ed9d34913e30292b
  - Area: security / agent control plane
  - Finding Type: security documentation
  - Reason: EVMbench measures exploit capability; we should document abuse scenarios (what would an agent need to do to violate policy?) and map to controls (allowlist, audit trail, token TTL).
  - Links:
    - `docs/audit/EVMBENCH_INSPIRED_AGENT_EVALUATION_BRAINSTORM_2026-02-21.md`
    - `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`
    - [PR #868](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/868)
  - DoD:
    - [x] New section in AGENT_CONTROL_PLANE_SECURITY_BASELINE: "Agent-as-attacker scenarios" with mapping to existing controls
    - [x] No new runtime code required; doc only


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


### P2

<a id="ledger-p2-fitchef-mascot-insight-endpoint"></a>
- [x] P2: FitChef mascot insight endpoint
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1065`
  - Status: Merged on 10 March 2026 (`#1065`)
  - Area: AI runtime / coaching / product
  - Finding Type: execution
  - Locations:
    - `core/insight/fitchef_companion.py`
    - `app/routers/fitchef_insight.py`
    - `app/schemas/fitchef_coaching.py`
  - Reason: The first public mascot slice should expose a bounded text-only coaching surface without changing the current `/api/v1/insight` contract or reviving `/api/v1/vip/insight*` drift.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/contracts/API_CANONICAL_MAP.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
    - `docs/review/PR_1065_FIXED_MAPPING.md`
  - DoD:
    - `POST /api/v1/insight/fitchef` exists as VIP-only mascot surface
    - Request/response schemas are typed and documented in OpenAPI
    - Rate-limit, monthly quota, policy audit, and wellness-language validation follow canonical insight ordering
    - `/api/v1/insight` remains unchanged
    - Contract tests cover `200` plus representative failure cases and assert JSON `Content-Type` plus standardized error fields
    - One happy-path integration test lands in the same PR
    - Output-shaping path is deterministic and documented in the PR IN/OUT spec, test plan, and rollback note
  - Blockers: Depends on [P2: FitChef sandbox Phase 2 deferred scope](#ledger-p2-fitchef-sandbox-phase-2-deferred-scope)

<a id="ledger-p2-fitchef-weekly-reflection-endpoint"></a>
- [x] P2: FitChef weekly reflection endpoint
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1071`
  - Status: Merged on 10 March 2026 (`#1071`)
  - Area: AI runtime / coaching / product
  - Finding Type: execution
  - Locations:
    - `core/insight/fitchef_companion.py`
    - `app/routers/fitchef_insight.py`
    - `app/schemas/fitchef_coaching.py`
  - Reason: Weekly reflection is the second mascot scenario and should reuse the same bounded FitChef coaching runtime instead of inventing a separate route family or client-owned workflow.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
    - `docs/review/PR_1071_FIXED_MAPPING.md`
  - DoD:
    - `POST /api/v1/insight/fitchef/weekly-reflection` exists with shared coaching envelope
    - Response uses `scenario=\"weekly_reflection\"` and returns bounded action items
    - Tier/rate-limit/quota/audit posture matches the mascot insight endpoint
    - No persistence, exports, or client-owned orchestration is added
    - Contract tests cover `200` plus representative failure cases and assert JSON `Content-Type` plus standardized error fields
    - One happy-path integration test lands in the same PR
    - Output-shaping path is deterministic and documented in the PR IN/OUT spec, test plan, and rollback note
  - Blockers: Depends on [P2: FitChef mascot insight endpoint](#ledger-p2-fitchef-mascot-insight-endpoint)

<a id="ledger-p2-fitchef-slip-support-endpoint"></a>
- [x] P2: FitChef slip-support endpoint
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1076 (`feat(fitchef): add slip-support endpoint`)
  - Status: Merged on 10 March 2026 (`#1076`)
  - Area: AI runtime / coaching / product
  - Finding Type: execution
  - Locations:
    - `core/insight/fitchef_companion.py`
    - `app/routers/fitchef_insight.py`
    - `app/schemas/fitchef_coaching.py`
  - Reason: Slip-support is the third mascot scenario and should normalize recovery-oriented coaching into the same text-only runtime instead of introducing reminders, exports, or autonomous background work.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/design/NUTRITION_COACHING_DESIGN.md`
    - `core/insight/creative_scientific_innovations.md`
    - `docs/review/PR_1076_FIXED_MAPPING.md`
  - DoD:
    - `POST /api/v1/insight/fitchef/slip-support` exists with shared coaching envelope
    - Response uses `scenario=\"slip_support\"` and excludes therapy or medicalized language
    - Non-judgmental recovery guidance is covered by deterministic tests
    - No reminders, background jobs, realtime fan-out, or export hooks are added
    - Contract tests cover `200` plus representative failure cases and assert JSON `Content-Type` plus standardized error fields
    - One happy-path integration test lands in the same PR
    - Output-shaping path is deterministic and documented in the PR IN/OUT spec, test plan, and rollback note
  - Blockers: Depends on [P2: FitChef mascot insight endpoint](#ledger-p2-fitchef-mascot-insight-endpoint)

<a id="ledger-p2-fitchef-runtime-orchestration-dedup"></a>
- [x] P2: FitChef runtime orchestration dedup
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1083 (`refactor(fitchef): deduplicate runtime orchestration path`)
  - Status: Merged on 10 March 2026 via PR #1083
  - Area: AI runtime / orchestration / tech debt
  - Finding Type: tech-debt
  - Locations:
    - `app/services/fitchef_runtime.py`
  - Reason: `run_mascot_insight_task()` and `run_weekly_reflection_task()` currently duplicate the bounded orchestration path for RAG retrieval, audit gates, quota enforcement, provider calls, and stable error mapping. This should be consolidated only after the Phase 2 slices stabilize.
  - Links:
    - `docs/contracts/FITCHEF_MASCOT_PHASE2_CONTRACT.md`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-fitchef-weekly-reflection-endpoint`
    - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-fitchef-slip-support-endpoint`
    - `docs/review/PR_1083_FIXED_MAPPING.md`
  - DoD:
    - Shared orchestration helper removes duplicated FitChef VIP runtime flow without changing public route contracts
    - Mascot, weekly reflection, and slip-support still preserve feature-flag, tier, rate-limit, quota, audit, and provider error ordering
    - Deterministic regression tests cover the shared helper paths
  - Blockers: None

<a id="ledger-p2-monthly-pr-analysis-cadence"></a>
- [ ] P2: Monthly PR analysis cadence and evidence hygiene
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-MONTHLY-PR-ANALYSIS-REFRESH
  - Status: 🟡 In progress (February-March 2026 baseline artifact added)
  - Area: docs / governance / reporting
  - Finding Type: reporting hygiene
  - Reason (EN): Monthly retrospective summaries are useful for program steering, but they must remain evidence-first and must not become a second source of truth for backlog closure, merge readiness, or release status. A tracked cadence item keeps the artifact honest and versioned.
  - Links:
    - `docs/review/MONTHLY_PR_ANALYSIS_2026-03.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
    - `docs/orchestration/TOP20_PR_RECOVERY_TASK_PACKETS_2026-03-08.md`
    - `docs/roadmap/P0_MASTER_CHECKLIST_PHASE_FIT_TRIAGE_2026-03-05.md`
  - DoD:
    - Monthly analysis artifact exists under `docs/review/` with explicit period and source list
    - Summary distinguishes closed items from materially advanced but still open work
    - Report explicitly points back to canonical SoTs (`BACKLOG_LEDGER`, Top-20 queue, phase-fit checklist)
    - Future monthly refreshes supersede prior snapshots via new versioned artifacts instead of silent rewrites
    - Docs-only PR stays narrow and does not introduce runtime or contract drift

- [x] P2: Philosophy Validator (runtime LLM output validation)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality / safety)
  - Target PR: PR #972 (`feat/philosophy-validator-core`)
  - Status: ✅ Merged (PR #972, 2026-03-04)
  - Reason (EN): Deterministic runtime validator for LLM outputs used in product copy/coaching. `validate_llm_output(text, domain=None) -> Report`; BLOCKER codes: WELLNESS_MEDICAL_CLAIM_*, WELLNESS_GUARANTEE, NON_FALSIFIABLE_VAGUE, POTENTIAL_CONTRADICTION. No network, regex/rules only. Coordinator can require rewrite before merge.
  - Links:
    - `core/insight/philosophy_validator.py`
    - `tests/test_philosophy_validator.py`
  - DoD:
    - `core.insight.philosophy_validator` module merged
    - Unit tests pass (RU/EN blockers, contradiction, determinism)
    - AGENTS.md policy: LLM outputs must pass philosophy_validator (BLOCKER = rewrite)


- [x] P2: Philosophy-agent + RAG validation pipeline
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (AI / RAG / philosophy)
  - Target PR: feat/p2-philosophy-rag-pipeline
  - Status: ✅ Implemented (2026-03-02)
  - Reason (EN): Pipeline query → RAG → philosophy-agent → LLM so that RAG context is validated before response; per BACKLOG Philosophical logic principles.
  - Links:
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md` (sect. 3.2)
    - `docs/insights/PHILOSOPHICAL_LOGIC_LLM_RELIABILITY.md`
    - `.cursor/agents/philosophy-agent.md`
    - `core/rag/philosophy_pipeline.py` (4-stage pipeline implementation)
  - DoD:
    - RAG context passed to philosophy validation layer; integration test
    - `make verify` passes
  - Evidence:
    - 4-stage deterministic pipeline: rule validation → claim classification → source alignment → logical consistency
    - Stage 1 blocks (medical/weasel/malformed); stages 2-4 advisory-only warnings
    - 42 unit tests in `tests/test_philosophy_pipeline.py`
    - diff-coverage 98% (>=97%)


- [x] P2: RAG chunk content redaction helper (PII/sensitive data)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (defense-in-depth; corpus is controlled server docs)
  - Target PR: PR #1010
  - Status: Done (merged in PR #1010)
  - Reason (EN): The redaction helper was added and wired into prompt assembly and response previews as part of the Wave 4 runtime closure.
  - Links:
    - `app/routers/cbt_insight.py:186-196` (chunk content usage)
    - `PR #942` CodeRabbit comment (`2868000571`)
  - DoD:
    - Add redact_rag_context_for_insight() helper (or equivalent)
    - Apply to prompt assembly and response previews
    - Unit tests for redaction patterns


- [x] P2: RAG for CBT agent (first domain agent)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (AI / RAG / coaching)
  - Target PR: feat/p2-rag-cbt-agent
  - Status: Implemented
  - Reason (EN): Connect CBT/coaching flow to RAG per AGENT_CORPUS_MAP; first agent to use retrieval before LLM.
  - Implementation (EN):
    - Created CBT corpus documents: `docs/cbt/cognitive_restructuring.md`, `docs/cbt/thought_records.md`, `docs/psychology/motivation_theories.md`
    - Added `AGENT_CORPUS_MAP` to `core/rag/contracts.py` with cbt-agent mapping
    - Implemented corpus filtering in `core/rag/vector_rag.py` and `core/rag/simple_rag.py`
    - Created PRO-gated endpoint `POST /api/v1/pro/cbt/insight` in `app/routers/cbt_insight.py`
    - Feature-flagged via `FEATURE_CBT_AGENT` env var
  - Links:
    - `docs/audit/RAG_IMPLEMENTATION_AND_AGENT_KNOWLEDGE_AUDIT.md` (sect. 4.2, 4.3)
    - `docs/contracts/RAG_CONTRACT.md` (Corpus Routing)
    - `.cursor/agents/cbt-psychologist-agent.md`
  - DoD:
    - CBT path retrieves context from docs/cbt/ (or configured corpus); context passed to LLM
    - Tier-gated (PRO/VIP); tests; `make verify` passes


- [x] OpenAPI debt for `/api/v1/export/sign` reclassified as internal contract
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #1035 (`fix(export): harden signing secret access`)
  - Status: ✅ Merged (PR #1035, 2026-03-08)
  - Priority: P2
  - Area: backend / OpenAPI / frontend contract
  - Finding Type: contract-clarification
  - Location: `app/routers/plan_export.py`, `frontend/src/lib/sharedLinks.ts`
  - Reason: Resolved in PR #1035: `/api/v1/export/sign` remains intentionally hidden from canonical public OpenAPI, keeps the stable runtime JSON shape `{url, exp, ttl}`, and preserves the explicit internal web-adapter boundary via a local typed adapter.
  - Links:
    - `app/routers/plan_export.py`
    - `frontend/src/lib/sharedLinks.ts`
    - `legacy_app.py`
    - `docs/review/PR_1035_FIXED_MAPPING.md`
  - DoD:
    - Backend keeps `SignedLinkResponse` as the runtime response model
    - `POST /api/v1/export/sign` keeps the stable JSON shape `{url, exp, ttl}` with regression coverage
    - Public OpenAPI continues to exclude export endpoints
    - Web keeps a local typed adapter with explicit rationale for the hidden-schema boundary


- [x] P2: Execution Wave 4 — Semantic retrieval (pgvector + multilingual embeddings)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #902 (`docs/food-db-w4-kickoff`) + PR #905 (`feat(food-db): add W4-B feature-flag semantic search routing`) + PR #914 (`feat/food-w4-benchmark-rollback-closure`)
  - Status: ✅ Merged (W4-A #902, W4-B #905, W4-C #914 all merged 2026-02-26)
  - Area: backend / search relevance
  - Finding Type: strategic enhancement
  - Reason: Semantic retrieval is valuable but should follow stable snapshot/search/menu foundations and remain optional behind a feature flag.
  - Execution Notes:
    - (2026-02-25) W4-A kickoff docs merged in PR #902
    - (2026-02-25) W4-B runtime merged in PR #905 (feature-flagged `semantic > compat > legacy`)
    - (2026-02-26) W4 benchmark + rollback validation bundle prepared in PR #914
      - Added semantic benchmark harness: `scripts/benchmarks/food_semantic_retrieval_benchmark.py`
      - Added rollback-safe tests for semantic flag-off path: `tests/test_food_store_service.py`, `tests/test_foods_router_additional.py`
      - Added benchmark audit artifact/report: `docs/audit/PR_914_FOOD_DB_W4_SEMANTIC_BENCHMARK.md`, `docs/audit/artifacts/food_w4_semantic_benchmark.json`
  - Links:
    - `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md`
    - `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
    - `scripts/benchmarks/food_semantic_retrieval_benchmark.py`
    - `docs/audit/PR_914_FOOD_DB_W4_SEMANTIC_BENCHMARK.md`
  - DoD:
    - Feature-flagged semantic retrieval is implemented
    - Cost/performance benchmark is documented
    - Rollback-safe deployment path is defined and validated
    - Non-semantic search path remains default and stable

<a id="ledger-p2-search-meili-transport-pooling"></a>
- [ ] P2: Search Meili transport pooling + lifecycle hook
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-SEARCH-MEILI-TRANSPORT-POOLING
  - Area: backend / search
  - Finding Type: runtime hardening follow-up
  - Reason: The search shadow foundation intentionally keeps an injected per-call `httpx.Client` transport because Meili remains optional and low-volume in this slice. If traffic expands, the backend should move to a shared pooled client with deterministic shutdown semantics instead of creating a fresh client per request.
  - Links:
    - `app/services/search_meili.py`
    - `docs/review/PR_1099_FIXED_MAPPING.md`
  - DoD:
    - Shared Meili transport/client is lifecycle-managed and explicitly closed on shutdown
    - Search bootstrap owns transport configuration instead of hidden module-level state
    - Tests cover connection reuse and shutdown cleanup without changing `/api/v1/foods*` contracts

<a id="ledger-p2-search-pgtrgm-candidate-generation"></a>
- [ ] P2: Search PostgreSQL `pg_trgm` candidate generation lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-SEARCH-PGTRGM-CANDIDATES
  - Area: backend / search
  - Finding Type: deferred hybrid-search rollout
  - Reason: This PR intentionally preserves SQLite/FTS as the live baseline and adds Meili shadow mode only. PostgreSQL `pg_trgm` candidate generation remains deferred until PostgreSQL is promoted to the canonical search-adjacent store.
  - Links:
    - `app/services/search_meili.py`
    - `app/services/food_store.py`
    - `docs/review/PR_1099_FIXED_MAPPING.md`
  - DoD:
    - `pg_trgm` candidate generation exists behind additive strategy routing with deterministic fallback
    - Relevance and latency tests cover candidate generation for representative food queries
    - `/api/v1/foods*` contracts remain unchanged and shadow divergence is observable

<a id="ledger-p2-search-zero-downtime-swap-orchestration"></a>
- [ ] P2: Search zero-downtime swap orchestration lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR-TBD-SEARCH-ZERO-DOWNTIME-SWAP
  - Area: backend / search / ops
  - Finding Type: deferred indexing-orchestration rollout
  - Reason: This foundation PR adds deterministic indexing helpers only. The admin/orchestration surface for build-validate-warm-swap cleanup remains deferred until Meili shadow rollout is proven and operational safeguards are specified.
  - Links:
    - `app/services/food_search_indexing.py`
    - `docs/review/PR_1099_FIXED_MAPPING.md`
  - DoD:
    - Offline build-validate-warm-swap workflow is implemented with deterministic commands or admin surface
    - Swap orchestration is tested against `*_v2` indexes without changing public food API contracts
    - Grace-period cleanup and rollback-safe recovery are documented and covered by tests


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


- [x] P2: Orchestration — agent routing graph (task → domains → agents)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #967
  - Status: ✅ Merged (PR #967, 2026-03-04)
  - Priority: P2
  - Area: dev-process / orchestration
  - Finding Type: routing
  - Reason: Capability matrix is advisory; no automatic routing. Task → domain classifier → agent set makes orchestration deterministic.
  - Links:
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Routing graph spec or document (task → domains → agents)
    - Linked from coordinator or capability matrix


- [x] docs(infra): add `.markdownlint.json` (follow-up after PR #617)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #775 (`docs(audit): add CP3 no-op audit and execution plan`)
  - Status: ✅ Merged (PR #775, 2026-02-17)
  - Reason: PR #617 scope reduced to docs-only (audit + handoff); markdownlint config moved out to avoid diff-coverage/CI scope. Add repo-wide markdownlint config in dedicated PR.
  - DoD: New PR with `.markdownlint.json` only; CI green; no mixing with code/audit PRs.


- [x] P2: Guards — wellness language blocker (docs safety)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (quality / safety)
  - Target PR: PR #969 (test/guards-wellness-language-blockers)
  - Status: ✅ Merged (PR #969, 2026-03-04)
  - Reason (EN): Deterministic CI guard to block medical/diagnostic claims in docs and public copy (wellness-only posture). Blocks RU+EN phrases: лечит, вылечит, вылечим, исцелит, диагноз, диагностирую, диагностирует; allowlist for policy docs.
  - Links:
    - `tests/guards/test_wellness_language_blockers_guard.py`
    - `tests/guards/wellness_language_allowlist.txt`
  - DoD:
    - Guard test merged; allowlist exists; fails on blocker phrases; documented marker `pulseplate-allow:blocker-example`


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

- [ ] P1: Agent knowledge library template packs (domain-specific)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (process scalability)
  - Target PR: PR_TBD_AGENT_LIBRARY_TEMPLATE_PACKS
  - Status: 📋 Planned
  - Reason (EN): Bootstrap library artifacts are in place, but recurring cycles
    need reusable, domain-specific packs (security, RAG, UX, DS) to keep
    brainstorm-to-PR flow fast and deterministic without policy drift.
  - Links:
    - `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
    - `docs/library/index.md`
    - `docs/library/promotion/2026-02-19_agent-library-bootstrap_promotion-log.md`
    - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
  - DoD:
    - Add template packs under `docs/library/templates/` for at least 4 tracks:
      security, RAG, UX/accessibility, data/evaluation
    - Each template includes routing card, evidence section, promotion target,
      and deferred-item ledger block
    - Add one worked example cycle using one template pack
    - `ReadLints` clean for all new docs

<a id="ledger-p1-agent-experimentation-lane"></a>
- [x] P1: Governed agent experimentation lane (PR1-PR6 orchestration epic)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (process scalability + bounded AI optimization)
  - Target PR: PR #1073 -> PR #1081 -> PR #1088 -> PR #1096 -> PR #1092 -> PR #1102 -> PR #1107
  - Status: ✅ Completed on 2026-03-11 (`a00bba2f`; PR `#1107`) with the original PR1-PR6 chain fully merged; PR `#1114` then reused the same governed lane for the next applied verification-first reliability cycle without reopening the epic
  - Reason (EN): PulsePlate now has coordinator-first workflow, KPP promotion, reflection, research track, telemetry rollups, and deterministic benchmark artifacts, but it still lacks one canonical protocol for `autoresearch`-style experiment loops. We need a governed experimentation lane so future optimization cycles can be bounded, auditable, and KPP-only instead of becoming ad-hoc autonomous mutation. (RU: Нужен единый канон для агентных циклов экспериментов, чтобы оптимизация не превращалась в неконтролируемую автомутацию репозитория.)
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
    - `docs/orchestration/workflow.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
    - `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
  - DoD:
    - PR1 governance SoT is merged and linked from the canonical orchestration docs
    - PR2 bootstrap tooling, PR3 runner MVP, PR4 promotion/telemetry, PR5 CV eval lane, and PR6 first applied reliability optimization all have explicit backlog entries
    - No phase of the lane permits hidden memory, autonomous merge, or mutation of immutable evaluation oracles
    - Sequencing stays explicit: PR1 governance -> PR2 tooling -> PR3 runner -> PR4 promotion -> PR5 CV -> PR6 reliability optimization

<a id="ledger-p1-agent-experiment-bootstrap"></a>
- [x] P1: PR2 deterministic experiment bootstrap tooling
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency for the experimentation lane)
  - Target PR: PR #1081
  - Status: ✅ Merged on 2026-03-10 (`fd7a1626`)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
  - Reason (EN): After governance lands, the lane needs a deterministic bootstrap artifact for experiment IDs, mutable surfaces, immutable oracle lists, budgets, and routing so candidate loops can start from a structured packet instead of prompt-only instructions.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
    - `scripts/orchestration/experiment_bootstrap.py`
    - `scripts/orchestration/experiment_contract.py`
  - DoD:
    - Local experiment packet bootstrap tooling exists with deterministic JSON output
    - Packet schema covers mutable surface, immutable oracles, budgets, metrics, and promotion target
    - Outputs live under gitignored local artifacts only
    - Tooling does not mutate runtime code or public contracts

<a id="ledger-p1-agent-experiment-runner"></a>
- [x] P1: PR3 experiment runner MVP for bounded candidate loops
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (dependency for first applied optimization)
  - Target PR: PR #1088
  - Related follow-up: PR #1096 (`fix(app): restore bootstrap patchability on main`)
  - Related follow-up status: ✅ Merged (PR #1096, 2026-03-11)
  - Related follow-up SHA: `ddfee576e0d2b53d3a24e08ee58080a6c73cb75d`
  - Status: ✅ Merged with hotfix traceability (PR `#1088` delivered the bounded experiment runner MVP; PR `#1096` then remediated the post-merge `app` bootstrap/patchability regression on `main` without widening scope into FitChef, sandbox, or design lanes)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR2 deterministic experiment bootstrap tooling](#ledger-p1-agent-experiment-bootstrap)
  - Reason (EN): The experimentation lane needs a bounded runner that applies candidate changes only to allowlisted surfaces, evaluates them against immutable oracles, and discards regressions without touching merge/readiness flows.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `scripts/orchestration/experiment_contract.py`
    - `scripts/orchestration/experiment_runner.py`
    - `tests/test_experiment_bootstrap.py`
    - `tests/test_experiment_runner.py`
  - DoD:
    - Runner uses isolated execution and never mutates a dirty shared worktree
    - Runner enforces budgets and failure classes from the experimentation protocol
    - Immutable oracle mutation is rejected fail-closed
    - Runner outputs candidate result artifacts, not autonomous merge-ready commits

<a id="ledger-p1-agent-experiment-promotion"></a>
- [x] P1: PR4 experiment promotion and telemetry integration
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (governance closure for experiment outputs)
  - Target PR: PR #1092
  - Status: ✅ Merged on 2026-03-11 (`e0771be5`)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
  - Reason (EN): Winning candidates need one governed promotion path into PR packets, audits, guards, ledger items, or memory capsules, and telemetry needs experiment-aware fields so orchestration learning remains artifact-based and observable.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
    - `scripts/orchestration/agent_run_summary.py`
    - `scripts/orchestration/telemetry_rollup.py`
  - DoD:
    - Promotion tooling enforces exactly one durable destination per winning experiment
    - Telemetry rollups understand experiment identifiers and failure/promotion classes
    - Deferred experiment outcomes are ledgered immediately
    - No hidden-memory path bypasses KPP promotion

<a id="ledger-p1-agent-experiment-cv-lane"></a>
- [x] P1: PR5 CV experimentation and evaluation lane (docs/eval only)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (future multimodal track, no runtime integration yet)
  - Target PR: #1102
  - Status: ✅ Merged on 2026-03-11 (`55783414`; PR `#1102`)
  - Follow-up: Canonical ledger closeout normalization is implemented in PR `#1120` (this docs-only follow-up) and becomes canonical on merge.
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [CV (photo → food): contract schema + uncertainty/degrade UX states + privacy packet](#ledger-p2-cv-photo-food)
  - Reason (EN): Computer vision needs the same packetized experimentation contract as LLM/RAG work, but limited to offline evaluation, uncertainty, privacy packets, and deterministic degrade behavior before any runtime photo feature is attempted.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/CV_EXPERIMENT_PACKET_TEMPLATE.md`
    - `docs/orchestration/contracts/CV_PHOTO_FOOD_EVAL_CONTRACT.md`
    - `.cursor/agents/cv-agent.md`
    - `.cursor/agents/data-scientist-agent.md`
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
    - `docs/audit/PR_1102_CV_EXPERIMENTATION_LANE_AUDIT_2026-03-11.md`
  - DoD:
    - CV experiment packet fields cover dataset, uncertainty bands, privacy constraints, and degrade states
    - CV lane remains docs/eval only with no image-retention runtime behavior
    - Coordinator routing for CV experiments is explicit and bounded
    - Deterministic acceptance criteria are documented

<a id="ledger-p1-agent-experiment-first-reliability-pr"></a>
- [x] P1: PR6 first applied LLM/RAG reliability optimization via governed lane
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (first practical output of the experimentation lane)
  - Target PR: PR #1107
  - Status: ✅ Merged on 2026-03-11 (`a00bba2f`)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
    - [P1: PR4 experiment promotion and telemetry integration](#ledger-p1-agent-experiment-promotion)
    - [P1: Recursive methods for LLM/RAG/AI assistant (multi-hop retrieval, recursive reasoning, self-refinement, self-verification, learning)](#ledger-p1-recursive-methods)
  - Reason (EN): The first applied experiment-generated change should target `LLM/RAG reliability`, using current deterministic benchmark and test oracles to validate one bounded optimization before broader autonomous tooling is trusted.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `scripts/orchestration/experiment_bootstrap.py`
    - `scripts/orchestration/experiment_runner.py`
    - `tests/test_experiment_bootstrap.py`
    - `tests/test_experiment_runner.py`
  - DoD:
    - One bounded reliability candidate is generated through the governed lane
    - Candidate improvement is accepted by immutable oracles and documented with evidence
    - Result is promoted through a normal human-reviewed PR
    - No storage-cost or CV scope is mixed into this first applied optimization

<a id="ledger-p1-reliability-v2-verification-pr"></a>
- [x] P1: PR7 verification-first Reliability V2 applied orchestration cycle
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (factual trust uplift on the merged experimentation lane)
  - Target PR: PR #1114
  - Status: ✅ Merged on 2026-03-11 (`57770899`)
  - Dependencies:
    - [P1 Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR6 first applied LLM/RAG reliability optimization via governed lane](#ledger-p1-agent-experiment-first-reliability-pr)
    - [P1: PR3 experiment runner MVP for bounded candidate loops](#ledger-p1-agent-experiment-runner)
    - [P1: PR4 experiment promotion and telemetry integration](#ledger-p1-agent-experiment-promotion)
  - Reason (EN): After the first applied reliability change proved the governed lane end to end, the next applied slice needed a verification-first runtime policy that raises factual trust for RAG-backed insight generation while preserving the public `InsightResponse` shape and bounded provider cost.
  - Links:
    - `core/insight/philosophical_runtime.py`
    - `core/rag/orchestration.py`
    - `tests/test_philosophical_runtime.py`
    - `tests/test_rag_orchestration.py`
    - `tests/test_recursive_rag.py`
    - `tests/test_insight_rag_response_fields.py`
    - `docs/review/PR_1114_FIXED_MAPPING.md`
  - DoD:
    - Verification-first gating prefers accepted RAG-backed answers with `verification_rate >= 0.7`
    - Low-verification factual/deep outputs trigger at most one bounded rewrite before a conservative fallback
    - Recursive and non-recursive paths preserve the current response contract and deterministic reason codes
    - The applied runtime change is validated by deterministic local oracles and merged through normal human-reviewed PR governance

<a id="ledger-p1-creative-research-eval-lane"></a>
- [ ] P1: Creative research eval lane under governed experimentation epic
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (research moat, bounded discovery workflow)
  - Target PR: PR `#1106` -> PR `#1112` -> PR_TBD_CREATIVE_RESEARCH_INTERNAL_PILOT
  - Status: 🟡 In progress (PR `#1106` carries the docs-only protocol slice; PR `#1112` carries the offline eval harness/contract layer as a stacked offline-only follow-up)
  - Dependencies:
    - [P1: Governed agent experimentation lane (PR1-PR6 orchestration epic)](#ledger-p1-agent-experimentation-lane)
    - [P1: PR4 experiment promotion and telemetry integration](#ledger-p1-agent-experiment-promotion)
  - Reason (EN): PulsePlate needs one governed `creative_research` sub-lane for divergence -> convergence -> verification -> promotion cycles, but it must remain inside the existing experimentation umbrella instead of becoming a second orchestration constitution. The lane should strengthen the Research / Differentiation contour, stay human-gated, and avoid public runtime exposure in wave 1.
  - Links:
    - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
    - `docs/orchestration/CREATIVE_RESEARCH_SUBLANE_PROTOCOL.md`
    - `docs/orchestration/CREATIVE_RESEARCH_OFFLINE_EVAL_PROTOCOL.md`
    - `docs/orchestration/contracts/CREATIVE_RESEARCH_EVAL_CONTRACT.md`
    - `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
    - `docs/orchestration/AGENT_EXPERIMENT_PACKET_TEMPLATE.md`
    - `scripts/orchestration/creative_research_eval.py`
    - `scripts/orchestration/creative_research_eval_contract.py`
    - `tests/test_creative_research_eval.py`
    - `tests/test_creative_research_eval_contract.py`
    - `docs/review/PR_1112_FIXED_MAPPING.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
    - `docs/orchestration/CREATIVE_RESEARCH_INTERNAL_PILOT_CONTRACT.md`
    - `app/routers/creative_research_internal.py`
    - `app/services/creative_research_runtime.py`
    - `app/schemas/creative_research.py`
    - `core/creative_research.py`
    - `tests/test_creative_research_pilot_api.py`
  - DoD:
    - PR-A lands docs-only protocol and routing/evaluation/handoff visibility for `creative_research`
    - PR-B adds offline eval harness, deterministic judge contracts, negative controls, and no runtime integration
    - PR-C remains internal-only, feature-flagged, hidden from public OpenAPI, and introduces no new heavy LLM endpoint on the core path
    - The lane preserves no hidden memory, no autonomous merge, no immutable-oracle mutation, and quota-before-call for any future provider-backed pilot

<a id="ledger-p2-creative-research-domain-typing"></a>
- [ ] P2: Tighten creative research core domain typing
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1124`
  - Status: 🟢 In progress in PR `#1124`
  - Reason (EN): `core/creative_research.py` is the shared SoT for the creative
    research lane, but it still exposes `Any` and `dict[str, Any]` at validated
    boundaries. Tighten the domain contract with explicit typed structures
    without widening PR-C beyond the bounded internal pilot scope.
  - Links:
    - `core/creative_research.py`
    - `app/schemas/creative_research.py`
    - `docs/orchestration/CREATIVE_RESEARCH_INTERNAL_PILOT_CONTRACT.md`
    - `docs/review/PR_1118_FIXED_MAPPING.md`
    - `docs/review/PR_1124_FIXED_MAPPING.md`
  - DoD:
    - Replace `Any` at the public core creative-research validation boundary
      with `object` plus explicit typed domain structures
    - Keep app/schema adapters aligned with the typed core contract
    - Preserve deterministic creative-research eval and pilot tests

<a id="ledger-p2-pr1118-governance-closeout"></a>
- [x] P2: PR #1118 governance closeout for review-thread mapping and final merge-readiness pass
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1118`
  - Status: ✅ Completed in merged PR `#1118` on March 11, 2026
  - Reason (EN): PR `#1118` intentionally postpones final artifact closeout until
    the remaining review dispositions settle; the canonical mapping artifact,
    discussion-thread pass markers, and final merge-readiness / wait-window
    evidence still need one synchronized closeout pass.
  - Links:
    - `docs/review/PR_1118_FIXED_MAPPING.md`
    - `scripts/orchestration/review_mapping_artifact.py`
    - `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
  - DoD:
    - All remaining PR `#1118` review threads have explicit dispositions
    - The two `Discussion Thread Pass` checkboxes are checked in the canonical
      mapping artifact
    - Final merge-readiness / wait-window evidence is recorded before merge

<a id="ledger-p2-phase2-body-artifact-sync"></a>
- [ ] P2: Eliminate PR body and mapping artifact phase2 drift
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR_TBD_PHASE2_BODY_ARTIFACT_SYNC
  - Area: orchestration / CI governance
  - Reason: PR5 closeout exposed a hidden governance fragility: `check_pr_body_phase2_gates.py` requires both the canonical mapping artifact and the PR body mirror to carry checked discussion/mapping markers plus at least one mapping entry, which creates avoidable double-maintenance drift during late review cycles.
  - Links:
    - `scripts/ci/check_pr_body_phase2_gates.py`
    - `docs/review/PR_1102_FIXED_MAPPING.md`
    - `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`
  - DoD:
    - Phase2 body mirror is generated or validated from a single canonical source
    - Late review-cycle updates no longer require manual duplication of mapping lines
    - CI guidance explicitly distinguishes canonical SoT vs human-readable mirror

<a id="ledger-p2-clean-clone-dependency-parity"></a>
- [ ] P2: Restore deterministic clean-clone dependency parity for local verify
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR_TBD_CLEAN_CLONE_DEPENDENCY_PARITY
  - Area: tooling / developer-experience
  - Reason: Final PR5 local `make verify` failed in the clean clone because `.venv` was missing locked `opentelemetry-*` packages required by `tests/test_genai_tracing.py`, even though `requirements.txt` already declared them. This is an environment parity gap, not a code regression, but it weakens merge confidence.
  - Links:
    - `Makefile`
    - `requirements.txt`
    - `tests/test_genai_tracing.py`
    - `tests/test_genai_tracing_config.py`
  - DoD:
    - Fresh clean clones can run `make verify` after one documented bootstrap path with no missing locked dependencies
    - Local setup docs mention the canonical venv refresh command when lockfile drift is suspected
    - At least one deterministic check guards against silently incomplete clean-clone environments

<a id="ledger-p2-gh-checks-current-head-filter"></a>
- [ ] P2: Filter superseded GitHub check noise in merge triage
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR_TBD_GH_CHECKS_CURRENT_HEAD_FILTER
  - Area: orchestration / GitHub governance
  - Reason: PR5 merge triage repeatedly showed stale failed `test-pr` and `coverage-pr` lines from superseded runs in `gh pr checks`, even after the current head became `CLEAN`. This creates false negatives and slows final merge decisions.
  - Links:
    - `scripts/ci/check_pr_merge_readiness.py`
    - `RUNBOOK_AGENT.md`
  - DoD:
    - Repo guidance or helper tooling can distinguish current-head required checks from superseded historical failures
    - Merge triage output clearly labels stale runs as non-blocking when canonical readiness already passed
    - Final merge checklist references the filtered current-head view

<a id="ledger-p2-pr5-ledger-closeout-docs-only"></a>
- [x] P2: Normalize PR5 ledger closeout via docs-only follow-up PR
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR `#1120`
  - Area: orchestration / ledger governance
  - Reason: `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md` requires a docs-only follow-up PR when a merged PR closes a ledger item. PR5 closeout was captured during the mixed-scope PR6 kickoff sequence, so it needs a narrow docs-only normalization PR instead of widening PR6 further.
  - Links:
    - `docs/orchestration/PR_MERGE_WORKFLOW_MATRIX.md`
    - `docs/roadmap/BACKLOG_LEDGER.md`
    - `docs/review/PR_1102_FIXED_MAPPING.md`
  - Status: ✅ Implemented in PR `#1120` (this docs-only follow-up); canonical closeout takes effect on merge.
  - DoD:
    - A docs-only follow-up PR updates the PR5 ledger closeout in canonical form
    - The follow-up PR references PR `#1102` and this deferred remediation item
    - No runtime or tooling files are mixed into that normalization PR

- [ ] P2: First-class CV routing domain in orchestration graph
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR_TBD_CV_ROUTING_DOMAIN
  - Area: orchestration / routing
  - Reason: PR5 keeps `ml` as the graph-level domain for CV experiments. If future work needs `cv-agent` as graph-primary rather than advisory, `AGENT_ROUTING_GRAPH.md`, `AGENT_CAPABILITY_MATRIX.md`, `AGENT_CONTEXT_MAP.md`, and routing/tooling tests must be updated together.
  - Links:
    - `docs/orchestration/AGENT_ROUTING_GRAPH.md`
    - `.cursor/agents/cv-agent.md`
    - `docs/orchestration/CV_EXPERIMENTATION_PROTOCOL.md`
  - DoD:
    - Routing graph defines a canonical `cv` domain or explicit equivalent
    - Capability/context docs match the graph
    - Bootstrap/routing tests cover graph-primary CV routing deterministically

- [ ] P2: Canonical client ownership for future CV degrade UX
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR_TBD_CV_DEGRADE_UX_OWNERSHIP
  - Area: orchestration / ios / frontend
  - Reason: PR5 documents degrade states for future runtime/client work, but it intentionally does not invent a new canonical iOS/web execution owner. That ownership must be made explicit before any client-visible CV UX is implemented.
  - Links:
    - `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
    - `docs/orchestration/AGENT_CONTEXT_MAP.md`
    - `.cursor/agents/agent-coordinator.md`
  - DoD:
    - Future CV client work has an explicit canonical implementation owner
    - Routing and context docs no longer imply conflicting iOS/frontend ownership
    - Backlog item references the first runtime/client CV PR that consumes degrade states

<a id="ledger-p1-design-tooling-phase2-env-api"></a>
- [ ] P1: Phase 2 env/API automation for Notion, Airweave, and Penpot
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P1 (design-tooling scalability after governance baseline)
  - Target PR: TBD (post-governance automation stream)
  - Status: 📋 Planned
  - Reason (EN): Phase 1 establishes governed runbooks and source precedence for
    Figma, Notion, Airweave, and Penpot, but non-Figma tools remain
    `HITL/browser-first`. A separate phase is needed to design scoped env/API
    automation, session evidence, and security review without creating a second
    source of truth. (RU: Вторая фаза нужна для безопасной env/API-автоматизации
    Notion, Airweave и Penpot после фиксации governance-базиса.)
  - Links:
    - `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
    - `docs/runbooks/NOTION_STRUCTURED_MEMORY_GOVERNANCE.md`
    - `docs/runbooks/AIRWEAVE_RESEARCH_INGESTION_LANE.md`
    - `docs/runbooks/PENPOT_SECONDARY_DESIGN_LANE.md`
    - `docs/memory/kpp_knowledge_promotion_pipeline.md`
  - DoD:
    - Define scoped auth model for each tool (`browser-only` vs `env/API`)
    - Add evidence requirements for write operations and promotions
    - Confirm no secondary tool bypasses git SoT or Figma canonical mappings
    - Update coordinator/runbook docs with approved automation paths only

- [ ] P2: Rename legacy `vip_llm_monthly_usage` table to tier-neutral name
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


- [x] P2: CorpusNotIndexedError - wire up or remove
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (minor cleanup)
  - Target PR: PR #1010
  - Status: Done (merged in PR #1010)
  - Reason (EN): The dead exception export was removed and regression coverage landed in the merged Wave 4 closure PR.
  - Links:
    - `core/rag/contracts.py`
    - `core/rag/__init__.py`
    - `tests/test_rag_contract_surface.py`
    - PR #942 CodeRabbit comment (2868000574)
  - Evidence:
    - `core/rag/contracts.py:1` — contract surface no longer defines `CorpusNotIndexedError`.
    - `core/rag/__init__.py:1` — package surface no longer re-exports the dead symbol.
    - `tests/test_rag_contract_surface.py:10` — regression tests assert the dead export stays removed.
  - DoD:
    - [x] Remove the dead exception class/export and update regression tests

---

- [x] P2: Execution Wave 3-R2 — Consent + signed handoff contract
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #960 (`feat(restaurants): W3-R2 consent + signed handoff contract`)
  - Status: ✅ Merged (PR #960, 2026-03-04)
  - Reason: Partner access must be explicit, revocable, and auditable.
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md
    - app/routers/pro_restaurant_partner.py
    - app/schemas/restaurant_partner.py
    - tests/test_pro_restaurant_partner_api.py
  - DoD:
    - Consent/share issuance flow documented with expiry + revocation semantics
    - Fail-closed behavior documented for revoked/expired shares (`403/410`)
    - Audit fields fixed (`issuer`, `partner_id`, `issued_at`, `expires_at`, `revoked_at`)


- [x] P2: Multi-hop retrieval + query refinement (W1 core)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (AI / RAG)
  - Target PR: PR #973 (`feat/recursive-rag-w1-core`)
  - Status: ✅ Merged (PR #973, 2026-03-04)
  - Reason (EN): Recursive RAG W1 (core-only) is delivered behind feature flag with deterministic budgets and fail-safe fallback; advanced reasoning/refinement phases remain tracked separately in P1 recursive roadmap.
  - Links:
    - `docs/insights/RECURSIVE_METHODS_LLM_RAG.md`
    - `docs/contracts/RAG_CONTRACT.md` (budget)
  - DoD:
    - `retrieve_recursive_context_structured(...)` integrated with feature-flag routing
    - Budget constants and early-stop behavior enforced deterministically
    - Fallback to legacy path remains fail-safe on internal errors
    - `make verify` passes


- [x] P2: sources[] in Insight response (client-visible)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2 (API / RAG)
  - Target PR: PR #935
  - Status: ✅ Merged as part of PR #935 (2026-02-27)
  - Reason (EN): Expose RAG sources to client for transparency and EU AI Act traceability; requires RAG contract implementation first.
  - Links:
    - `docs/contracts/RAG_CONTRACT.md` (sect. 2)
    - `legacy_app.py` (InsightResponse)
  - DoD:
    - Insight response includes sources[] when rag_used=true; preview redacted; OpenAPI updated
    - `make verify` and `make openapi-check` pass


<a id="ledger-pr998-orch2-carryover"></a>
- [x] P2: Carry over PR #998 orchestration-2.0 review wave to PR #1000
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #1000 (`feat/agent-orchestration-2-0`)
  - Status: Done (carryover comments re-evaluated and dispositioned in merged PR #1000)
  - Area: orchestration / review governance / scope management
  - Finding Type: carryover after scope cleanup
  - Reason: PR #998 was force-cleaned back to the artifact-first governance scope. Cubic comments posted on 2026-03-06 against orchestration-runtime expansion files remain valid review input, but that code now lives in PR #1000 rather than PR #998.
  - Links:
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/998`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1000`
    - `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/998#pullrequestreview-3906532584`
    - `docs/review/PR_1000_FIXED_MAPPING.md`
  - DoD:
    - Carryover cubic comments from PR #998 are re-evaluated against PR #1000 scope
    - Relevant fixes or explicit dispositions are recorded on PR #1000
    - PR #998 remains limited to canonical Fixed Mapping SoT work

- [x] P2: Execution Wave 3-R1 — Partner API contract freeze (`menu -> partner`)
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #958 (`feat(restaurants): add PRO partner order contract (W3-R1)`)
  - Status: ✅ Merged (PR #958, 2026-03-03)
  - Reason: Freeze canonical v1 contract before deep runtime integration to prevent schema drift.
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md
    - app/routers/pro_restaurant_partner.py
    - app/schemas/restaurant_partner.py
  - Blockers:
    - Persistent storage + audit trail not implemented yet (in-memory seam for W3-R1 only)
    - Partner retrieval/confirmation hardening and export adapter waves pending (`W3-R3`, `W3-R4`)
  - DoD:
    - Non-breaking PRO endpoints contract documented and available under `/api/v1/pro/restaurants/partner/*`
    - State model and transition constraints documented (`draft -> pending_partner -> confirmed|rejected -> fulfilled|cancelled`)
    - Request/response schema examples and compatibility policy (additive-only for v1) documented


- [x] P2: Execution Wave 3-R3 — Partner retrieval + confirmation hardening
  - Owner: @katsiaryna_kavaleuskaya
  - Priority: P2
  - Target PR: PR #962 (`feat(restaurants): W3-R3 retrieval and confirmation hardening`)
  - Status: ✅ Merged (PR #962, 2026-03-04)
  - Reason: Deterministic partner retrieval and confirmation semantics must be hardened before onboarding.
  - Links:
    - docs/design/RESTAURANT_INTEGRATION_SPEC.md
    - docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md
    - app/routers/pro_restaurant_partner.py
    - tests/test_pro_restaurant_partner_api.py
    - tests/test_pro_restaurant_partner_openapi_contract.py
  - DoD:
    - Owner isolation for retrieval/confirm is deterministic (`403` on issuer mismatch)
    - `410 Gone` semantics are deterministic for expired handoff shares (including replay behavior)
    - Confirm idempotency contract is deterministic for replay/conflict (`client_event_id`)
    - OpenAPI partner contract is locked by tests (paths, response codes, schema refs, security)
    - Out-of-scope boundary remains enforced (no payment/delivery in this wave)


- [x] P2: Tooling — pre-flight auto-verification script
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR #966
  - Status: ✅ Merged (PR #966, 2026-03-04)
  - Priority: P2
  - Area: tooling / orchestration
  - Finding Type: automation
  - Reason: Pre-flight Checklist is manual; coordinator "mentally checks" docs. Risk of drift. Script is direct executor of canon.
  - Links:
    - `docs/orchestration/AGENT_CONTEXT_MAP.md`
    - `docs/orchestration/workflow.md`
    - `.cursor/agents/agent-coordinator.md`
    - `docs/plan/ORCHESTRATION_IMPROVEMENTS_PLAN_2026.md`
  - DoD:
    - Script verifies required context files present, repo hygiene (no tracked worktrees), prints PASS/FAIL
    - Failure mode explicit; does not block unrelated tasks (scoped to orchestration workflow)


### Other

- [x] PR-560 CI iOS stability (merged 2026-01-21)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-560
  - Status: ✅ Merged
  - Reason: iOS CI stability fixes (simulator selection, Xcode pinning)
  - Links:
    - docs/CONTEXT_HANDOFF_2026-01-21.md
  - DoD: ✅ Completed (iOS CI stable)


- [x] PR-563 Thin HTTP Adapter (iOS) — merged 2026-01-21
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-563
  - Status: ✅ Merged
  - Reason: unified thin transport layer for iOS client (no business logic)
  - Links:
    - docs/audit/PR_562_THIN_CLIENT_HTTP_ADAPTER_AUDIT_TEMPLATE.md
    - <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/563>
  - DoD: ✅ Completed (iOS HTTPClient/APIClient/BMIService implemented)


- [x] Auto-verification script (Pre-flight Checklist) — superseded by P2: Tooling — pre-flight auto-verification script
  - Owner: @katsiaryna_kavaleuskaya
  - Status: ✅ Superseded (consolidated into P2 entry above)
  - Reason: Same scope; consolidated with plan link in P2 entry.


- [x] PR-566 (Phase 2): Coordinator cleanup and deduplication — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-566
  - Status: ✅ Merged
  - Reason: Agent coordinator deduplication (removed capability duplication)
  - Links:
    - docs/audit/PR_566_COORDINATOR_CLEANUP_AUDIT.md
  - DoD: ✅ Completed (coordinator references agent files instead of duplicating)


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


- [x] PR-570 (Phase 3): Agent index + model selection rationale — merged
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-570
  - Status: ✅ Merged
  - Links:
    - docs/audit/PR_567_AGENT_INDEX_AUDIT.md
    - docs/agents/index.md


- [x] PR-561 Trivy suppression (CVE-2025-15281 glibc) (merged 2026-01-21)
  - Owner: @katsiaryna_kavaleuskaya
  - Target PR: PR-561
  - Status: ✅ Merged
  - Reason: Security suppression for unfixed upstream glibc CVE
  - Links:
    - docs/security/CVE-2025-15281-glibc.md
    - trivy/ignore-policy.rego
  - DoD: ✅ Completed (suppression with expiry date)


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



**Last updated:** 2026-03-08 (ledger reorder + truth audit)
**Maintainer:** @katsiaryna_kavaleuskaya
<!-- markdownlint-enable MD013 -->
