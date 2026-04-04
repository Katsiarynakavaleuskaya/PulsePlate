# PulsePlate — P0/P1 Execution Document

Date: 2026-03-30
Status: operator execution map

## Summary

- Batch B is closed as a batch, but the paid contour is not fully release-ready.
- The active critical path is now: deploy/runtime closure -> backend monetization follow-through -> web truth -> legal/release-shell follow-through -> AI hardening follow-through.
- Do not reopen B1-B4 baseline work. Use explicit follow-up items already open in the canonical ledger.

## Status update — 2026-04-03

- PR1 Postgres foundation is already merged; do not reopen it inside the authz closeout lane.
- PR2 deploy shell lane materially landed via `#1293`, with the extra CD env-token follow-up in `#1297`.
- PR3 activation + persistence truth merged as `#1296`; shadow runtime truth is removed from the active monetization critical path.
- PR4 closeout landed as docs/authz packet `#1298`, and web entitlement truth hardening landed via `#1299`, but `BACKLOG_LEDGER.md` remains the source of truth for whether `ledger-p0-billing-entitlement-routing` and `ledger-p0-web-entitlement-truth` are fully closed.
- Web progress no longer ships fabricated charts on the release path; that docs-only closeout merged as `#1308`.
- `docs/legal-policy-publish` already merged as `#1304`; the current Wave 4 compliance closeout slice merged as `#1307`, but the canonical P0 epic remains open until the ledger says otherwise.
- Wave 4 iOS/App Store release-ops closeout is already represented by merged `#1312`, `#1323`, and `#1324`; those merged slices do not change the rule that still-open P0 release-truth ledger items keep priority over P1 provider modernization.
- `feat/apple-server-api-migration` remains a prepared P1 provider-modernization follow-on and must not overtake still-open P0 release-truth items in the ledger, especially `ledger-p0-eu-compliance-control-plane-follow-through`.
- WebSocket foundation is no longer a stub-only surface; it is sufficiently wired for foundation scope, but it is not the current release priority.

## Source of truth order

1. `BACKLOG_LEDGER.md`
2. `DEPLOY_WEB_DIAGNOSIS_AND_FIX.md`
3. `PulsePlate_Master_Index_A-E.md`
4. `PulsePlate_Master_State_Document.md`
5. `OPENAPI_VISIBILITY_MATRIX.md` + `API_CANONICAL_MAP.md` + `API_COMPAT.md`
6. `PP_DESIGN_BRIDGE_REALIGNMENT_PACKET.md` + `FRONTEND_IOS_DESIGN_IMPLEMENTATION_ROADMAP.md`

## Decision log

- Do not treat Batch B as the next active lane.
- Do not reopen StoreKit baseline / thin SubscriptionManager baseline.
- Treat remaining monetization work as follow-up ledger items.
- Put infra/runtime closure before AI/design expansion.
- Treat Apple provider modernization as a prepared follow-on lane, not the immediate next lane, until remaining P0 release-truth follow-through is cleared.

## Execution order

### Wave 1 — Deploy / runtime closure
1. `infra/postgres-droplet-foundation`
2. `fix/deploy-web-spa-routing`
3. `docs/release-env-security-contract` only if it blocks deploy truth on staging/production

### Wave 2 — Backend monetization follow-through
1. `feat/billing-activation-and-persistence`
2. `feat/billing-entitlement-routing`

### Wave 3 — Web truth
1. `feat/web-entitlement-truth`
2. `docs/web-progress-contract-closeout`

### Wave 4 — Legal / release shell
1. `docs/legal-policy-publish` — merged via `#1304`
2. `feat/eu-compliance-control-plane-follow-through` — Wave 4 closeout merged via `#1307`; any remaining program-level follow-through stays tracked in the open ledger epic
3. `docs/ios-subscription-offers-governance` — merged via `#1312`
4. `feat/ios-appstore-assets-rollout` — merged via `#1323`
5. `feat/ios-appstore-semantic-validators` — merged via `#1324`
6. `feat/apple-server-api-migration` — prepared follow-on only after remaining P0 release-truth follow-through is cleared

### Wave 5 — API / contract truth
1. `chore/openapi-runtime-sync`
2. `feat/openapi-decoupling-split`

### Wave 6 — AI follow-through
1. `feat/insight-fallback-chain`
2. `feat/rag-hardening-followthrough`
3. `docs/ai-bounded-context-packet`
4. `feat/ai-bounded-context-extraction`
5. `feat/llm-reliability-security-gates`

### Wave 7 — Design bridge operationalization
1. `docs/design-agent-runtime-realignment`
2. `feat/design-bridge-preflight-and-capture`
3. `feat/design-bridge-first-parity-pack`

## PR map

### 1. infra(postgres): promote self-hosted Postgres to canonical Droplet foundation
- status: merged; keep out of PR4 scope
- closes: `ledger-p0-self-hosted-postgres-droplet-foundation`
- goal: remove optional/profile-gated posture, require `DATABASE_URL`, add health-gated dependency, backup/restore scripts, runbook
- do not include: billing, pgvector, MinIO, search, analytics

### 2. fix(deploy): restore SPA routing and production web shell
- status: materially landed via `#1293`; CD env-token follow-up landed via `#1297`
- closes: deploy blocker from `DEPLOY_WEB_DIAGNOSIS_AND_FIX.md`
- goal: Caddy SPA fallback, API proxy split, deep-route 200s, diagnose script, artifact path truth
- do not include: visual polish, progress data refactor, legal copy changes

### 3. feat(billing): activation + subscription persistence follow-through
- status: merged as `#1296`
- closes together:
  - `ledger-p0-billing-activation-service`
  - `ledger-p0-billing-subscription-persistence`
- goal: consume Apple verify contract, persist canonical subscription state, idempotent activation
- do not include: entitlement routing, iOS UI, App Store migration

### 4. feat(authz): enforce entitlement-backed routing after billing activation
- status: sequencing/closeout packet landed as `#1298`, but canonical closure still follows `BACKLOG_LEDGER.md`
- ledger note: `ledger-p0-billing-entitlement-routing` remains the deciding source of truth until explicitly closed there
- goal: backend entitlement truth for `/api/v1/pro/*` and `/api/v1/vip/*`; fail-closed startup contract; explicit RU/BY pre-entitlement rule
- policy: manual RU/BY billing entry routes stay transport-auth only, not entitlement surfaces

### 5. feat(frontend): move web premium truth to canonical backend/store state
- status: sequencing/hardening slice landed as `#1299`, but canonical closure still follows `BACKLOG_LEDGER.md`
- ledger note: `ledger-p0-web-entitlement-truth` remains the deciding source of truth until explicitly closed there
- goal: remove local premium source of truth; dev-only gate mock purchase/restore
- do not include: backend subscription redesign

### 6. docs(frontend): close web progress contract drift
- status: docs-only closeout lane after shipped runtime hardening
- closes: `ledger-p0-web-progress-contract`
- goal: reconcile docs to the shipped web truth: no fabricated chart values in release path and an explicit trusted empty state until real data exists
- do not include: backend progress API, chart-history implementation, or new frontend runtime data contracts

### 7. docs(release): publish legal policy paths and align client links
- status: merged as `#1304`
- closes: `ledger-p0-legal-policy-publish`
- goal: canonical privacy/terms paths live in repo and are linked from web/iOS

### 8. feat(compliance): EU-first compliance control plane follow-through
- status: Wave 4 closeout slice merged as `#1307`, but the canonical P0 epic remains open for program-level DSAR/public-surface and regulated-lane follow-through until the ledger says otherwise
- ledger note: `ledger-p0-eu-compliance-control-plane-follow-through` remains the deciding source of truth until explicitly closed there
- goal: keep `/privacy`, docs/legal, and compliance runtime synchronized for AI/health surfaces

### 9. docs/ios: subscription offers governance and StoreKit-truth pricing contract
- status: merged as `#1312`
- closes: `ledger-p1-app-store-subscription-offers-governance`
- goal: UI pricing/trial/eligibility copy must come from StoreKit/App Store truth
- canon: `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md` is the only SoT for
  App Store offers governance and StoreKit-truth pricing / trial / eligibility
  copy; roadmap consumers stay pointer-only
- deferred follow-ups:
  - `ledger-p1-ios-appstore-assets-rollout`
  - `ledger-p1-ios-appstore-semantic-validators`
  - `ledger-p1-apple-server-api-migration`

### 10. feat(ios-release-ops): protected App Store asset rollout
- status: merged as `#1323`
- closes together:
  - `ledger-p1-ios-appstore-assets-rollout`
  - `ledger-p1-pr1147-ios-appstore-asset-followups`
- goal: protected environments, upload workflow, deterministic screenshot contract, runbook

### 11. feat(ios-release-ops): semantic metadata/privacy validators
- status: merged as `#1324`
- closes: `ledger-p1-ios-appstore-semantic-validators`
- goal: block medical/promissory copy drift and privacy-package mismatches

### 12. feat(billing): migrate Apple verification to App Store Server API
- status: prepared follow-on only; do not open this lane ahead of still-open P0 release-truth work
- closes: `ledger-p1-apple-server-api-migration`
- canonical contract anchor: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-apple-server-api-migration` owns the full precondition, wire-compatibility, and temporary-fallback list for this lane; this execution document keeps only the sequencing pointer
- preconditions:
  - `ledger-p0-billing-entitlement-routing` is closed in the canonical ledger
  - `ledger-p0-web-entitlement-truth` is closed in the canonical ledger
  - release-shell / compliance follow-through no longer blocks release truth; map this to still-open P0 items, especially `ledger-p0-eu-compliance-control-plane-follow-through`, not by reopening `ledger-p0-legal-policy-publish`
  - no newly open P0 release-truth blocker is allowed to be overtaken unless an explicit decision log says otherwise
- goal: move off classic `verifyReceipt` while keeping downstream activation contract stable and preserving the public/iOS transport contract
- implementation note: deriving the App Store Server API identifier from the existing server-side receipt path is a feasibility checkpoint inside the lane; if it is not reliable, keep the legacy path as an explicit temporary fallback (owner: billing/provider lane owner; review date: 2026-07-03; exit via `ledger-p1-apple-server-api-migration` DoD closure) and do not force an iOS transport change in the same PR

### 13. chore(contracts): public OpenAPI/runtime/docs sync
- goal: keep public schema restricted to bmi/pro/vip, mark premium as compat-only, regenerate FE artifacts

### 14. feat(openapi): split backend schema generation from FE type generation
- closes: `ledger-p1-openapi-decoupling-split`

### 15. feat(ai-runtime): insight fallback chain and readiness visibility
- closes: `ledger-p0-insight-fallback-chain`

### 16. feat(rag): vector query hardening + confidence recomputation
- closes/reduces:
  - `vector_rag SQL assembly refactor`
  - RAG follow-through packet scope

### 17. docs(architecture): AI bounded-context packet
- prepares, but does not close: `ledger-p1-ai-bounded-context-extraction`

### 18. feat(ai-runtime): extract AI runtime into dedicated bounded context
- closes: `ledger-p1-ai-bounded-context-extraction`

### 19. feat(ai-quality): CI gates for retrieval, faithfulness, prompt-injection, privacy
- closes: `ledger-p1-llm-reliability-security-gates`

### 20. docs/design): design-agent runtime realignment bridge
- goal: repo-first design bridge contract, no runtime mutations, Storybook-first web review, iOS simulator verifier path

### 21. feat(design-ops): bridge preflight + screenshot capture + first parity pack
- goal: make design bridge operational evidence pipeline, not principle-only documentation

## What is already done and must not be reopened

- B1 baseline runtime merged in PR #1182
- StoreKit contract baseline merged in PR #1172
- Apple verify -> activation normalization merged in PR #1185
- B3 operational/setup close-out merged in PR #1189
- B4 thin-client SubscriptionManager flow merged in PR #1207
- iOS Keychain conformance merged in PR #1179

## Non-goals

- No new AI surface expansion before Waves 1–4 are stable
- No GTM/brand work before runtime truth is stable
- No design-tool automation that mutates runtime code directly
- No reopening `/api/v1/premium/*` as product source of truth

## Exit criteria for release-ready shell

Release-ready shell is not achieved until all of the following are true:
- production web serves SPA correctly on deep routes
- Postgres is canonical prod DB on Droplet
- activation + persistence + entitlement routing are server-side truth
- web premium state and progress state are non-fabricated
- legal policy paths are published and linked by clients
- App Store pricing/metadata/assets path is operationally governed
- fallback/echo mode is explicit in readiness state
