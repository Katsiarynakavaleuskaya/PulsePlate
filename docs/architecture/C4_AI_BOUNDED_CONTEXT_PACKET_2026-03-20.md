# C4 AI Bounded Context Extraction Packet

## Status

This document freezes the packet for the C4 AI bounded-context extraction lane.

It is a **packet-only** architecture artifact. It does **not** implement the
runtime extraction itself and does **not** satisfy
`ledger-p1-ai-bounded-context-extraction`.

The implementation-truth item remains:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`

The implementation PR identity also remains unchanged:

- `PR-TBD-AI-BOUNDED-CONTEXT`

## Purpose

Freeze the ownership boundary, implementation decomposition, touched-scope
discipline, and non-goals for the future AI runtime extraction without changing
runtime behavior, route behavior, or public contracts now.

## Packet Scope

This packet freezes:

1. ownership boundary
2. future implementation stack
3. touched-file discipline
4. non-goals and spillover constraints

This packet does **not**:

- create `core/ai/*`
- move provider code
- migrate routes
- change OpenAPI or public schemas
- alter FitChef runtime behavior
- retire the bounded-context seam ADR

## Ownership Boundary

The current runtime remains distributed, but the target ownership boundary is:

- `app/routers/*`
  - thin HTTP adapters only
- `app/services/*`
  - thin app-layer orchestration and tracing adapters only
- `core/rag/*`
  - retrieval and orchestration primitives only
- `core/insight/*`
  - insight-domain helpers, prompt shaping, and validation helpers only
- future `core/ai/*`
  - canonical bounded context for shared AI runtime ownership
  - provider seams
  - runtime policy assembly
  - safety / evaluation ownership mapping

## Future Implementation Stack

The later implementation under `PR-TBD-AI-BOUNDED-CONTEXT` is expected to land
as a bounded sequence:

1. package seam creation
2. provider and runtime ownership extraction
3. safety / evaluation ownership consolidation
4. compatibility cleanup and removal of transitional wording

This packet only freezes that decomposition. It does not perform any step above.

## Touched-File Discipline

### Allowed in this packet PR

- packet-scoped architecture documentation
- seam wording clarification in the bounded-context ADR
- PR governance artifact after PR creation

### Reserved for later implementation PRs

- `core/ai/*`
- `core/rag/*`
- `core/insight/*`
- selected app-layer adapter files
- provider/runtime implementation code

### Default no-touch for this packet PR

- runtime code under `app/*`, `core/*`, `providers/*`
- OpenAPI artifacts
- contract and schema surfaces
- FitChef live route paths

## Canonical Wording Rules

Any draft PR or follow-up docs generated from this packet must state all the
following:

- this is a **packet-only** change
- no runtime or public API changes land here
- this PR does **not** satisfy
  `ledger-p1-ai-bounded-context-extraction`
- implementation remains a later canonical step

Safe dependency wording:

- C4 is prepared and reviewable now
- implementation remains pending explicit canonical promotion

This packet must not claim repo-canonical dependencies that are not explicitly
documented in the current source-of-truth artifacts.

## Non-goals

- no `core/ai/*` creation in this PR
- no route migration
- no provider movement
- no quota / rate-limit rewiring
- no OpenAPI changes
- no FitChef surface changes
- no GTM, Batch D, or Batch E spillover
- no broad governance cleanup hidden inside C4

## Validation

Before opening or updating the draft packet PR, validate:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/route_with_telemetry.py --domain ml --task-type "bounded-context packet"`
- `python3 scripts/ci/check_docs_phase1_gates.py --files <changed-doc-files>`
- `pytest -q tests/test_repo_policy_guards.py`

PR-specific merge-readiness and review-disposition tracking stay canonical in:

- `docs/review/PR_<N>_FIXED_MAPPING.md`

`make verify` remains mandatory before any future merge claim, even for this
docs-first lane.
