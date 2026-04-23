# Wave 6 A8 Recursive Speed Optimization W1 Packet

**Date:** 23 April 2026
**Scope:** bounded Wave 6 product-AI runtime follow-up for philosophical speed
optimization on the recursive stack
**Mode:** planning packet

## Purpose

Freeze one narrow Wave 6 follow-up slice after merged `PR-A7` that reduces
recursive latency using the already-landed philosophical routing primitives and
bounded recursive seams.

This packet exists to:

- keep `PR-A8` limited to speed optimization for the existing recursive stack;
- reuse speech-act classification, language-game detection, adaptive depth, and
  pragmatic early stopping already present in `main`;
- preserve `VerificationBundle` / verify-before-write semantics from `PR-V1`;
- keep app/service seams thin and public transport contracts unchanged;
- defer any comparative speed or quality claims to `PR-A9` evidence.

## Current-head truth

- `core/insight/philosophical_runtime.py` already owns the philosophical query
  router, public runtime metadata, phase12 rewrite/fallback logic, pragmatic
  validator usage, and adaptive depth selection through the existing bounded
  runtime contract
  (`core/insight/philosophical_runtime.py:128-187`,
  `core/insight/philosophical_runtime.py:236-338`,
  `core/insight/philosophical_runtime.py:386-603`,
  `core/insight/philosophical_runtime.py:721-874`).
- `core/insight/linguistic/__init__.py` already contains cheap deterministic
  speech-act and language-game classification used by the router
  (`core/insight/linguistic/__init__.py:13-88`).
- `core/insight/post_analytical/__init__.py` already contains pragmatic
  assessment and hermeneutic depth optimization used for bounded stopping and
  depth control (`core/insight/post_analytical/__init__.py:12-79`).
- `core/ai/insight_runtime.py` already owns prepared runtime truth for both the
  philosophy rollout policy and recursive rollout policy and must stay the only
  authoritative pre-execution seam
  (`core/ai/insight_runtime.py:42-61`,
  `core/ai/insight_runtime.py:155-223`).
- `core/rag/recursive_retrieval.py` already provides deterministic recursive
  retrieval with bounded hops, refinement passes, verification passes, timeout
  budget, and request-local optimization diagnostics
  (`core/rag/recursive_retrieval.py:63-156`,
  `core/rag/recursive_retrieval.py:338-510`).
- `core/rag/orchestration.py` already owns recursive execution metadata,
  degraded reasons, and `VerificationBundle` assembly and must remain the
  canonical owner for retrieval-path verification truth
  (`core/rag/orchestration.py:28-73`,
  `core/rag/orchestration.py:240-382`,
  `core/rag/orchestration.py:546-579`).
- `app/services/insight_runtime.py` and
  `app/services/insight_application_service.py` already form the thin tracing /
  app handoff seam and must stay observational rather than authoritative
  (`app/services/insight_runtime.py:63-104`,
  `app/services/insight_runtime.py:124-205`,
  `app/services/insight_application_service.py:113-214`).
- The epic and backlog still place `PR-A8` next and keep semantic cache
  deferred (`docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:475-489`,
  `docs/roadmap/BACKLOG_LEDGER.md:2088-2115`).

## Hard boundaries

- No `legacy_app.py` edits
- No `app/routers/*` edits
- No OpenAPI or public response-shape changes
- No new route-layer DTOs
- No semantic cache, Redis/GPTCache, GraphRAG, or ContextManifest work
- No recursive learning lane
- No provider-side chain-of-thought / tree-of-thought widening
- No verification-registry redesign
- No public latency or quality claims without replay evidence

## Canonical implementation surfaces

### Primary runtime seams

- `core/insight/philosophical_runtime.py`
- `core/insight/linguistic/__init__.py`
- `core/insight/post_analytical/__init__.py`
- `core/ai/insight_runtime.py`
- `core/rag/recursive_retrieval.py`
- `core/rag/orchestration.py`
- `app/services/insight_runtime.py`
- `app/services/insight_application_service.py`

### Support surfaces only if needed

- `core/rag/contracts.py`
- `app/utils/feature_flags.py`

### Canonical planning evidence

- `docs/orchestration/WAVE6_A8_TASK_ANALYSIS_2026-04-23.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md:475-489`
- `docs/roadmap/BACKLOG_LEDGER.md:2088-2115`
- `docs/insights/PHILOSOPHICAL_SPEED_OPTIMIZATION.md`

## Required invariants

- `PR-A8` is a bounded speed-optimization lane, not a philosophy rewrite or a
  new recursive architecture.
- Prepared runtime ownership remains in `core.ai.prepare_insight_runtime(...)`;
  app/service layers must not become a second speed-optimization authority.
- Existing public metadata fields only:
  `route_type`, `depth_used`, `verification_rate`, `falsifiability_rate`,
  `contradiction_count`, `reason_codes`, `optimization_applied`.
- `VerificationBundle` / verify-before-write semantics from `PR-V1` remain in
  force.
- Recursive budgets, deterministic stop reasons, and observational
  `verification_calls` remain hard boundaries.
- Semantic cache remains deferred.
- Replay/evidence remains the only source of truth for comparative performance
  claims.

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

- reuse existing speech-act and language-game classifiers to tighten runtime
  path selection;
- reuse existing adaptive depth and pragmatic assessment to reduce unnecessary
  recursive depth;
- preserve and, if needed, refine early-stop behavior across recursive/RAG and
  phase12 validation paths;
- keep the prepared runtime and thin app handoff seams explicit;
- add deterministic tests for bounded speed behavior and no public contract
  drift.

### Out of scope

- semantic cache, persistence, or replay/publication work
- provider-side recursive reasoning expansion
- recursive learning / personalization
- new public metadata fields
- benchmark or marketing narrative work

## First-cut guardrails

The first implementation cut must preserve these exact guardrails:

- no weakening of `VerificationBundle` and knowledge-promotion admission
- no app/tracing recomputation of rollout or speed truth after prepared runtime
- no new response fields or metadata widening
- no medical/local direct-path drift
- no replacement of deterministic recursive budgets or stop reasons

## Primary tests

- `tests/test_core_ai_insight_runtime.py`
- `tests/test_insight_application_service.py`
- `tests/test_recursive_rag.py`
- `tests/test_rag_orchestration.py`
- `tests/test_philosophical_runtime.py`

Fallback only if needed:

- `tests/test_app_insight_runtime.py`
- `tests/test_remaining_modules.py`

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- targeted `pytest -q` on the primary test surfaces above
- `pre-commit run --all-files`
- `make verify`

## Plugin / Skill Recommendation

Planning / implementation stage:

- no plugin family is required for the code change itself
- `GitHub` becomes relevant only once the PR opens
- `CodeRabbit` becomes relevant only in the post-open review cycle

Keep unused for this lane:

- `Computer Use`, `Hugging Face`, `Cloudflare`, `Figma`, `Jam`, `Expo`,
  `build-*`, `Life Science Research`
