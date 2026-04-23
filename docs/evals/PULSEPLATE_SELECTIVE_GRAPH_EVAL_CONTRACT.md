# PulsePlate Selective Graph Eval Contract

**Status:** docs-only offline contract
**Effective date:** 2026-04-23 (`America/New_York`)
**Parent ADR:** [`ADR_SELECTIVE_GRAPHRAG_CONTRACT_2026-04-22.md`](../architecture/ADR_SELECTIVE_GRAPHRAG_CONTRACT_2026-04-22.md)
**Lane packet:** [`PULSEPLATE_SELECTIVE_GRAPH_EVAL_CONTRACT_TASK_PACKET_2026-04-23.md`](../orchestration/PULSEPLATE_SELECTIVE_GRAPH_EVAL_CONTRACT_TASK_PACKET_2026-04-23.md)
**Canonical release-gates owner:** [`PULSEPLATE_RAG_RELEASE_GATES.md`](./PULSEPLATE_RAG_RELEASE_GATES.md)
**Companion RAGAS owner:** [`RAGAS_SETUP.md`](./RAGAS_SETUP.md)
**Semantic cache gate:** [`PulsePlate_Semantic_Cache_Gate_and_Plan.md`](../roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md)
**Ledger anchors:** [`ledger-p1-rag-release-gates-lane`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane), [`ledger-p1-recursive-methods`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-recursive-methods)

## Purpose

This lane defines the smallest committed offline contract for future selective
graph evaluation in PulsePlate.

It exists to freeze:

- which graph-question surfaces are allowed
- what a committed offline graph-eval record looks like
- how graph-eval stays subordinate to the existing evidence and evaluation spine

It does not introduce:

- runtime GraphRAG rollout
- semantic cache widening
- provider behavior changes
- a graph runner
- graph-specific CI thresholds
- a second canonical evaluation rail

## Allowed Surfaces Only

Offline graph-eval is allowed only for the three surfaces already approved by
the selective GraphRAG ADR:

1. `corpus_level_nutrition_summarization`
2. `multi_hop_contraindication_reasoning`
3. `plan_explainability`

All other graph-question categories remain out of scope for this contract.

## Canonical Ownership Boundary

The canonical owners remain unchanged:

- [`PULSEPLATE_RAG_RELEASE_GATES.md`](./PULSEPLATE_RAG_RELEASE_GATES.md)
  owns threshold vocabulary, gate checks, and `PASS` / `NO-GO` semantics
- [`RAGAS_SETUP.md`](./RAGAS_SETUP.md) owns the companion local report-only
  RAGAS surface

This graph-eval contract is an offline design surface only. It must not be
used to redefine:

- `thresholds`
- `threshold_results`
- `gate_checks`
- `release_decision`
- `--require-pass`

This lane is docs/schema-only and informational only. It does not change
runtime retrieval, request-path logic, provider behavior, or canonical
`PASS` / `NO-GO` ownership.

## Committed Repo Artifacts

Committed contract artifacts for this lane:

- `data/evals/pulseplate_selective_graph_eval_schema.json`
- `data/evals/pulseplate_selective_graph_eval_sample.jsonl`
- this document

Local or CI-only artifacts for any future graph-eval experimentation must stay
under gitignored paths and must not be committed.

## Dataset Contract

Each offline record must contain exactly these required top-level fields:

- `id`
- `surface`
- `question`
- `reference_answer`
- `graph_context`
- `expected_claims`
- `reasoning_expectation`

### Surface enum

`surface` must be one of:

- `corpus_level_nutrition_summarization`
- `multi_hop_contraindication_reasoning`
- `plan_explainability`

### Graph context

`graph_context` must include:

- `nodes`
- `edges`

Each node must contain:

- `id`
- `type`
- `label`

Allowed node types:

- `foods`
- `nutrients`
- `conditions`
- `restrictions`
- `meal_templates`
- `guideline_concepts`

Each edge must contain:

- `source`
- `relation`
- `target`

Allowed edge relations:

- `contains`
- `rich_in`
- `contraindicated_for`
- `recommended_for`
- `substitutable_with`

### Expected claims

`expected_claims` is a non-empty `list[str]` that captures the grounded claims
the future evaluator should verify against the candidate answer.

### Reasoning expectation

`reasoning_expectation` must include:

- `kind`

Allowed kinds:

- `global_summary`
- `multi_hop`
- `comparative_explanation`

## Fixture Contract

The committed sample fixture is intentionally tiny and synthetic.

It must contain exactly three records:

- one for `corpus_level_nutrition_summarization`
- one for `multi_hop_contraindication_reasoning`
- one for `plan_explainability`

The fixture must not contain:

- live user data
- provider outputs
- runtime traces
- graph execution traces
- graph-specific scores or thresholds

## Provenance And Fail-Closed Rules

This contract inherits the selective GraphRAG ADR boundary:

- graph structure is not canonical truth by itself
- graph nodes and edges must stay attributable to approved structured inputs or
  cited evidence surfaces
- any future graph-eval artifact or schema input must fail closed when
  malformed and must not weaken shared AI guards or widen gate outcomes
- future graph-eval work must preserve provenance, source fingerprints, and
  fail-closed behavior
- no graph-eval lane is allowed to pull semantic cache forward or imply runtime
  graph retrieval

## Deferred Follow-Ups

Deferred to later, separately approved lanes only:

- graph-eval runner implementation
- graph-specific scoring
- graph-specific thresholds
- CI graph-eval reporting
- runtime GraphRAG retrieval
- semantic cache work

Those follow-ups must remain subordinate to the canonical release-gates lane
and must not create a second evaluation source of truth.
