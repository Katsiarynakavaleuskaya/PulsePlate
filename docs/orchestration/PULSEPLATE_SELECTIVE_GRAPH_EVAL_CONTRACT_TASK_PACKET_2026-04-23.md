# PulsePlate Selective Graph Eval Contract Task Packet

**Date:** 2026-04-23 (`America/New_York`)
**Mode:** coordinator-first, worktree-isolated, docs + schema lane
**Worktree:** `worktrees/selective-graph-eval-contract`
**Branch:** `docs/selective-graph-eval-contract`
**Ledger:** [`ledger-p1-rag-release-gates-lane`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane)

## Decision Question

How should PulsePlate define the smallest offline graph-eval contract for the
three approved selective GraphRAG surfaces without widening into runtime
GraphRAG, semantic cache, provider behavior, or a second canonical eval rail?

## Summary

This lane is a narrow follow-up on the accepted selective GraphRAG ADR.

It introduces:

- one canonical docs contract for offline selective graph evaluation
- one committed JSON schema
- one tiny synthetic fixture

It does not introduce:

- a graph runner
- graph thresholds
- graph release decisions
- runtime GraphRAG behavior

This lane is docs/schema-only and informational only. It does not change
runtime retrieval, request-path logic, provider behavior, or canonical
`PASS` / `NO-GO` ownership.

## Success Criteria

1. A committed docs contract defines the allowed graph-eval surfaces and the
   minimal offline record shape.
2. The contract explicitly stays subordinate to the canonical release-gates
   lane and the companion report-only RAGAS lane.
3. The committed schema bounds `surface`, node types, edge relations, and
   reasoning kinds to the selective GraphRAG starter boundary.
4. The committed fixture contains exactly one synthetic case for each approved
   graph surface.
5. The lane introduces no runtime/request-path/provider/semantic-cache changes.

## Role Order (mandatory)

Execute in this order for the lane:

1. `agent-coordinator`
2. `architecture-specialist`
3. `data-scientist-agent`
4. `ai-innovation-specialist`
5. `backend-engineer`

Privileged-surface reviewer:

1. `security-auditor`

Post-open mandatory review lane:

1. `qa-engineer-agent`
2. `bug-hunter`

## Skill / Plugin Routing

Required skills:

- `pulseplate-workflow`
- `docs-sync`
- `pulseplate-gates`

Recommended skills:

- `agents-md`
- `bug-triage`

Required plugin surfaces:

- `GitHub` for live PR/check/review truth
- `CodeRabbit` for post-open review truth

Optional read-only plugin surfaces only if repo docs leave a real evidence gap:

- `Hugging Face`
- `Life Science Research`

Explicitly out of scope:

- `Computer Use`
- `Netlify`

## Scope

### In scope

- `docs/evals/PULSEPLATE_SELECTIVE_GRAPH_EVAL_CONTRACT.md`
- `docs/orchestration/PULSEPLATE_SELECTIVE_GRAPH_EVAL_CONTRACT_TASK_PACKET_2026-04-23.md`
- `data/evals/pulseplate_selective_graph_eval_schema.json`
- `data/evals/pulseplate_selective_graph_eval_sample.jsonl`
- narrow cross-links in:
  - `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
  - `docs/evals/RAGAS_SETUP.md`

### Out of scope

- `app/**`
- `core/**`
- `llm.py`
- `scripts/evals/**`
- runtime/provider/request-path changes
- semantic cache implementation or widening
- GraphRAG runtime rollout
- graph-specific thresholds or CI gates
- a second evaluation rail

## Contract Decisions

### Allowed surfaces

Only these graph-eval surfaces are allowed:

- `corpus_level_nutrition_summarization`
- `multi_hop_contraindication_reasoning`
- `plan_explainability`

### Required record fields

Every committed offline record must contain:

- `id`
- `surface`
- `question`
- `reference_answer`
- `graph_context`
- `expected_claims`
- `reasoning_expectation`

### Starter graph vocabulary

Allowed node types:

- `foods`
- `nutrients`
- `conditions`
- `restrictions`
- `meal_templates`
- `guideline_concepts`

Allowed edge relations:

- `contains`
- `rich_in`
- `contraindicated_for`
- `recommended_for`
- `substitutable_with`

Allowed reasoning kinds:

- `global_summary`
- `multi_hop`
- `comparative_explanation`

## Risks

- accidental wording that reads like a runtime graph roadmap
- accidental creation of a second graph-eval rail
- semantic-cache drift through vague follow-up language
- fixture content that looks like provider output rather than curated evaluation
  input

## Mitigations

- keep the diff to docs/schema/fixture and two narrow cross-links only
- state explicitly that release-gates and companion RAGAS ownership stay
  unchanged
- require malformed graph-eval schema inputs or artifacts to fail closed in any
  later implementation instead of widening gate behavior
- state explicitly that semantic cache remains under its own gate
- keep fixture rows synthetic and contract-focused

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
make validate-min
```

Before any merge-ready claim:

```bash
make verify
```

## DoD

- docs contract is committed under `docs/evals/`
- packet is committed under `docs/orchestration/`
- schema and sample fixture are committed under `data/evals/`
- release-gates and companion RAGAS docs link to this lane without yielding
  canonical ownership
- semantic cache and runtime GraphRAG remain deferred-only
- post-open `qa-engineer-agent -> bug-hunter` lane is executed after PR open
