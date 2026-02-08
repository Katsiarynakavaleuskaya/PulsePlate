# Memory Capsule: API tiers + canonical namespaces

**Topic:** FREE / PRO / VIP tier boundaries and URL namespaces
**Type:** Invariants + test hygiene reminders
**Last updated:** 8 February 2026

---

## What

PulsePlate has canonical API tier namespaces and strict tier guard rules.

Key rule: tier enforcement must run **before** payload validation (tier wins over payload).

---

## Why

Tier namespace drift causes:

- frontend/iOS calling deprecated paths
- incorrect auth behavior (403 vs 422 confusion)
- OpenAPI/type generation drift (wrong paths leak into clients)

---

## Invariants (SoT)

- Tiers are FREE/PRO/VIP and `/premium/*` is deprecated: `AGENTS.md:540`, `AGENTS.md:541`
- VIP namespace: `AGENTS.md:542`
- PRO namespace: `AGENTS.md:657`
- Canonical namespaces list: `AGENTS.md:663`
- Tier guard order (403 before 422): `AGENTS.md:660`
- Premium aliases are shims only (no business logic): `AGENTS.md:664`, `AGENTS.md:675`

---

## Commands (verification / triage)

- Tier guard policy tests (fast signal):

```bash
pytest -q tests/test_repo_policy_guards.py
```

---

## Links (canonical)

- `AGENTS.md` → “Product tiers and API namespaces (canonical)”
- `docs/contracts/PRODUCT_TIER_MAP.md`
