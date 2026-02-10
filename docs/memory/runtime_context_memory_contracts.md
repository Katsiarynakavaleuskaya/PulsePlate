# Memory Capsule: Runtime context memory (contracts + guardability)

**Topic:** Runtime user memory vs dev-time repo memory

**Type:** Pointer capsule (SoT links only)

**Last updated:** 10 February 2026

---

## What

**Preferred entrypoint:** `docs/orchestration/contracts/RUNTIME_CONTEXT_MEMORY_CONTRACTS.md`.

This capsule is **not** a contract; it is a pointer-only index note for dev-time navigation.

Runtime “context memory” is **explicit user-scoped storage** used by AI/RAG pipelines.
It must be:

- budgeted (stop conditions)
- injection-resistant (retrieved content untrusted)
- uncertainty-aware (degrade deterministically under low confidence)

This is distinct from dev-time “memory capsules”, which are repo pointers only.

---

## Canonical references (SoT)

- Runtime memory contract (draft): `docs/orchestration/contracts/RUNTIME_CONTEXT_MEMORY_CONTRACTS.md`
- RAG contract (draft): `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md` → Contract A3
- UQ contract (draft): `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md` → Contract A2
- CV contract (draft): `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md` → Contract A4
- Abuse controls (rate limit + monthly quota): `docs/memory/llm_cost_abuse_controls.md`
- “External/retrieved content is untrusted” rule: `docs/orchestration/workflow.md`
- KPP (dev-time learning via repo artifacts): `docs/memory/kpp_knowledge_promotion_pipeline.md`
