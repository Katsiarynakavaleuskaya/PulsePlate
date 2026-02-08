# Memory Capsule: One BMI Engine Invariant

**Topic:** BMI canonical computation path
**Type:** Invariant + enforcement pointers
**Last updated:** 8 February 2026

---

## What

PulsePlate has a hard rule: **exactly one canonical BMI engine** is the sole calculation path for BMI-related computations.

This is not “style”. It is an architectural invariant enforced by guard tests.

---

## Why

Multiple BMI computation paths cause:

- inconsistent results (“BMI undefined” class of issues)
- broken debugging (cannot trust which path was used)
- client drift (thin client policy violations)
- increased test flakiness and coverage waste

---

## Invariants (SoT)

- BMI engine invariant (canonical): `AGENTS.md:813`–`AGENTS.md:829`
- Enforcement tests: see “Enforcement” bullets in `AGENTS.md:817`–`AGENTS.md:822`

---

## Commands (verification / triage)

- Guard policy suite (fast signal):

```bash
pytest -q tests/test_repo_policy_guards.py
```

- BMI canonical guard (if investigating BMI-path drift):

```bash
pytest -q tests/test_bmi_canonical_guard.py
```

- Anti-duplication guard (BMI math outside `core/`):

```bash
pytest -q tests/test_no_bmi_math_outside_core.py
```

---

## Links (canonical)

- Root rules: `AGENTS.md` → “BMI Engine Invariant (Hard Rule)”
- Guard entrypoints: `tests/test_bmi_canonical_guard.py`, `tests/test_no_bmi_math_outside_core.py`
