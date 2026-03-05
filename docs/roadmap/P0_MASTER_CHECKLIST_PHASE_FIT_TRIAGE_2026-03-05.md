# P0 Master Checklist Phase-Fit Triage (2026-03-05)

- Source snapshot: `docs/roadmap/PulsePlate_Master_Checklist_v1.0.md` and `PulsePlate_Master_Checklist.docx`
- Triage owner: `@katsiaryna_kavaleuskaya`
- Decision policy: map each checklist item to `Now`, `Next`, `Later`, or `Deferred` against current program order:
  1. P0 checklist alignment
  2. P0 payments RU/BY + iOS-first baseline
  3. P1 AI reliability waves
  4. P1 frontend/iOS parity

## Canonical Matrix

| # | Checklist Item | Phase | Backlog Mapping | Note |
|---|---|---|---|---|
| 1 | localStorage -> httpOnly cookie | Now | `PR-TBD-SESSION-COOKIE-HARDENING` | Security blocker before scale release |
| 2 | LLM fallback chain | Now | `PR-TBD-INSIGHT-FALLBACK-CHAIN` | VIP reliability/fail-safe |
| 3 | RAG input sanitizer | Now | `PR-TBD-RAG-INPUT-SANITIZER` | Prompt-injection risk |
| 4 | VIP echo mode alert | Now | `PR-TBD-INSIGHT-FALLBACK-CHAIN` | Add readiness/error visibility |
| 5 | iOS Keychain storage verification | Now | `PR-TBD-IOS-KEYCHAIN-CONFORMANCE` | Mandatory mobile secret storage control |
| 6 | Android Keystore storage verification | Deferred | `PR-TBD-ANDROID-KEYSTORE-CONFORMANCE` | Deferred until Android monetization wave |
| 7 | PRO/VIP route Depends audit | Now | `PR-TBD-PRO-VIP-DEPENDS-GUARD` | API access-control integrity |
| 8 | Apple StoreKit 2 products setup | Next | `PR-TBD-IOS-STOREKIT-PRODUCTS` | Operational setup after baseline contract |
| 9 | Google Play Billing setup | Deferred | `PR-TBD-GOOGLE-BILLING` | Not primary rail in current phase |
| 10 | Paddle web checkout | Later | `PR-TBD-PADDLE-WEB-CHECKOUT` | Global expansion rail |
| 11 | YooKassa RU/BY | Deferred | `Replaced by ERIP/SWIFT baseline` | Superseded by current RU/BY payment strategy |
| 12 | Unified `activate_subscription()` | Now | `PR-TBD-PAYMENTS-RUBY-IOS-BASELINE` | Canonical billing source model |
| 13 | RuStore billing | Later | `PR-TBD-RUSTORE-BILLING` | After Android monetization track opens |
| 14 | PostgreSQL migration | Next | `PR-TBD-POSTGRES-STAGING-CUTOVER` | Controlled infra cutover |
| 15 | Diet flags frontend/backend sync | Now | `PR-TBD-DIET-FLAGS-CONTRACT-SYNC` | Product correctness across clients |
| 16 | Semantic RAG upgrade | Later | existing P1/P2 RAG backlog wave | Depends on P1 reliability baseline |
| 17 | VIP core imports reliability check | Next | `PR-TBD-VIP-CORE-IMPORT-HEALTH` | Runtime reliability hardening |
| 18 | Legacy `/premium/*` cleanup | Next | existing namespace governance wave | Continue deprecation rollout |
| 19 | Enable `FEATURE_FOOD_SEARCH_SEMANTIC_ENABLED` | Later | food semantic rollout wave | Turn on after search validation window |
| 20 | WebSocket TokenVerifier integration | Next | `PR-TBD-WS-TOKEN-VERIFIER-HARDEN` | Keep with realtime hardening batch |
| 21 | iOS SubscriptionManager integration | Now | `PR-TBD-IOS-SUBSCRIPTION-MANAGER` | iOS primary monetization path |
| 22 | Apple receipt verification backend | Now | `PR-TBD-BILLING-APPLE-VERIFY` | Required for automated iOS billing |
| 23 | Android BillingManager | Deferred | `PR-TBD-ANDROID-BILLING-MANAGER` | Deferred by iOS-first strategy |
| 24 | Google purchase verification backend | Deferred | `PR-TBD-BILLING-GOOGLE-VERIFY` | Deferred by iOS-first strategy |
| 25 | iOS HealthKit integration | Later | `PR-TBD-IOS-HEALTHKIT` | Growth feature, not P0 blocker |
| 26 | Android Health Connect/Fit integration | Later | `PR-TBD-ANDROID-HEALTH-CONNECT` | Android later wave |
| 27 | Keep coverage gate >=97% | Now | already enforced canonical gates | Continuous hard gate |
| 28 | Billing endpoint tests | Now | `PR-TBD-PAYMENTS-RUBY-IOS-BASELINE` | Mandatory for payment baseline |
| 29 | Security workflow (Bandit/Safety) | Next | existing security CI track | Keep enforced for release waves |
| 30 | Nightly PostgreSQL integration tests | Next | existing nightly DB track | Required before DB cutover |
| 31 | App Store Connect account setup | Next | `PR-TBD-IOS-STORE-OPS` | Release operations work |
| 32 | Google Play Console setup | Deferred | `PR-TBD-GPLAY-STORE-OPS` | Deferred with Android monetization |
| 33 | Store screenshots + preview | Next | `PR-TBD-STORE-ASSETS` | Required before iOS release submission |
| 34 | ASO keywords | Next | `PR-TBD-ASO-KEYWORDS-W1` | Pre-release growth asset |
| 35 | Privacy Policy + Terms | Now | `PR-TBD-LEGAL-POLICY-PUBLISH` | Release/compliance blocker |
| 36 | ODbL compliance check | Next | existing ODbL compliance entry | Validate app-level attribution surface |
| 37 | Product Hunt launch | Later | `PR-TBD-GTM-PRODUCT-HUNT` | Post-release growth |
| 38 | SEO landing pages | Later | `PR-TBD-SEO-LANDING-PACK` | Post-release growth |
| 39 | TikTok/Reels content engine | Later | `PR-TBD-SOCIAL-CONTENT-ENGINE` | Post-release GTM |
| 40 | Soft paywall A/B tests | Later | `PR-TBD-SOFT-PAYWALL-AB` | After billing baseline stabilizes |
| 41 | YouTube long-form campaign | Later | `PR-TBD-YOUTUBE-GTM-W1` | Post-release GTM |

## Immediate Execution (Now Bucket)

1. Session and auth transport hardening (`#1`).
2. Insight reliability protection (`#2`, `#4`) and RAG input sanitization (`#3`).
3. Payment baseline contract for `ios_app_store`, `erip_qr`, `swift_manual` (`#12`, `#21`, `#22`, `#28`).
4. Access-control and product-contract correctness (`#5`, `#7`, `#15`).
5. Mandatory legal baseline (`#35`).

## Deviation Notes vs Original Checklist

1. `#11 YooKassa` is replaced by canonical RU/BY rails: `eRIP QR + SWIFT manual`.
2. Android monetization (`#9`, `#23`, `#24`, `#32`) is deferred by iOS-first revenue policy.
3. Growth and content block (`#37`-`#41`) stays later until quality and payment baseline are stabilized.

## Acceptance

- All checklist items `#1`-`#41` mapped to one phase bucket.
- Every `Now` item has explicit backlog target PR identifier.
- Superseded items are explicitly marked as replaced (not silently dropped).
