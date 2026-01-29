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
