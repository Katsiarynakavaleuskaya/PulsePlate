# PulsePlate — P0/P1 Execution Document

Date: 2026-03-30
Status: operator execution map

## Summary

- Batch B is closed as a batch, but the paid contour is not fully release-ready.
- The active critical path is now: deploy/runtime closure -> backend monetization follow-through -> web truth -> legal/release shell -> App Store closeout -> AI hardening follow-through.
- Do not reopen B1-B4 baseline work. Use explicit follow-up items already open in the canonical ledger.

## Status update — 2026-04-03

- PR1 Postgres foundation is already merged; do not reopen it inside the authz closeout lane.
- PR2 deploy shell lane materially landed via `#1293`, with the extra CD env-token follow-up in `#1297`.
- PR3 activation + persistence truth merged as `#1296`; shadow runtime truth is removed from the active monetization critical path.
- PR4 is no longer pending implementation; that closeout merged as `#1298`.
- PR4 closeout landed as docs/authz packet `#1298`, and web entitlement truth hardening landed via `#1299`.
- Web progress no longer ships fabricated charts on the release path; that docs-only closeout merged as `#1308`.
- `docs/legal-policy-publish` already merged as `#1304`, and the current Wave 4 compliance closeout merged as `#1307`.
- The next active new Wave 4 lane is now `docs/ios-subscription-offers-governance`, followed by the remaining iOS/App Store modernization items.
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
2. `feat/eu-compliance-control-plane-followthrough` — Wave 4 closeout merged via `#1307`
3. `docs/ios-subscription-offers-governance` — next active new lane
4. `feat/ios-appstore-assets-rollout`
5. `feat/ios-appstore-semantic-validators`
6. `feat/apple-server-api-migration`

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
- status: closeout merged as `#1298`
- closes: `ledger-p0-billing-entitlement-routing`
- goal: backend entitlement truth for `/api/v1/pro/*` and `/api/v1/vip/*`; fail-closed startup contract; explicit RU/BY pre-entitlement rule
- policy: manual RU/BY billing entry routes stay transport-auth only, not entitlement surfaces

### 5. feat(frontend): move web premium truth to canonical backend/store state
- status: merged as `#1299`
- closes: `ledger-p0-web-entitlement-truth`
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
- status: Wave 4 closeout merged as `#1307`; any remaining program-level DSAR/public-surface work stays tracked in the ledger epic and is not the next active implementation lane
- closes: `ledger-p0-eu-compliance-control-plane-follow-through`
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
- closes together:
  - `ledger-p1-ios-appstore-assets-rollout`
  - `ledger-p1-pr1147-ios-appstore-asset-followups`
- goal: protected environments, upload workflow, deterministic screenshot contract, runbook

### 11. feat(ios-release-ops): semantic metadata/privacy validators
- closes: `ledger-p1-ios-appstore-semantic-validators`
- goal: block medical/promissory copy drift and privacy-package mismatches

### 12. feat(billing): migrate Apple verification to App Store Server API
- closes: `ledger-p1-apple-server-api-migration`
- goal: move off classic `verifyReceipt` while keeping downstream activation contract stable

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
