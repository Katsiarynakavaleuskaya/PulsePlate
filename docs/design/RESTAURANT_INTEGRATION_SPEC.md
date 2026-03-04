# Restaurant/Chef Integration Specification

**Status:** Vision / Research (P2)
**Date:** 2026-01-28
**Owner:** @katsiaryna_kavaleuskaya

---

## Overview

**Concept:** Restaurants and individual chefs accept menus from our products (weekly plan, recipes, constraints) and cook food for users. Separate product block (not coaching, not social network); technically relies on plan export and partner contract.

**English summary:** Partners (restaurants/chefs) receive structured menu packages from PulsePlate (weekly plan, recipes, dietary constraints) and prepare meals for users. Requires export format, sharing/consent mechanism, and documented partner contract schema.

---

## Technical Prerequisites in Our Program

| Requirement | Purpose | What Exists / What to Add |
| ----------- | ------- | ------------------------- |
| **Structured menu export** | Machine-readable "menu package" for partner: days, meals, dishes, portions, constraints. | Exists: VIP weekly plan (`vip.py`, `premium_week.py`), recipes (`recipes`, `recipe_synth`), PDF/other export (`plan_export.py`, `shoplist_export.py`). Add: **"menu for partner" format** (JSON/PDF): week by days, dish list, ingredients, portions, diet/allergen tags. |
| **Dietary constraints and allergens** | Partner must see: VEG/KETO/GF, no nuts, no gluten, etc. | Exists: `core/dietary_constraints.py` (DIET_FLAGS), constraints in menus/recipes. Add: **unified export of constraints and allergens** in menu contract (fields in export schema for partner). |
| **Consent and sharing** | User explicitly "sends menu to restaurant X" or "generates link for chef". | None. Add: **sharing mechanism** — either signed link with expiry (signed URL, like export/sign), or **Partner API** (partner by key requests user plan by consent token). Plus audit: who, when, to whom gave plan. |
| **Partner contract schema** | Documented format: what restaurant/chef receives (fields, examples). | None. Add: **"Menu for partner" schema** (OpenAPI/JSON Schema): dates, meals, dish name, recipe/ingredients, portions, dietary_tags, allergens, optionally calories/macros. Stable contract = foundation for integration. |
| **Partner identification (optional)** | Directory of restaurants/chefs, choice "send menu to restaurant X". | None. Long-term: **partner directory** (name, cuisine, delivery zone, API or link acceptance). Not blocker for first scenario "menu link". |
| **Order/payment/delivery** | If full cycle "ordered in app — delivered" needed. | Out of current scope. This is partner product (aggregator/marketplace). Our program provides only **menu and contract**; order and fulfillment — on partner side or separate service. |

---

## Minimal First Step in Program

1. **Export format "menu for partner"** (JSON + optionally PDF) based on existing weekly plan + recipes + dietary_constraints.
2. **Sharing mechanism:** Signed link with expiry (reuse idea from export/sign) or separate endpoint "generate partner link" with consent.
3. **Documented contract schema** (what's in JSON, which fields required) for restaurants/chefs.

## Contract-First Decomposition (W3-R1..W3-R4)

Naming note: `W3-R*` is a dedicated restaurant integration sub-track and does not change historical
Food DB Wave 3 items (`W3-A..W3-E`).

| Wave | Scope | DoD |
| ---- | ----- | --- |
| **W3-R1** | Contract freeze (OpenAPI/JSON contract + examples for partner menu package) | Contract and required fields are frozen for v1, additive-only compatibility rule documented. |
| **W3-R2** | Consent + share issuance (signed link/token with expiry) | Expiry + revocation semantics documented; audit fields defined (`issuer`, `partner_id`, `issued_at`, `expires_at`, `revoked_at`). |
| **W3-R3** | Partner retrieval contract | Deterministic success/error contract documented (`200/401/403/404/410/429`), no payment/delivery scope creep. |
| **W3-R4** | Export adapter + deterministic contract tests | Mapping from weekly plan/recipes/constraints to partner payload documented; deterministic test matrix is mandatory gate. |

## Current Contract Surface (W3-R1 baseline)

Canonical non-breaking PRO endpoints:

- `POST /api/v1/pro/restaurants/partner/orders/preview`
- `POST /api/v1/pro/restaurants/partner/orders`
- `GET /api/v1/pro/restaurants/partner/orders/{order_id}`
- `POST /api/v1/pro/restaurants/partner/orders/{order_id}/confirm`
- Evidence: `app/routers/pro_restaurant_partner.py:30`, `app/routers/pro_restaurant_partner.py:40`, `app/routers/pro_restaurant_partner.py:80`, `app/routers/pro_restaurant_partner.py:106`

Status model for partner orders:

`draft -> pending_partner -> confirmed | rejected -> fulfilled | cancelled`
- Evidence: `app/schemas/restaurant_partner.py:27`

Current implementation baseline (contract-first):

- Server computes totals (`subtotal`, `fees`, `total`) and does not trust client totals.
- Evidence: `app/services/restaurant_partner_orders.py:61`
- Idempotency via `client_event_id` for create/confirm paths.
- Evidence: `app/services/restaurant_partner_orders.py:85`, `app/services/restaurant_partner_orders.py:155`
- `confirm` is fail-closed for invalid transitions.
- Evidence: `app/services/restaurant_partner_orders.py:195`, `app/routers/pro_restaurant_partner.py:132`
- Legacy `/api/v1/restaurants/*` remains backward-compatible and is not changed by this contract track.
- Evidence: `app/routers/restaurants.py:25`

## W3-R2 Contract Surface (consent + signed handoff)

Canonical non-breaking PRO endpoints (contract-first seam):

- `POST /api/v1/pro/restaurants/partner/orders/{order_id}/handoff/shares`
  - `201` issued, `403` partner consent required, `404` order not found, `422` invalid payload.
- `GET /api/v1/pro/restaurants/partner/handoff/shares/{share_id}/status`
  - `200` active, `403` revoked (fail-closed), `410` expired (fail-closed), `404` not found.
- `POST /api/v1/pro/restaurants/partner/handoff/shares/{share_id}/revoke`
  - `200` revoked (idempotent), `404` not found.

Audit fields (fixed in contract):

- `issuer`
- `partner_id`
- `issued_at`
- `expires_at`
- `revoked_at`

Evidence anchors:

- Endpoints: `app/routers/pro_restaurant_partner.py:149`, `app/routers/pro_restaurant_partner.py:193`, `app/routers/pro_restaurant_partner.py:232`
- Contract models: `app/schemas/restaurant_partner.py:166`, `app/schemas/restaurant_partner.py:171`
- Fail-closed semantics (`403/410`): `app/routers/pro_restaurant_partner.py:198`, `app/routers/pro_restaurant_partner.py:206`
- Revoke idempotency enforcement + test: `app/services/restaurant_partner_orders.py:323`, `tests/test_pro_restaurant_partner_api.py:531`

## W3-R3 Contract Notes (retrieval + confirmation hardening)

Issuer isolation (hard requirement):

- `GET /api/v1/pro/restaurants/partner/orders/{order_id}` and
  `POST /api/v1/pro/restaurants/partner/orders/{order_id}/confirm`
  are issuer-isolated operations.
- Access with a different issuer/API key must return `403` (owner mismatch), fail-closed.
- Evidence anchors: `app/routers/pro_restaurant_partner.py:120`, `app/routers/pro_restaurant_partner.py:162`,
  `app/services/restaurant_partner_orders.py:196`, `app/services/restaurant_partner_orders.py:210`.
- Contract tests: `tests/test_pro_restaurant_partner_api.py:111`,
  `tests/test_pro_restaurant_partner_api.py:131`, `tests/test_pro_restaurant_partner_api.py:363`,
  `tests/test_pro_restaurant_partner_api.py:384`.

Gone semantics (hard requirement):

- Expired handoff share status is terminal-gone semantics (`410`) and must stay deterministic on replay.
- Replay of status checks after expiry must continue to return `410` (no silent recovery to `200`/`403`).
- Evidence anchors: `app/services/restaurant_partner_orders.py:204`,
  `app/services/restaurant_partner_orders.py:249`, `app/routers/pro_restaurant_partner.py:129`,
  `app/routers/pro_restaurant_partner.py:183`.
- Contract tests: `tests/test_pro_restaurant_partner_api.py:230`,
  `tests/test_pro_restaurant_partner_api.py:410`, `tests/test_pro_restaurant_partner_api.py:880`.

Out-of-scope boundary in W3-R3:

- W3-R3 does not introduce payment, delivery orchestration, partner marketplace directory,
  or fulfillment lifecycle expansion.
- Scope is restricted to retrieval/confirm hardening + deterministic error contract behavior.
- Scope evidence anchors: `app/routers/pro_restaurant_partner.py:120`,
  `app/routers/pro_restaurant_partner.py:162`, `tests/test_pro_restaurant_partner_openapi_contract.py:7`,
  `docs/roadmap/BACKLOG_LEDGER.md:3032`.

Temporary seam governance (contract-first -> persistent integration):

- ADR: `docs/architecture/ADR_RESTAURANT_PARTNER_CONTRACT_SEAM_2026-03-03.md` (explicit seam and exit conditions).
- Ledger SoT: `docs/roadmap/BACKLOG_LEDGER.md` (`W3-R1`..`W3-R4` execution items with DoD and blockers).
- Exit criteria (must all hold):
  1. Runtime storage migrates from in-memory seam to persistent storage with audit trail.
  2. All partner-order error contracts are typed and verified in deterministic tests.
  3. Legacy-only assumptions are removed or formally deprecated with a tracked removal PR.

---

## Out of Current Scope

Order acceptance, payment, delivery, partner directory with booking — recorded as possible evolution after format and sharing exist.

---

## Prerequisites

- ✅ VIP weekly plan stable (`vip.py`, `premium_week.py`)
- ✅ Export infrastructure exists (`plan_export.py`, `shoplist_export.py`)
- ✅ Dietary constraints module stable (`core/dietary_constraints.py`)
- ⏳ Backend/VIP stabilization complete (P0)

---

## References

- `app/routers/plan_export.py`, `vip.py` (weekly plan, recipes, export)
- `core/dietary_constraints.py`, `core/targets.py`
- `docs/roadmap/BACKLOG_LEDGER.md` (P2 Vision: Restaurant/chef integration)
- `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md` (Food Data Platform SoT; Wave 3 alignment for restaurant menus and moderated submissions)
