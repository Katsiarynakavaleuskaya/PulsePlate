# Wave 6 A3 AI Bounded-Context Packet

**Date:** 18 April 2026
**Scope:** docs-only architecture packet for `PR-A3`
**Mode:** historical pre-open governance packet; landed via PR #1469 on
`2026-04-19T11:35:29Z` with merge commit
`f8454715f88e44657cfad1c4675f93ea669dc490` from branch
`codex/ai-bounded-context-packet`

## Purpose

Freeze the current-head ownership map for the AI bounded-context lane before the
runtime extraction slice (`PR-A4`).

## Closeout Status

This packet landed through PR #1469
`docs(architecture): define AI bounded-context packet and ownership map`, merged
on `2026-04-19T11:35:29Z` with merge commit
`f8454715f88e44657cfad1c4675f93ea669dc490` from branch
`codex/ai-bounded-context-packet`.

This status note does not change the packet's original scope. `PR-A4` /
`ledger-p1-ai-bounded-context-extraction` remains separate and open until its
own extraction DoD is proven, and semantic-cache markers remain
`closed / false / false / true`.

This packet exists to:

- keep `PR-A3` narrow and docs-only;
- align architecture wording with the already-landed `core/ai/*` seam;
- make router/service/core ownership explicit before any further code movement;
- prevent `PR-A3` from widening into extraction, semantic cache, or new AI
  features.

## Current-head truth

The bounded-context seam is no longer hypothetical.

- `core/ai/*` already exists as the canonical AI bounded-context facade and
  runtime-preparation seam:
  - `core/ai/__init__.py:1-27`
  - `core/ai/insight_runtime.py:1-185`
- `app/services/*` remains the thin app-layer orchestration and tracing layer:
  - `app/services/insight_application_service.py:1-131`
  - `app/services/insight_runtime.py:1-191`
- `app/routers/*` remains the HTTP edge:
  - `app/routers/fitchef_insight.py:1-130`
- repo-level architecture docs already describe `core/ai/` as the canonical
  bounded-context entry seam:
  - `docs/architecture/system_overview.md:17-20`
  - `docs/architecture/system_overview.md:98-103`
- the seam ADR explicitly keeps packet-only architecture work separate from the
  later extraction lane:
  - `docs/architecture/ADR_AI_RUNTIME_BOUNDED_CONTEXT_SEAM_2026-03-09.md:32-42`

## Hard boundaries

- No runtime/product code changes
- No OpenAPI or public contract mutation
- No extraction / code movement into `core/ai/*`
- No provider rewiring beyond docs/evidence wording
- No semantic cache work
- No new model/runtime features
- No GTM / plugin / advisory rail spillover

## Canonical ownership map

### `app/routers/*`

- Thin HTTP adapters only
- Request/response schemas
- Route-level auth / rate-limit / feature-flag edges
- No canonical provider/runtime ownership

### `app/services/*`

- Thin app-layer orchestration only
- Tracing / telemetry adapters
- Runtime execution bridging into `core/ai/*`
- No durable bounded-context ownership

### `core/rag/*`

- Retrieval primitives
- Retrieval orchestration
- Retrieval validation
- No HTTP / route ownership

### `core/insight/*`

- Insight-domain helpers
- Prompt shaping / insight validation helpers
- Philosophy-domain runtime pieces that are not yet fully absorbed into the AI
  bounded context

### `core/ai/*`

- Canonical AI bounded-context entry seam
- Runtime preparation
- Provider loading seam
- Transparency ownership
- The target consolidation home for broader provider / safety / evaluation
  ownership during `PR-A4`

## A3 deliverables

`PR-A3` is allowed to change only:

- packet-scoped architecture docs
- orchestration packet docs for this lane
- backlog/roadmap references that point to the canonical `A3 -> A4` sequence
- governance wording needed to remove stale “future `core/ai/*`” claims

`PR-A3` must not claim to satisfy:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`

## A4 reservation

`PR-A4` is the later extraction lane that may:

- move remaining provider/runtime ownership into `core/ai/*`;
- reduce transitional ownership in `app/services/*`, `core/rag/*`, and
  `core/insight/*`;
- preserve thin adapters at router/service edges while consolidating AI core
  ownership.

That work is explicitly out of scope for `PR-A3`.

## Required role-agent order for this lane

1. `agent-coordinator`
2. `architecture-specialist`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`

Rules:

- every assigned role agent must be used in this order;
- no assigned role agent may be skipped without an explicit packet update;
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains
  mandatory.

## Canonical files for `PR-A3`

- `docs/orchestration/WAVE6_A3_AI_BOUNDED_CONTEXT_PACKET_2026-04-18.md`
- `docs/architecture/C4_AI_BOUNDED_CONTEXT_PACKET_2026-03-20.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- `docs/architecture/ADR_AI_RUNTIME_BOUNDED_CONTEXT_SEAM_2026-03-09.md`

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `pytest -q tests/test_repo_policy_guards.py`

`make verify` remains mandatory before any later merge-ready claim.
