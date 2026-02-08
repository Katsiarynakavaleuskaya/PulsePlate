# Memory Capsule: DB fallback single source of truth

**Topic:** DB fallback invariants and test hygiene
**Type:** Hard rules + safe test patterns
**Last updated:** 8 February 2026

---

## What

DB fallback is owned by **one canonical module**: `core/db_fallback.py`.

No other module may define or directly read/write fallback global state. All access must go through the public helpers.

---

## Why

Fallback drift causes:

- stale-global bugs (import-time copies of state)
- xdist pollution (tests leaking env/session state)
- “works locally, fails in CI” failures

---

## Invariants (SoT)

- Single source of truth: `AGENTS.md:222`
- `legacy_app.py` must delegate only (no fallback helpers/flags): `AGENTS.md:223`
- SessionLocal lifecycle invariant (no `SessionLocal.configure()`): `AGENTS.md:224`
- State mutation policy (helpers only): `AGENTS.md:225`
- Forbidden stale import pattern: `AGENTS.md:226`
- Test hygiene (restore SessionLocal + env keys): `AGENTS.md:228`
- Module/package collision rule: `AGENTS.md:230`

---

## Commands (verification)

- Guard policies (fast signal):

```bash
pytest -q tests/test_repo_policy_guards.py
```

---

## Links (canonical)

- `AGENTS.md` → “DB fallback policy (hard, TP2)”
- Implementation: `core/db_fallback.py`
