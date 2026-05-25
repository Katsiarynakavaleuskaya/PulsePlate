# C4 AI Bounded Context Packet

## Status

This document freezes the packet for the C4 AI bounded-context architecture
lane (`PR-A3`) that prepares the later extraction lane (`PR-A4`).

Closeout note: PR-A3 landed via PR #1469
`docs(architecture): define AI bounded-context packet and ownership map`, merged
on `2026-04-19T11:35:29Z` with merge commit
`f8454715f88e44657cfad1c4675f93ea669dc490` from branch
`codex/ai-bounded-context-packet`.

It is a **packet-only** architecture artifact. It does **not** implement the
runtime extraction itself and does **not** satisfy
`ledger-p1-ai-bounded-context-extraction`.

The implementation-truth item remains:

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`

The implementation PR identity remains:

- `PR-A4`

## Purpose

Freeze the ownership boundary, implementation decomposition, touched-scope
discipline, and non-goals for the later AI runtime extraction without changing
runtime behavior, route behavior, or public contracts now.

## Packet Scope

This packet freezes:

1. ownership boundary
2. future implementation stack
3. touched-file discipline
4. non-goals and spillover constraints

This packet does **not**:

- widen the already-landed `core/ai/*` seam into extraction work
- move provider code
- migrate routes
- change OpenAPI or public schemas
- alter FitChef runtime behavior
- retire the bounded-context seam ADR

## Ownership Boundary

The current runtime already enters through `core/ai/*`, but broader
provider/safety/eval ownership still remains distributed enough that extraction
work is a later lane. The target ownership boundary is:

- `app/routers/*`
  - thin HTTP adapters only
- `app/services/*`
  - thin app-layer orchestration and tracing adapters only
- `core/rag/*`
  - retrieval and orchestration primitives only
- `core/insight/*`
  - insight-domain helpers, prompt shaping, and validation helpers only
- `core/ai/*`
  - canonical bounded context entry seam for shared AI runtime ownership
  - provider seams
  - runtime preparation and transparency ownership
  - target consolidation home for broader safety / evaluation ownership

### Evidence

- `app/routers/*` remains the HTTP edge:
  `app/routers/fitchef_insight.py:45` defines the router surface, and
  `app/routers/fitchef_insight.py:101` maps request input into a task envelope
  before delegating to app-layer runtime code.
- `app/services/*` remains thin app-layer orchestration/tracing glue:
  `app/services/insight_application_service.py:24`-`app/services/insight_application_service.py:27`
  imports the canonical `core.ai` entry seam,
  `app/services/insight_application_service.py:80`-`app/services/insight_application_service.py:88`
  prepares runtime state through that seam, and
  `app/services/insight_runtime.py:1`-`app/services/insight_runtime.py:4`
  documents that tracing remains outside `core/`.
- `core/rag/*` owns retrieval and orchestration primitives:
  `core/rag/orchestration.py:121` exposes the retrieval + validation pipeline,
  `core/rag/orchestration.py:176` executes retrieval/prompt assembly, and
  `core/rag/validation.py:110` validates retrieved chunks against wellness
  boundaries.
- `core/insight/*` owns insight-domain helpers, prompt shaping, and validation:
  `core/insight/safety.py:10` redacts prompt context,
  `core/insight/llm_provider_loader.py:34` keeps provider loading lazy for
  insight callers, and `core/insight/philosophy_validator.py:84` validates
  wellness-safe output.
- `core/ai/*` already exists as the canonical bounded-context entry seam:
  `core/ai/__init__.py:1`-`core/ai/__init__.py:27` defines the facade surface,
  `core/ai/insight_runtime.py:1`-`core/ai/insight_runtime.py:8` documents the
  stable bounded-context package, and
  `core/ai/insight_runtime.py:142`-`core/ai/insight_runtime.py:185`
  prepares runtime/provider/transparency state without HTTP ownership.
- repo-canonical architecture docs already describe `core/ai/*` as the AI seam:
  `docs/architecture/system_overview.md:19` and
  `docs/architecture/system_overview.md:98`-`docs/architecture/system_overview.md:103`.
- the seam ADR keeps packet-only preparation separate from implementation:
  `docs/architecture/ADR_AI_RUNTIME_BOUNDED_CONTEXT_SEAM_2026-03-09.md:34`-`docs/architecture/ADR_AI_RUNTIME_BOUNDED_CONTEXT_SEAM_2026-03-09.md:42`.

## Future Implementation Stack

The later implementation under `PR-A4` is expected to land
as a bounded sequence:

1. remaining provider and runtime ownership extraction into the existing seam
2. app/service adapter narrowing around the extracted ownership
3. safety / evaluation ownership consolidation
4. compatibility cleanup and removal of transitional wording

This packet only freezes that decomposition. It does not perform any step above.

## Touched-File Discipline

### Allowed in this packet PR

- packet-scoped architecture documentation
- orchestration packet for `PR-A3`
- backlog / roadmap pointer correction for `A3 -> A4`
- seam wording clarification in the bounded-context ADR
- PR governance artifact after PR creation

### Reserved for later implementation PRs

- `core/rag/*`
- `core/insight/*`
- `core/ai/*` implementation internals
- selected app-layer adapter files
- provider/runtime implementation code

### Default no-touch for this packet PR

- runtime code under `app/*`, `core/*`, `providers/*`
- OpenAPI artifacts
- contract and schema surfaces
- FitChef live route paths

## Canonical Wording Rules

Any draft PR or follow-up docs generated from this packet must state the
following:

- this is a **packet-only** change
- no runtime or public API changes land here
- `core/ai/*` already exists; this PR only freezes ownership wording
- this PR does **not** satisfy
  `ledger-p1-ai-bounded-context-extraction`
- implementation remains `PR-A4`

Safe dependency wording:

- C4 is prepared and reviewable now
- implementation remains pending explicit canonical promotion

This packet must not claim repo-canonical dependencies that are not explicitly
documented in the current source-of-truth artifacts.

## Non-goals

- no `core/ai/*` extraction or internal code movement in this PR
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
- `pre-commit run --all-files`
- `pytest -q tests/test_repo_policy_guards.py`

PR-specific merge-readiness and review-disposition tracking stay canonical in:

- `docs/review/PR_<N>_FIXED_MAPPING.md`

`make verify` remains mandatory before any future merge claim, even for this
docs-first lane.
