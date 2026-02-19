# Project Knowledge Library

Canonical library for agent-driven knowledge enrichment and promotion.

## Source of truth

- Runbook: [`docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`](../orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md)
- Matrix: [`docs/orchestration/AGENT_CAPABILITY_MATRIX.md`](../orchestration/AGENT_CAPABILITY_MATRIX.md)
- Brainstorm protocol: [`docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`](../orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md)
- Research protocol: [`docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`](../orchestration/RESEARCH_TRACK_PROTOCOL.md)
- KPP: [`docs/memory/kpp_knowledge_promotion_pipeline.md`](../memory/kpp_knowledge_promotion_pipeline.md)
- Backlog ledger: [`docs/roadmap/BACKLOG_LEDGER.md`](../roadmap/BACKLOG_LEDGER.md)

## Library map

- Brainstorm artifacts: [`docs/library/brainstorm/`](./brainstorm/)
- Research evidence: [`docs/library/research/`](./research/)
- Decisions (ADR pointers): [`docs/library/decisions/`](./decisions/)
- Promotion logs: [`docs/library/promotion/`](./promotion/)

## Workflow entry point

1. Create brainstorm artifact with a `Routing Card`.
2. Add research evidence only when external claims are used.
3. Write synthesis and decision.
4. Promote into one durable target (SoT/ADR/tests/ledger).
5. Open PR with explicit `IN/OUT`, validation, and deferred links.
