# iOS StoreKit Products Contract

## Purpose

This document is the canonical repository-owned source of truth for iOS
StoreKit subscription products.

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

### App Store Connect

- Create subscription products in App Store Connect under the PulsePlate iOS
  app record.
- Use the exact canonical IDs listed in this contract.
- Keep product group / family aligned with `premium_subscription`.
- Do not create alternate runtime product IDs without updating this document and
  the matching Swift catalog in the same PR.

### Sandbox / TestFlight prerequisites

- StoreKit products must be visible in the current App Store Connect
  configuration.
- The current build must be signed with the intended bundle identifier.
- Sandbox test accounts must be available before end-to-end purchase testing.
- TestFlight / sandbox runs must verify that runtime loads only the canonical
  IDs from this contract.

### Runtime verification checklist

- Launch the paywall and confirm runtime requests only canonical IDs.
- Confirm StoreKit returns the expected monthly/yearly plans or a valid subset.
- Confirm empty catalog shows an unavailable state instead of placeholder plans.
- Confirm unknown/unapproved IDs are not rendered.

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
- App Store screenshots, metadata, or asset rollout.
