# PR-633 — Unify `TargetsIn` schemas (legacy_app ↔ `app.schemas.nutrition_targets`)

**Date:** 3 февраля 2026 года
**Type:** Follow-up (P1, drift prevention)
**Scope owner:** @katsiaryna_kavaleuskaya

---

## Summary

This PR eliminates schema drift by making `TargetsIn` a **single source of truth** and ensuring
legacy endpoints validate structured `targets` payloads via the canonical schema.

---

## Ledger scope (source of truth)

Backlog item (P1, next by order for PR-633) defines strict DoD:

- One canonical schema (single source of truth) + thin wrapper/alias where needed
- Parity tests (fields + validation behavior)
- No contract break for legacy endpoints (explicitly verified in tests)

**Evidence (ledger):**

```375:390:docs/roadmap/BACKLOG_LEDGER.md
- [ ] P1: Unify `TargetsIn` schemas (legacy_app ↔ `app.schemas.nutrition_targets`)
  ...
  - Evidence:
    - `app/schemas/nutrition_targets.py:L1-L58` (import-safe schema + `TargetsIn` validators)
    - `legacy_app.py:L2879-L2919` (`legacy_app.TargetsIn` definition)
    - `legacy_app.py:L2939-L2954` (`TargetsIn.model_validate(...)` use in legacy request validator)
  - DoD:
    - One canonical schema (single source of truth) with a thin wrapper/alias where needed
    - Parity tests that prevent schema drift (fields + validation behavior for structured targets payloads)
    - No contract break for legacy endpoints (explicitly verified in tests)
```

---

## Locked scope

### In scope

- Canonical `TargetsIn` remains in `app/schemas/nutrition_targets.py` (import-safe).
- `legacy_app.TargetsIn` becomes a thin alias/wrapper to canonical schema (no local validators).
- Add parity tests to prevent drift in fields + validation behavior.
- Add explicit test that legacy endpoint contract is not broken by this unification.

### Anti-scope (explicitly forbidden)

- OpenAPI remediation / feature flags / unrelated routers
- New endpoints
- Any new business logic in `legacy_app.py` (legacy must remain thin proxy / delegation only)

---

## Architecture decision

### Source of truth (SoT)

**SoT:** `app.schemas.nutrition_targets.TargetsIn`

**Reason:** module is explicitly designed to be import-safe for OpenAPI path.

**Evidence:**

```1:9:app/schemas/nutrition_targets.py
IMPORTANT:
- This module must stay import-safe (no SQLAlchemy, no Base/metadata side-effects).
- Routers may import these schemas at module import time (OpenAPI generation path).
```

### Legacy policy

Legacy must not define its own validation path for `TargetsIn` to avoid drift. Legacy uses canonical
schema by alias/wrapper.

---

## Contract decision (F17)

✅ Numeric strings (e.g. `"150.0"`) are considered **valid** numeric inputs for `macros`/`micro`.

**Reason:** reduces client breakage and avoids avoidable 422 errors caused by UI serialization
while preserving strict validation (bool forbidden; finite; `>= 0`).

This decision is enforced by parity tests.

---

## Test plan (DoD evidence)

- Parity tests validate:
  - same fields
  - same validation behavior (`"150.0"` valid; `True` invalid; `NaN/Inf` invalid; negative invalid)
- Legacy endpoint test verifies:
  - structured `targets` payload validation remains strict
  - no contract break (request still accepted/rejected deterministically)

---

## Verification gates (canonical)

Before merge:

- `pre-commit run --all-files`
- `make verify`
- `make openapi-check` (expected: **no diff**)

---

## Security Notes

- Accepting numeric strings does not expand attack surface: values are still strictly normalized and
  validated (no bool, must be finite, must be `>= 0`).
- Removing duplicate validation paths reduces ambiguity and “bypass via drift” risk.

---

## Marketing & GTM Notes

This PR is user-invisible but improves reliability: fewer unexpected 422 errors from serialization
differences → fewer “app feels broken” moments → better onboarding retention.
