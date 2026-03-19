# iOS StoreKit Products Contract

## Purpose

This document is the canonical repository-owned source of truth for iOS
StoreKit subscription products.

The baseline defined here is already established on `main`; follow-up docs,
runtime, and release work must extend this contract rather than redefine the
canonical product IDs.

It defines:

- the exact StoreKit / App Store Connect `product_id` values allowed in runtime,
- the backend entitlement tier mapping associated with each product,
- the setup baseline for App Store Connect, sandbox, and TestFlight checks,
- the validation rules that prevent client-side drift.

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
- pricing / trial / eligibility governance,
- App Store screenshots, metadata, or asset rollout,
- the actual submission/release decision for a future App Store build.
