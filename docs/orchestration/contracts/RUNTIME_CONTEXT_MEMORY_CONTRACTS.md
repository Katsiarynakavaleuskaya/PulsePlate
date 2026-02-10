# Runtime Context Memory Contracts (Draft, Docs-only)

**Status:** Draft contracts for future runtime implementation PRs

**Scope:** Runtime user context memory (not dev-time repo “memory capsules”)

**Last updated:** 10 February 2026

---

## Definition

**Preferred entrypoint:** This file is the runtime memory **contract**. The capsule
`docs/memory/runtime_context_memory_contracts.md` is a **pointer-only index note** and must not be treated as a duplicate contract.

Runtime context memory is **explicit, user-scoped storage** used to personalize AI/coaching/RAG outputs.

Hard boundary:

- This is **not** “model memory”.
- This is **not** a second Source of Truth for project rules.

Project “self-learning” remains KPP-driven (repo artifacts only): `docs/memory/kpp_knowledge_promotion_pipeline.md`.

---

## Contract M1) Trust boundaries (non-negotiable)

- Retrieved content (web, OSS, RAG snippets, user memories) is **untrusted**.
- System instructions come only from fixed, versioned prompts/contracts.
- Do not follow instructions embedded inside retrieved content.

Canonical security note: `docs/orchestration/workflow.md` → “Security: External / Retrieved Content”.

---

## Contract M2) Memory types (minimum)

Future runtime memory MUST distinguish at least:

- **Episodic memory** (recent interactions/events; TTL-bounded)
- **Semantic memory** (durable preferences/constraints; user-controlled)

Required per-item fields (minimum):

- `user_id` (or equivalent auth-scoped key)
- `type` (`episodic` | `semantic`)
- `source` (`user_stated` | `stored_fact` | `inferred`)
- `created_at` / `updated_at`
- retention metadata (TTL or deletion policy)

---

## Contract M3) Budgets / stop conditions (required)

Any runtime pipeline that reads memory and calls an LLM MUST have explicit budgets:

- max retrieved items (e.g. `K_doc`, `K_user`)
- max context size (`C_max`)
- max hops / recursion (default: 0)
- timeouts

Must align with repo abuse controls:

- rate limiting (LLM endpoints)
- monthly hard quota enforced **before** provider calls
- feature flags checked **before** quota consumption

Canonical pointers: `AGENTS.md` (rate limiting + monthly quota) and `docs/memory/llm_cost_abuse_controls.md`.

---

## Contract M4) Attribution (when memory/RAG is used)

If an output uses retrieval (docs or memory), responses MUST include sources/attribution.

Canonical draft contract: `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md` → “Contract A3) RAG + Recursive Verification”.

---

## Contract M5) Uncertainty / degrade behavior (memory-aware)

Memory retrieval must expose uncertainty in a **guardable** way (no false precision).

Minimum:

- memory items have `confidence_bucket` (`high` | `medium` | `low`) and optional `conflict_flag`
- low/conflicting memory triggers deterministic degrade behavior:
  - omit personalization, or
  - ask a single clarifying question

Reference draft: `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md` → “Contract A2) Uncertainty / Bayesian-UQ”.

---

## Contract M6) Privacy + user controls

Runtime memory MUST support:

- per-item delete (“forget this”)
- bulk clear (“forget all”)
- export (contract-defined scope)
- explicit consent and retention rules for any stored media (photos)

CV-specific constraints live in: `docs/orchestration/contracts/AI_OUTPUT_CONTRACTS.md` → “Contract A4) CV pipeline”.

---

## Acceptance criteria (future deterministic tests)

Future runtime PRs implementing memory MUST include deterministic tests proving:

1. user isolation (no cross-user memory leakage)
2. budgets enforced (top-K and context caps)
3. injection defense: retrieved content cannot override system instructions
4. low-confidence/conflict → deterministic degrade path
5. delete/export paths are honored per contract
