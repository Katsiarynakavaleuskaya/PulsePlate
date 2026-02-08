# Project Memory (Capsules Index)

**Status:** Canonical index (SoT pointers only)
**Scope:** Dev-only project memory (not runtime user memory)
**Last updated:** 8 February 2026

---

## What this is

“Memory capsules” are short, stable, single-topic notes that help agents avoid repeating the same rediscovery work.

Hard rule: capsules are **not** a second Source of Truth. They only point to canonical rules and commands.

---

## Capsules

- `docs/memory/bmi_one_engine_invariant.md` — One BMI Engine invariant (canonical rule + enforcement pointers)
- `docs/memory/openapi_determinism_and_side_effect_free_generation.md` — OpenAPI determinism + side‑effect‑free generation rules
- `docs/memory/llm_cost_abuse_controls.md` — LLM cost‑abuse controls (rate limiting + monthly quota + budgets)
