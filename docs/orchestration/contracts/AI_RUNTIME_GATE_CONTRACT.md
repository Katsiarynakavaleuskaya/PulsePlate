# AI Runtime Gate Contract

**Status:** Canonical PR-A5 gate source for the product AI runtime rail
**Last updated:** 11 April 2026

## Purpose

Define one deterministic source of truth for the `PR-A5` runtime-quality lane:

- retrieval regressions
- faithfulness / unsupported-claim fail-closed checks
- prompt-injection / untrusted-context adversarial checks
- privacy-sensitive and tenant-isolation regressions

This contract is runtime-rail only. It does **not** authorize semantic cache work,
public API drift, or a second evaluation framework.

## Canonical Entrypoint

Use this launcher as the single deterministic bundle entrypoint:

```bash
python3 scripts/orchestration/ai_runtime_gate_bundle.py
```

Default gate bundle coverage:

- `tests/test_logic_philosophy_replay_eval.py`
- `tests/test_agent_run_summary_artifact.py`
- `tests/test_philosophy_validator.py`
- `tests/test_recursive_rag.py`
- `tests/test_rag_orchestration.py`
- `tests/test_vector_rag.py`

## Gate Coverage Map

### 1. Retrieval regressions

- Deterministic retrieval/orchestration behavior stays covered in:
  - `tests/test_rag_orchestration.py`
  - `tests/test_recursive_rag.py`
  - `tests/test_vector_rag.py`

### 2. Faithfulness / unsupported-claim fail-closed

- Unsupported-claim and contradiction checks stay grounded in:
  - `tests/test_logic_philosophy_replay_eval.py`
- Wellness-safe output blocking stays grounded in:
  - `tests/test_philosophy_validator.py`

### 3. Prompt-injection / untrusted-context adversarial checks

- Retrieval output is always treated as untrusted input to the prompt path.
- Deterministic adversarial regressions stay covered in:
  - `tests/test_rag_orchestration.py`
  - `tests/test_recursive_rag.py`
  - `tests/test_vector_rag.py`

### 4. Privacy-sensitive and tenant-isolation regressions

- Prompt/source preview preparation must redact source metadata, PII, and structured
  identity markers before prompt assembly or preview rendering.
- Tenant isolation stays covered in:
  - `tests/test_vector_rag.py`
  - `tests/test_recursive_rag.py`
  - `tests/test_rag_orchestration.py`

### 5. Evidence / release path validator

- Product-copy / coaching evidence path keeps `philosophy_validator` in the release-facing
  artifact flow via:
  - `scripts/orchestration/agent_run_summary.py`
  - `tests/test_agent_run_summary_artifact.py`

## Recursive Memo Seam Contract

The recursive hop memo/cache seam is a bounded optimization seam only.

Required invariants:

- request-scoped only
- no cross-request reuse
- no persistent store
- no Redis
- no GPTCache
- feature-flag-off path disables memo behavior cleanly
- no public response-shape or endpoint contract changes

Canonical implementation surface:

- `core/rag/recursive_retrieval.py`

## Explicit Semantic Cache Boundary

Semantic cache remains deferred by gate.

Canonical deferred gate:

- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`

This PR-A5 contract must not widen into:

- semantic cache implementation
- exact/fuzzy cache rollout
- Redis/GPTCache backend work
- Karpathy/wiki/compiler rail
- billing/auth/entitlement truth
- legal/compliance output memory

## Operator Notes

- This bundle is deterministic by design and reuses existing tests/evaluators.
- `make verify` remains the repo-wide hard gate.
- This runtime gate bundle is the narrow AI-runtime SoT that roadmap/runbook docs should point to.
