# Memory Capsule: `legacy_app.py` must stay a thin compat proxy

**Topic:** Preventing drift in legacy entrypoint
**Type:** Hard rule + guard pointers
**Last updated:** 8 February 2026

---

## What

`legacy_app.py` is a **thin compatibility proxy only**.

It must not accumulate new runtime behavior (middleware, metrics, infra routes) and must delegate to canonical bootstrap/app layers.

---

## Why

Legacy drift creates:

- duplicate registration / subtle behavior divergence
- broken observability and routing assumptions
- “fix it once, breaks elsewhere” regressions

---

## Invariants (SoT)

- Legacy policy header: `AGENTS.md:212`
- Forbidden behavior changes (middleware/observability/infra routes): `AGENTS.md:215`
- Middleware/observability must live in bootstrap called from `app/main.py`: `AGENTS.md:216`
- Allowed contents (thin proxies/shims only): `AGENTS.md:217`

---

## Commands (verification)

- Guard policies (fast signal):

```bash
pytest -q tests/test_repo_policy_guards.py
```

---

## Links (canonical)

- `AGENTS.md` → “legacy_app.py policy (hard)”
- Entrypoint invariant: `AGENTS.md:352` (runtime uses `app.main:app`)
