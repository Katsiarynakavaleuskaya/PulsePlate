# ADR: OpenAPI Workflow Split Seam (2026-03-09)

- Status: Accepted (temporary seam)
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-openapi-decoupling-split`

## Context

`make openapi` is the current canonical combined workflow for backend schema
generation and frontend type regeneration. This keeps OpenAPI artifacts
deterministic today, but backend-only contract work still pays the frontend
install/type-generation cost.

## Decision

Keep `make openapi` as the only canonical command until the split is
implemented. Document the planned backend/frontend split as a temporary workflow
seam and track its removal through the linked ledger item.

## Exit criteria

Retire this seam only when all are true:

1. A dedicated backend schema target exists without frontend install dependency.
2. A dedicated frontend type-generation target exists.
3. `make openapi-check` remains the canonical sync verifier.
4. `AGENTS.md`, runbooks, API contract docs, and CI docs all describe the split
   workflow consistently with no transitional wording.

## Consequences

- Positive: docs stay truthful about the current command surface.
- Positive: the future split has explicit removal criteria.
- Negative: backend-only workflows keep temporary coupling until the follow-up
  PR lands.
