# ADR: Selective GraphRAG Contract for Nutrition Reasoning (2026-04-22)

- Status: Accepted (docs-only contract)
- Date: 2026-04-22
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane`

## Context

PulsePlate now has a canonical internal evaluation lane for RAG quality and a
companion report-only RAGAS bootstrap. What it does not yet have is one
explicit architecture contract that says where GraphRAG is justified, where it
is not justified, and how it must stay subordinate to the existing evidence and
evaluation spine.

Repo evidence already points away from "GraphRAG everywhere":

- the canonical release-gates lane owns threshold vocabulary, gate checks, and
  `PASS` / `NO-GO` semantics in
  `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
- the companion RAGAS lane is explicitly report-only and subordinate in
  `docs/evals/RAGAS_SETUP.md`
- semantic cache remains a deferred optimization gate in
  `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- the broader architecture direction favors a proof-first evidence spine before
  graph or cache widening

This ADR exists to freeze that boundary before any future graph-specific design
or implementation lane starts.

## Decision

PulsePlate adopts a **selective GraphRAG contract**, not a general GraphRAG
retrieval strategy.

GraphRAG is justified only for future nutrition reasoning surfaces that need
graph structure to add value beyond the existing non-graph evidence spine:

1. corpus-level nutrition summarization
2. multi-hop contraindication reasoning
3. explainability for "why this plan, not another"

GraphRAG is explicitly **not** authorized by default for:

- food lookup
- barcode lookup
- simple meal generation
- default retrieval for ordinary insight flows
- a replacement for the canonical release-gates lane
- semantic cache or any cache-opening work
- provider behavior or request-path changes

This is a docs-only architecture contract. It does not authorize runtime
GraphRAG rollout, graph-specific CI thresholds, or a new product-facing
evaluation rail.

## Starter Graph Boundary

Any future bounded graph lane must stay within the following starter schema
unless a later ADR explicitly widens it.

The starter graph is a normalized concept layer over the current PulsePlate
evidence spine, not a new source-of-truth surface. In current repo terms,
`foods` and `meal_templates` map most directly to the existing nutrition and
meal-planning domain entities already exercised in `core/food_db.py`,
`core/recipe_synth.py`, and `core/daily_plate.py`; `nutrients` map to the
structured nutrient concepts already carried through those same nutrition
surfaces; and `conditions`, `restrictions`, and `guideline_concepts` map to
the cited domain concepts already represented across guarded nutrition logic
and evaluation corpora such as `core/dietary_constraints.py`,
`core/nutrition_bayesian_analyzer.py`, and the release-gates / companion-eval
docs datasets. Future edges such as `contains`, `rich_in`, or
`contraindicated_for` may normalize relationships across those evidence
surfaces, but every relationship must still be attributable back to cited
evidence or approved structured inputs.

### Nodes

- `foods`
- `nutrients`
- `conditions`
- `restrictions`
- `meal_templates`
- `guideline_concepts`

### Edges

- `contains`
- `rich_in`
- `contraindicated_for`
- `recommended_for`
- `substitutable_with`

This bounded schema is intentionally conservative. Nutrition reasoning may later
need higher-arity facts, but this ADR does not authorize modeling beyond the
starter boundary. Any later widening must come through a separate ADR that
defines source modeling and provenance semantics explicitly.

## Routing and Provenance Contract

The default path remains the existing non-graph evidence spine:

- canonical release-gates ownership for threshold and gate semantics
- current bounded runtime orchestration without a default graph path
- companion RAGAS metrics only as report-only informational surfaces

A future graph path is allowed only for selective multi-hop or global questions.
It must never become the implied default retrieval path.

Any future GraphRAG implementation must preserve repo fail-closed behavior:

- no bypass of shared input and safety guards
- no bypass of evidence selection and source attribution
- no graph-derived answer treated as canonical truth without provenance
- no graph path that weakens existing release-gates or runtime safety policy

No future graph lane is authorized by this ADR to bypass current runtime
preparation or orchestration seams, widen `app/**`, `core/**`, or `llm.py`,
or introduce new route, DTO, or OpenAPI truth without a later separately
approved bounded PR opening that scope.

Provenance remains first-class. Any later graph slice must keep source
fingerprints, citation-chain completeness, and explicit source-of-truth
boundaries instead of treating graph structure itself as canonical knowledge.

## Evaluation and Governance Boundary

This ADR does not create a graph-evaluation rail.

The canonical owners remain:

- `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md` for threshold vocabulary, gate
  semantics, and release decisions
- `docs/evals/RAGAS_SETUP.md` for the companion local report-only RAGAS surface

Deferred follow-up only:

- graph-specific evaluation design
- graph-specific artifacts or thresholds
- graph-aware runtime retrieval slices
- separately approved semantic-cache work under its own existing gate

Any future graph-eval work must remain subordinate to the canonical
release-gates lane and cannot redefine `PASS` / `NO-GO` ownership.

## Exit Criteria

This contract should remain in force until all are true:

1. the evidence and evaluation spine remains the accepted default for RAG
   quality decisions
2. any future graph work appears only through a later separately approved
   bounded lane and does not widen into default retrieval
3. graph-specific evaluation follows the existing release-gates governance
   instead of inventing a second canonical rail
4. semantic cache remains governed by its own gate and is not pulled forward by
   graph work

## Consequences

- Positive: GraphRAG is framed as a selective reasoning tool instead of an
  architecture default
- Positive: enterprise/demo narrative becomes clearer because explainability and
  contraindication reasoning are the named graph targets
- Positive: future graph work is forced to keep provenance and fail-closed
  boundaries explicit
- Negative: some useful graph ideas remain deferred until a later bounded lane
  proves they fit the canonical evidence/eval spine
