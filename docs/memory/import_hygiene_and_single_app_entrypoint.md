# Memory Capsule: Import hygiene + single app entrypoint

**Topic:** Preventing Dual Base / import drift
**Type:** Invariants + verification commands
**Last updated:** 8 February 2026

---

## What

PulsePlate enforces strict **import hygiene** to prevent dual-namespace imports, xdist hangs, and “two apps” bugs.

Key idea: there must be exactly **one** FastAPI app entrypoint and no test-time import hacks that create parallel module graphs.

---

## Why

Import drift can cause:

- duplicated module state (“Dual Base”)
- test hangs/timeouts under xdist
- missing legacy exports / broken shims
- nondeterministic behavior in CI vs local

---

## Invariants (SoT)

- Import hygiene invariants: `AGENTS.md:348`
- Entrypoint must be `app.main:app`: `AGENTS.md:352`
- Forbidden patterns (dynamic imports, sys.path/sys.modules): `AGENTS.md:357`, `AGENTS.md:358`, `AGENTS.md:359`
- ENV gating order (`TESTING=true` before imports): `AGENTS.md:363`

---

## Commands (fast checks)

- Guard policies:

```bash
pytest -q tests/test_repo_policy_guards.py
```

- Import hygiene checklist greps (see canonical checklist):

```bash
pytest -q tests/test_import_hygiene_guard.py tests/test_env_guards.py
```

---

## Links (canonical)

- `AGENTS.md` → “PR #403 specific invariants (Import Hygiene)”
- `AGENTS.md` → “Import Hygiene Checklist (must-run before PR)”
- `RUNBOOK_AGENT.md` (triage playbook)
