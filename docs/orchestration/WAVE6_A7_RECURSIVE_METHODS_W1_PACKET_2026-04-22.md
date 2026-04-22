# Wave 6 A7 Recursive Methods W1 Packet

**Date:** 22 April 2026
**Scope:** bounded Wave 6 product-AI runtime follow-up for recursive methods W1
**Mode:** planning packet

## Purpose

Freeze one narrow Wave 6 follow-up slice after merged `PR-A6` that promotes the
existing recursive retrieval/orchestration foundation on bounded product-AI
surfaces without reopening broad recursive roadmap phases or widening into
semantic cache.

This packet exists to:

- keep `PR-A7` bounded to recursive retrieval/orchestration/runtime surfacing;
- preserve recursive budgets, deterministic refinement, and bounded verification
  calls already present in `main`;
- keep `VerificationBundle` / verify-before-write semantics from `PR-V1` in
  force;
- preserve thin app/service seams and public transport contracts unchanged;
- defer quality/latency claims to replay/benchmark evidence rather than PR copy.

## Current-head truth

- `core/rag/recursive_retrieval.py` already contains deterministic recursive
  retrieval with bounded hops, refinement passes, verification passes, timeout
  budget, and request-local optimization diagnostics.
- `core/rag/orchestration.py` already owns the bounded recursive handoff into
  validated chunks, degraded reasons, recursive execution metadata, and
  canonical `VerificationBundle` assembly.
- `core/insight/philosophical_runtime.py` already consumes recursive execution
  metadata and exposes recursive-path reason codes through existing runtime
  metadata fields.
- `app/services/insight_application_service.py` and
  `app/services/insight_runtime.py` already own the thin application handoff
  and feature-flag seams and must stay that way.
- `PR-V1` already landed the verification registry and canonical
  verify-before-write admission contract through the recursive/RAG path.
- `PR-A6` already reconciled the philosophy rollout seam; recursive W1 must
  build on that merged runtime shape instead of reopening it.
- Semantic cache remains deferred and must not be widened by this lane.

## Hard boundaries

- No `legacy_app.py` edits
- No `app/routers/*` edits
- No OpenAPI or public response shape changes
- No new route-layer DTOs
- No semantic cache, Redis/GPTCache rollout, GraphRAG, or ContextManifest work
- No recursive learning / feedback adaptation lane
- No provider-side recursive reasoning / chain-of-thought expansion
- No second recursive runtime stack
- No reopening `PR-V1` or `PR-A6` architecture
- No widening into advisory/wiki/plugin control-plane rails

## Canonical implementation surfaces

### Primary runtime seams

- `core/rag/recursive_retrieval.py`
- `core/rag/orchestration.py`
- `core/verification/registry.py`
- `core/insight/philosophical_runtime.py`
- `app/services/insight_application_service.py`
- `app/services/insight_runtime.py`

### Support surfaces only if needed

- `app/utils/feature_flags.py`
- `core/rag/contracts.py`

### Canonical planning evidence

- `docs/orchestration/WAVE6_A7_TASK_ANALYSIS_2026-04-22.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-recursive-methods`

## Required invariants

- `PR-A7` is a bounded recursive rollout/reconciliation lane, not a full
  recursive-framework rewrite.
- W1 is limited to the recursive retrieval/orchestration stack already present
  in `main`; it does not add recursive learning or provider-side recursive
  reasoning.
- Existing hop, refinement, verification, and timeout budgets remain hard
  boundaries.
- `core/rag/orchestration.py` remains the canonical owner of recursive
  execution metadata and `VerificationBundle` assembly for the retrieval path.
- App/service layers stay thin and must not author recursive truth outside the
  bounded runtime seam.
- `VerificationBundle` / verify-before-write semantics from `PR-V1` remain in
  force.
- Existing runtime metadata fields only: `route_type`, `depth_used`,
  `verification_rate`, `falsifiability_rate`, `contradiction_count`,
  `reason_codes`, `optimization_applied`.
- Replay/eval evidence remains the source of truth for any comparative efficacy
  or latency-uplift claim.
- Semantic cache remains deferred under
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`.

## Required role-agent order for this lane

1. `agent-coordinator`
2. `architecture-specialist`
3. `data-scientist-agent`
4. `backend-engineer`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`

Rules:

- every assigned role agent must be used in this order;
- no assigned role agent may be skipped without an explicit packet update;
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains
  mandatory.

## W1 scope

### In scope

- reconcile and tighten bounded recursive execution behavior using the existing
  deterministic retrieval path;
- preserve and, if needed, refine recursive execution diagnostics that feed
  orchestration/runtime reason codes and `VerificationBundle` truth;
- keep feature-flag ownership explicit and thin across app/service seams;
- add deterministic tests for bounded recursive behavior, degraded/fail-safe
  branches, and no payload drift.

### Out of scope

- tree-of-thought / chain-of-thought provider prompting
- recursive learning, user-feedback adaptation, or personalization loops
- semantic cache and persistence work
- Redis/GPTCache rollout work
- broad experiment/replay/publication lane work unless the implementation
  directly changes that contract
- any scientific, comparative, or latency-uplift claim not backed by the
  replay/eval contract

## First-cut guardrails

The first implementation cut must preserve these exact guardrails:

- recursive retrieval stays deterministic and budget-bounded
- `verification_calls` stays observational and is not replaced by an ad-hoc
  second recursive validator stack
- recursive execution metadata continues to flow through
  `RAGOrchestrationResult` into existing runtime reason codes
- recursive enablement must not weaken tenant isolation, degraded fail-safe
  behavior, or verify-before-write admission
- app/service layers must not become a second recursive truth source after the
  prepared runtime/feature-flag seam resolves enablement
- tracing remains observational only and must not become a competing recursive
  authority

## Primary tests

- `tests/test_recursive_rag.py`
- `tests/test_rag_orchestration.py`
- `tests/test_insight_rag_response_fields.py`
- `tests/test_remaining_modules.py`

Fallback only if needed:

- `tests/test_philosophical_runtime.py`
- `tests/test_insight_application_service.py`
- `tests/test_rag_release_gates_runner.py`

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- targeted `pytest -q` on the primary test surfaces above
- `pre-commit run --all-files`
- `make verify`

## Plugin / Skill Recommendation

Planning stage:

- no plugin family is required now
- no extra skill activation is required beyond coordinator-first repo workflow

Useful later, but not needed for planning:

- `GitHub` for current-head PR/check truth once implementation starts
- `CodeRabbit` for the post-open review cycle

Keep unused at planning stage:

- `Computer Use`, `Hugging Face`, `Cloudflare`, `Figma`, `Jam`, `Expo`,
  `build-*`, `Life Science Research`
