# iOS StoreKit Products Contract

## Purpose

This document is the canonical repository-owned source of truth for iOS
StoreKit subscription products.

The baseline defined here is already established on `main`; follow-up docs,
runtime, and release work must extend this contract rather than redefine the
canonical product IDs.

It defines:

- the exact StoreKit / App Store Connect `product_id` values allowed in runtime,
- the canonical App Store subscription offer surfaces governed by the same
  StoreKit / App Store truth,
- the backend entitlement tier mapping associated with each product,
- the setup baseline for App Store Connect, sandbox, and TestFlight checks,
- the validation rules that prevent client-side drift,
- the copy contract for price / trial duration / eligibility messaging.

## Definition: StoreKit / App Store truth

For this contract, `StoreKit / App Store truth` means the currently effective
subscription product and offer information exposed by Apple's App Store Connect
configuration and the corresponding StoreKit runtime surface available to the
app for the current storefront, region, and account context.

In-scope truth sources:

- canonical product and offer configuration maintained in App Store Connect
- StoreKit-returned product, subscription, and offer fields visible to runtime
- storefront- or region-specific availability and pricing exposed by that live
  Apple surface

Out-of-scope substitutes:

- manually authored UI copy
- cached or stale screenshots used as pricing evidence
- product-marketing text that asserts price, trial, or eligibility without
  current StoreKit / App Store confirmation

## Canonical products

| product_id | tier | billing_interval | product_family | status | notes |
| --- | --- | --- | --- | --- | --- |
| `com.pulseplate.premium.monthly` | `pro` | `monthly` | `premium_subscription` | `active` | Canonical monthly StoreKit subscription ID |
| `com.pulseplate.premium.yearly` | `pro` | `yearly` | `premium_subscription` | `active` | Canonical yearly StoreKit subscription ID |

## Runtime rules

1. iOS runtime may request only the canonical `product_id` values listed in
   this contract.
2. Product IDs must not be duplicated as ad hoc inline strings in screens,
   services, or routers; runtime must read them from the canonical code catalog.
3. `product_id` is a StoreKit / App Store Connect identifier, not backend tier
   vocabulary.
4. Backend entitlement `tier` mapping comes from catalog metadata, never from
   string parsing of `product_id`. The fact that a `product_id` contains the
   word `premium` must not be used as business logic.
5. Paywall pricing, trial duration, and eligibility copy must not be treated as
   runtime truth. Runtime displays StoreKit-returned product fields only.
6. If StoreKit returns zero canonical products, paywall must fail closed and
   show an unavailable state.
7. If StoreKit returns a subset of canonical products, paywall may render only
   that approved subset and must not invent placeholders or fallback plans.
8. Unknown StoreKit products must be ignored by runtime.

## App Store subscription offers governance

This document is also the canonical repository-owned source of truth for the
subscription-offer surfaces tied to the canonical StoreKit catalog.

Governed offer surfaces:

- introductory offers
- offer codes
- promotional offers
- win-back pricing

Governance rules:

1. These offer surfaces are governed by App Store Connect configuration plus
   StoreKit runtime truth; they are not governed by ad hoc marketing copy.
2. UI and release copy must not hardcode subscription price, trial duration, or
   eligibility assertions outside StoreKit / App Store truth.
3. Runtime and release-facing copy may only describe an offer when the current
   StoreKit / App Store surface supports that description.
4. Ownership boundary: this contract owns StoreKit/App Store offers governance;
   payments contracts own receipt/activation routing, and asset/release lanes
   own screenshots, metadata packaging, and submission execution.
5. Future App Store submission, TestFlight, and billing follow-through docs must
   link back to this contract instead of redefining offer governance elsewhere.
6. Consumer docs may summarize this governance briefly, but they must stay in
   pointer mode and must not become a competing canon for price, trial, or
   eligibility truth.

## Copy fallback rules

When live StoreKit / App Store truth is available:

1. UI and release copy must reflect that truth and must not contradict it.
2. Price, trial duration, and eligibility messaging must be derived from the
   live StoreKit / App Store surface rather than manually asserted text.

When live StoreKit / App Store truth is unavailable:

1. Only non-assertive fallback wording is allowed.
2. Approved examples:
   - `See the App Store for current pricing`
   - `Trial availability may vary`
   - `Eligibility is determined by Apple / the App Store`
3. Localized currencies, regional offer differences, and country-specific
   availability must not be restated as manual assertions when live truth is
   unavailable; those surfaces must defer to the App Store.
4. Forbidden claims while live truth is unavailable:
   - numeric price claims
   - exact trial-length claims
   - definite eligibility claims

## Consumer-doc pointer mode

The following documents are consumers of this contract and must stay in pointer
mode for App Store offers / pricing copy policy:

- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`
- `docs/MOBILE_API_MIGRATION_GUIDE.md`
- `docs/roadmap/IOS_BACKEND_REALIZATION_ROADMAP.md`
- `docs/roadmap/PulsePlate_P0_P1_Execution_Document_2026-03-30.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

Pointer mode means:

1. They may reference this contract and summarize scope in one or two lines.
2. They must not redefine canonical pricing, trial-duration, eligibility, or
   offer-governance rules.
3. If StoreKit / App Store truth is unavailable, they must defer to the same
   non-assertive fallback wording policy defined here.
4. Follow-up release lanes must remain explicit and separate rather than being
   folded back into this governance contract.

## Setup baseline

**Baseline inputs only:** this section records the fixed App Store Connect,
sandbox, TestFlight, and runtime-validation prerequisites that belong to the
StoreKit baseline already merged on `main`. It is not the live step-by-step
release checklist.

**Single source of truth for release follow-through:** the actionable
operational/release checklist lives in `## Operational release checklist`
below. Future TestFlight / App Store submission work must extend that checklist
instead of creating a parallel setup document.

### App Store Connect baseline

- Create subscription products in App Store Connect under the PulsePlate iOS
  app record.
- Use the exact canonical IDs listed in this contract.
- Keep product group / family aligned with `premium_subscription`.
- Do not create alternate runtime product IDs without updating this document and
  the matching Swift catalog in the same PR.

### Sandbox / TestFlight baseline prerequisites

- StoreKit products must be visible in the current App Store Connect
  configuration.
- The current build must be signed with the intended bundle identifier.
- Sandbox test accounts must be available before end-to-end purchase testing.
- TestFlight / sandbox runs must verify that runtime loads only the canonical
  IDs from this contract.

### Runtime verification invariants

- Launch the paywall and confirm runtime requests only canonical IDs.
- Confirm StoreKit returns the expected monthly/yearly plans or a valid subset.
- Confirm empty catalog shows an unavailable state instead of placeholder plans.
- Confirm unknown/unapproved IDs are not rendered.

## Operational release checklist

### App Store Connect truth

- Confirm the live App Store Connect record still contains only the canonical
  product IDs from this contract.
- Confirm the subscription group / family still aligns with
  `premium_subscription`.
- Confirm no alternate product IDs, hidden duplicates, or deprecated runtime
  products have been reintroduced outside this contract.

### Sandbox / TestFlight readiness

- Confirm sandbox test accounts are available before purchase-flow validation.
- Confirm the intended build/bundle identifier can load the canonical StoreKit
  catalog in sandbox/TestFlight.
- Confirm the monthly/yearly products load as the expected approved subset and
  that empty/unknown product paths still fail closed.

### Repo sync requirements

- `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md` remains aligned with
  `ios/PulsePlate/Models/StoreKitProductCatalog.swift`.
- `docs/IOS_API_INTEGRATION.md` points future operational/setup work back to
  this checklist instead of duplicating StoreKit setup truth elsewhere.
- `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md`,
  `docs/MOBILE_API_MIGRATION_GUIDE.md`, and
  `docs/roadmap/IOS_BACKEND_REALIZATION_ROADMAP.md` must treat this file as the
  canonical offers-governance source for price / trial / eligibility copy.
- Batch-B planning docs (`docs/roadmap/BACKLOG_LEDGER.md`,
  `docs/roadmap/PulsePlate_Master_Index_A-E.md`) treat the baseline as closed
  and point future release/setup work to this contract.

### Future release handoff

- Any future App Store / TestFlight submission lane may reference this
  checklist, but must not redefine canonical product IDs or create a competing
  StoreKit setup source of truth.

## Validation checklist

- `docs/contracts/IOS_STOREKIT_PRODUCTS_CONTRACT.md` and
  `ios/PulsePlate/Models/StoreKitProductCatalog.swift` must contain the same
  canonical product IDs.
- Runtime tests must prove catalog ordering and unknown-product filtering.
- Thin-client guards must prevent hardcoded runtime product IDs outside the
  canonical catalog file.

## Merge gate

Do not merge a PR that changes this contract until the exact canonical product
IDs are re-verified against App Store Connect.

## Non-goals

This contract does not govern:

- backend entitlement truth,
- receipt verification or activation routing,
- Keychain or mobile secret storage,
- App Store screenshots, metadata, or asset rollout,
- semantic App Store metadata/privacy validators,
- protected ASC environment activation,
- the actual submission/release decision for a future App Store build,
- StoreKitManager / SubscriptionManager internal implementation details beyond
  the runtime invariants defined in this contract,
- backend billing changes, or
- OpenAPI / API contract changes.
