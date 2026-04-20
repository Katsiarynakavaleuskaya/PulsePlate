# Wave 6 K1 Knowledge Promotion Packet

**Date:** 19 April 2026
**Scope:** bounded post-A5 runtime follow-up for internal knowledge contracts
**Mode:** implementation packet

## Purpose

Freeze one narrow post-A5 runtime slice that introduces first-class internal
knowledge contracts and promotion rules **without** widening into semantic
cache, persistent storage, or HTTP/public-contract work.

This packet exists to:

- add a bounded `core/knowledge/*` subdomain;
- treat RAG chunks as evidence artifacts, not canonical facts;
- allow promotion only from validated RAG evidence that survives orchestration;
- keep route/service layers thin and keep semantic cache deferred.

## Current-head truth

- `core/ai/insight_runtime.py` already owns the canonical non-HTTP runtime
  preparation seam.
- `core/rag/orchestration.py` already computes deterministic retrieval
  diagnostics and degraded reasons.
- `core/insight/philosophical_runtime.py` already receives raw
  `RAGOrchestrationResult` and turns it into internal runtime metadata without
  public DTO drift.
- `app/services/insight_application_service.py` is already a thin handoff layer
  and must stay that way.

## Hard boundaries

- No `legacy_app.py` edits
- No `app/routers/*` edits
- No OpenAPI or public response contract changes
- No DB migrations or Postgres table rollout
- No Redis / GPTCache / semantic-cache implementation
- No route-layer or raw-provider promotion logic
- No widening into advisory/wiki/plugin control-plane rails

## Canonical implementation surfaces

### New internal subdomain

- `core/knowledge/__init__.py`
- `core/knowledge/contracts.py`
- `core/knowledge/policy.py`
- `core/knowledge/promotion.py`
- `core/knowledge/store.py`

### Existing seams allowed to change

- `core/ai/insight_runtime.py`
- `core/rag/orchestration.py`
- `core/insight/philosophical_runtime.py`
- `app/services/insight_runtime.py`
- `app/services/insight_application_service.py`

Reason:

- `app/services/insight_runtime.py` remains an allowed thin tracing seam only,
  used to thread `knowledge_policy` into the existing traced runtime handoff
  without moving promotion logic into routes or `legacy_app.py`.

## Required invariants

- RAG chunks remain evidence artifacts only.
- Knowledge promotion is allowed only from validated RAG evidence.
- Promotion must fail closed on degraded retrieval/orchestration reasons.
- `prepare_insight_runtime(...)` is the canonical seam for runtime knowledge
  policy.
- Request-local recursive caches are optimization helpers only and must never be
  treated as persistent knowledge.
- `DEEP_REASONING` is promotion-denied by default.
- Access scope must be at least as strict as the current tenant/subject
  isolation model.

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

## Execution evidence

- `docs/orchestration/WAVE6_K1_TASK_ANALYSIS_2026-04-19.md`
- `docs/orchestration/WAVE6_K1_WORK_REVIEW_2026-04-19.md`
- `docs/orchestration/WAVE6_K1_SYNTHESIS_2026-04-19.md`
- `docs/orchestration/WAVE6_K1_DOD_2026-04-19.md`

## Deliverables

- bounded `core/knowledge/*` contracts/policy/promotion/store seam
- `PreparedInsightRuntime.knowledge_policy`
- internal-only runtime handoff for promotion candidates
- deterministic tests for promotion allow/deny and supersession behavior
- root invariant wording updated without redefining semantic-cache gate

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- targeted pytest for knowledge/runtime/orchestration paths
- `pre-commit run --all-files`
- `make verify`

## Explicit semantic-cache boundary

K1 is **not** semantic cache.

Semantic cache remains governed by:

- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`

Hard rule:

- do not widen K1 into semantic-cache records, cache hit logic, Redis/GPTCache,
  or observability for semantic-cache precision/false-hit tracking.
