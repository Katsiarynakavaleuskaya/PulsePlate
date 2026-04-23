# Wave 6 A6 Philosophical Rollout W1 Packet

**Date:** 22 April 2026
**Scope:** bounded Wave 6 product-AI runtime follow-up for philosophical phase rollout
**Mode:** planning packet

## Purpose

Freeze one narrow Wave 6 follow-up slice after `PR-V1` that rolls out the
existing philosophical runtime foundation on bounded product-AI surfaces
without reopening foundation work or widening into semantic cache.

This packet exists to:

- keep `PR-A6` phase-ordered and `phase12-first reconciliation`;
- reconcile router/validation/rewrite/fallback behavior against the current
  bounded runtime seam;
- preserve `VerificationBundle` / verify-before-write semantics already landed
  in `PR-V1`;
- keep app/service layers thin and public transport contracts unchanged;
- defer any measured quality or latency claims to replay/benchmark evidence.

## Current-head truth

- `core/insight/philosophical_runtime.py` already contains the philosophical
  runtime foundation: router preview, local-direct paths, verification,
  falsification, contradiction counting, rewrite/fallback logic, and knowledge
  candidate handoff.
- `core/ai/insight_runtime.py` already owns the canonical non-HTTP bounded seam
  via `prepare_insight_runtime(...)`.
- `app/services/insight_application_service.py` and
  `app/services/insight_runtime.py` are already the thin application handoff and
  tracing seams and must stay that way.
- `PR-V1` already landed the verification registry and canonical
  verify-before-write admission contract through the runtime/RAG path.
- Semantic cache remains deferred and must not be widened by this lane.

## Hard boundaries

- No `legacy_app.py` edits
- No `app/routers/*` edits
- No OpenAPI or public response shape changes
- No new route-layer DTOs
- No semantic cache, Redis, GPTCache, GraphRAG, or ContextManifest work
- No philosophy foundation rewrite or second runtime stack
- No reopening verification-registry architecture from `PR-V1`
- No widening into advisory/wiki/plugin control-plane rails

## Canonical implementation surfaces

### Primary runtime seams

- `core/insight/philosophical_runtime.py`
- `core/ai/insight_runtime.py`
- `app/services/insight_application_service.py`
- `app/services/insight_runtime.py`

### Support surfaces only if needed

- `app/utils/feature_flags.py`
- `core/rag/orchestration.py`

### Canonical planning evidence

- `docs/orchestration/WAVE6_A6_TASK_ANALYSIS_2026-04-22.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophical-logic`

## Required invariants

- `PR-A6` is a bounded rollout/reconciliation lane, not a foundation rewrite.
- W1 treats `Aristotelian + Analytical` as the primary execution target because
  live code already exposes this through `FEATURE_PHILOSOPHY_PHASE12`.
- `prepare_insight_runtime(...)` remains the canonical ownership seam for
  bounded runtime preparation.
- App/service layers stay thin and must not author philosophy truth outside the
  bounded runtime seam.
- `VerificationBundle` / verify-before-write semantics from `PR-V1` remain in
  force.
- Existing metadata fields only: `route_type`, `depth_used`,
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

- introduce one bounded internal phase-rollout contract for the existing
  philosophy flags on the runtime path;
- surface stable additive runtime evidence for active philosophy phases using
  existing metadata fields;
- keep router/validation/rewrite/fallback behavior coherent across `core/ai`,
  runtime, and app handoff seams;
- add deterministic tests for bounded rollout behavior and no payload drift.

### Out of scope

- broad rollout of every philosophy family in one PR
- replay/eval corpus promotion unless the implementation directly changes that
  contract
- recursive speed optimization lane (`PR-A7`)
- semantic cache and persistence work
- any scientific, comparative, or latency-uplift claim not backed by the
  replay/eval contract

## First-Cut Defect Guardrails

The first implementation cut must preserve these exact guardrails:

- `router_enabled = philosophy_router_enabled || philosophy_linguistic_enabled`
  remains the truth table for route preview and direct-answer paths
- `generate_insight(...)` keeps legacy bool compatibility in the first cut while
  normalizing into the internal rollout policy
- tracing stays observational only and must not become a competing rollout
  authority
- app/service layers must not keep a second rollout-truth source after
  `prepare_insight_runtime(...)` returns the prepared policy
- rollout policy must not subsume `philo_validation_enabled` or
  `verification_bundle` admission semantics
- existing direct medical/local-answer no-provider behavior and verify-before-
  write fail-closed behavior must remain bit-for-bit intact

## Primary tests

- `tests/test_philosophical_runtime.py`
- `tests/test_core_ai_insight_runtime.py`
- `tests/test_insight_application_service.py`
- one narrow metadata path in `tests/test_philosophy_validation_integration.py`

Fallback only if needed:

- `tests/test_rag_orchestration.py`
- `tests/test_remaining_modules.py`
- `tests/test_logic_philosophy_replay_eval.py`

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
