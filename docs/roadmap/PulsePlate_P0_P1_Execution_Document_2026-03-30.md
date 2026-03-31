# PulsePlate — P0/P1 Execution Document

Date: 2026-03-30
Status: operator execution map

## Summary

- Batch B is closed as a batch, but the paid contour is not fully release-ready.
- The active critical path is now: deploy/runtime closure -> backend monetization follow-through -> web truth -> legal/release shell -> App Store closeout -> AI hardening follow-through.
- Do not reopen B1-B4 baseline work. Use explicit follow-up items already open in the canonical ledger.

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
4. `feat/billing-activation-and-persistence`
5. `feat/billing-entitlement-routing`

### Wave 3 — Web truth
6. `feat/web-entitlement-truth`
7. `feat/web-progress-contract`

### Wave 4 — Legal / release shell
8. `docs/legal-policy-publish`
9. `feat/eu-compliance-control-plane-followthrough`
10. `docs/ios-subscription-offers-governance`
11. `feat/ios-appstore-assets-rollout`
12. `feat/ios-appstore-semantic-validators`
13. `feat/apple-server-api-migration`

### Wave 5 — API / contract truth
14. `chore/openapi-runtime-sync`
15. `feat/openapi-decoupling-split`

### Wave 6 — AI follow-through
16. `feat/insight-fallback-chain`
17. `feat/rag-hardening-followthrough`
18. `docs/ai-bounded-context-packet`
19. `feat/ai-bounded-context-extraction`
20. `feat/llm-reliability-security-gates`

### Wave 7 — Design bridge operationalization
21. `docs/design-agent-runtime-realignment`
22. `feat/design-bridge-preflight-and-capture`
23. `feat/design-bridge-first-parity-pack`

## PR map

### 1. infra(postgres): promote self-hosted Postgres to canonical Droplet foundation
- closes: `ledger-p0-self-hosted-postgres-droplet-foundation`
- goal: remove optional/profile-gated posture, require `DATABASE_URL`, add health-gated dependency, backup/restore scripts, runbook
- do not include: billing, pgvector, MinIO, search, analytics

### 2. fix(deploy): restore SPA routing and production web shell
- closes: deploy blocker from `DEPLOY_WEB_DIAGNOSIS_AND_FIX.md`
- goal: Caddy SPA fallback, API proxy split, deep-route 200s, diagnose script, artifact path truth
- do not include: visual polish, progress data refactor, legal copy changes

### 3. feat(billing): activation + subscription persistence follow-through
- closes together:
  - `ledger-p0-billing-activation-service`
  - `ledger-p0-billing-subscription-persistence`
- goal: consume Apple verify contract, persist canonical subscription state, idempotent activation
- do not include: entitlement routing, iOS UI, App Store migration

### 4. feat(authz): enforce entitlement-backed routing after billing activation
- closes: `ledger-p0-billing-entitlement-routing`
- goal: backend entitlement truth for `/api/v1/pro/*` and `/api/v1/vip/*`; fail-closed startup contract; explicit RU/BY pre-entitlement rule
- policy: manual RU/BY billing entry routes stay transport-auth only, not entitlement surfaces

### 5. feat(frontend): move web premium truth to canonical backend/store state
- closes: `ledger-p0-web-entitlement-truth`
- goal: remove local premium source of truth; dev-only gate mock purchase/restore
- do not include: backend subscription redesign

### 6. feat(frontend): replace demo-grade progress data with backend/empty-state truth
- closes: `ledger-p0-web-progress-contract`
- goal: no fabricated chart values in release path

### 7. docs(release): publish legal policy paths and align client links
- closes: `ledger-p0-legal-policy-publish`
- goal: canonical privacy/terms paths live in repo and are linked from web/iOS

### 8. feat(compliance): EU-first compliance control plane follow-through
- closes: `ledger-p0-eu-compliance-control-plane-follow-through`
- goal: keep `/privacy`, docs/legal, and compliance runtime synchronized for AI/health surfaces

### 9. docs/ios: subscription offers governance and StoreKit-truth pricing contract
- closes: `ledger-p1-app-store-subscription-offers-governance`
- goal: UI pricing/trial/eligibility copy must come from StoreKit/App Store truth

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
