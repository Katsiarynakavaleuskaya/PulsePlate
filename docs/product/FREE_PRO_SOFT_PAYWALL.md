# Public Web Information Boundary (Compatibility Pointer)

**Status:** Compatibility filename retained for existing links. The current public-Web
contract is `docs/contracts/soft_paywall.md`.

**Last updated:** 2026-08-29

## Current public Web contract

The PulsePlate website is a free information and wellness-tool surface. Its
current user-facing propositions are:

- `This website is free to use.`
- `We’re designing more advanced FitChef features for PulsePlate on Apple devices.`
- `Purchases are not offered on this website.`
- `We’ll add a verified App Store link when public availability is confirmed.`

The only actions offered by this boundary are:

- `Try the free BMI calculator` → `/bmi`
- `Learn about PulsePlate for Apple devices` → `/marketing`
- `Not now` → dismiss the information surface

This copy does not claim public availability on a particular Apple device,
App Store availability, price, trial, eligibility, download readiness, or an
external Store URL.

## Canonical sources

- Public-Web hook and route semantics: `docs/contracts/soft_paywall.md`
- Product-tier and backend entitlement semantics: `docs/contracts/PRODUCT_TIER_MAP.md`
- Runtime localized Web copy: `appleProduct.*` in
  `frontend/src/locales/en.json`, `frontend/src/locales/ru.json`, and
  `frontend/src/locales/es.json`
- Backend compatibility availability fact: `availability.pro_available`

## Compatibility data boundary

Backend compatibility fields such as `message`, `target`, `limitations`, and
`next_step` may describe an API response, but they cannot author public-Web
copy, choose a Web action, infer entitlement, or open a paid destination.
`availability.pro_available` remains a backend compatibility fact; it is not
proof that a Web purchase, subscription, upgrade, trial, restore, checkout, or
entitlement-acquisition flow exists.

Any future Web monetization or full product parity requires a separate external
product, legal, and architecture admission. This compatibility pointer grants
no such authority.
