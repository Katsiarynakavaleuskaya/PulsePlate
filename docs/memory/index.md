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
- `docs/memory/kpp_knowledge_promotion_pipeline.md` — Knowledge Promotion Pipeline (KPP) (canonical promotion process)
- `docs/memory/runtime_context_memory_contracts.md` — Runtime context memory contracts (budgets, injection posture, UQ-aware degradation behavior)
- `docs/memory/import_hygiene_and_single_app_entrypoint.md` — Import hygiene + single app entrypoint invariants
- `docs/memory/docs_only_and_pr_scope_guard.md` — Docs-only PR rule + PR scope guard expectations
- `docs/memory/api_tiers_and_namespaces.md` — FREE/PRO/VIP namespaces + tier guard order rules
- `docs/memory/legacy_app_thin_proxy_policy.md` — `legacy_app.py` must stay a thin compat proxy
- `docs/memory/db_fallback_single_source_of_truth.md` — DB fallback single source of truth + test hygiene
- `docs/memory/ios_ci_udid_destination_policy.md` — iOS CI deterministic destination (UDID-only) rules
- `docs/memory/quality_gates_precommit_and_verify.md` — pre-commit + `make verify` quality gates
