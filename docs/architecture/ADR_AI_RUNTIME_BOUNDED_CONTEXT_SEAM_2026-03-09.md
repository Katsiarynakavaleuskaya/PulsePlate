# ADR: AI Runtime Bounded-Context Extraction Seam (2026-03-09)

- Status: Accepted (temporary seam)
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`

## Context

AI provider integration, safety controls, and insight/runtime behavior are
documented across several runtime areas. The target architecture is a clearer
bounded context, but the canonical package boundary is not implemented yet.

## Decision

Keep the current runtime structure, but document AI bounded-context extraction
as an explicit temporary seam with a linked ledger item and removal criteria.

## Exit criteria

Retire this seam only when all are true:

1. A canonical AI runtime package structure exists and is documented.
2. Routers and client layers remain thin adapters around AI behavior.
3. Safety, evaluation, and provider ownership are mapped to that bounded
   context.
4. `AGENTS.md`, architecture docs, and quick-path docs no longer need
   transitional wording about future extraction.

## Consequences

- Positive: contributors get an auditable explanation for the current wording.
- Positive: the architecture target is explicit without pretending it already
  exists.
- Negative: AI runtime ownership remains distributed until the follow-up PR.
