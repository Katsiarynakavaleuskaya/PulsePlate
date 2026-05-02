# PulsePlate Eval Validity Contract

<!-- markdownlint-disable MD013 -->

## Purpose

Define the measurement-science substrate for deterministic evaluation
validity across PulsePlate's existing eval lanes (RAG release gates,
judgment replay, logic/philosophy replay, selective graph eval).

Validity metrics are a **sibling layer** to existing quality and release
metrics. They do not replace canonical release-gate PASS/NO-GO vocabulary.
They measure stability of conclusions under deterministic transformations.

## Scope

- Item-level outcome tracking with canonical/variant grouping.
- Invariance testing (format, evidence order, curated paraphrase).
- Benchmark mutation (missing evidence, distractor context).
- Worst-case error rate reporting per item group.
- Item instability detection and registry.
- Slice-level breakdown (per tag).

## Non-goals

- **No** psychometrics / IRT in this foundation PR.
- **No** mechanistic evaluation research.
- **No** adaptive self-improving eval loop.
- **No** LLM-generated fixtures.
- **No** runtime integration (API, frontend, iOS).
- **No** Claude / Opus provider integration.
- **No** semantic cache changes.
- **No** hybrid adjudication framework (deferred).

## Relationship to Existing Release Gates

This contract is a **sibling measurement contract**, not a replacement for
`docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`.

- Release gates own PASS/NO-GO decisions.
- Validity metrics own stability/robustness measurement.
- Validity metrics never override release-gate decisions.
- Future integration: release-gate runners may optionally export
  item-level artifacts that the validity runner can consume.

## Item / Variant Model

Each evaluation item has a `canonical_id`. Variants share the same
`canonical_id` but have unique `variant_id` values. Every variant belongs
to a `variant_family` and has a `transform_type`.

Schema: `scripts/evals/eval_validity_contract.py`
Version: `EVAL_VALIDITY_SCHEMA_VERSION = "1.0"`

## Variant Families

| Family | Purpose |
|--------|---------|
| `canonical` | Original unmodified item |
| `invariance` | Semantically equivalent transform (should yield same decision) |
| `mutation` | Controlled degradation (may yield different decision) |

## Expected Relations

| Relation | Meaning |
|----------|---------|
| `same_decision` | Variant must produce the same pass/fail as canonical |
| `same_grade_band` | Variant score must be in the same band |
| `controlled_drop` | Score may drop but within expected bounds |

## Metrics

| Metric | Definition |
|--------|-----------|
| `invariance_score` | Fraction of invariance variants agreeing with canonical |
| `mutation_drop` | Mean score drop from canonical to mutation variants |
| `worst_case_error_rate` | Max failure rate across any item group |
| `item_instability_index` | Fraction of items with at least one unstable variant |
| `slice_support` | Count of outcomes per slice tag |
| `unstable_items` | Sorted list of canonical_ids with decision disagreement |
| `slice_breakdown` | Per-slice pass rate and mean score |

## Artifact Format

The validity runner produces a JSON report:

```json
{
  "schema_version": "1.0",
  "invariance_score": 0.666667,
  "mutation_drop": {"overall": 0.6, "by_transform": {...}},
  "worst_case_error_rate": 0.666667,
  "item_instability_index": 0.5,
  "slice_support": {"rag": 7, "bmi": 4},
  "unstable_items": ["rag_retrieval_002"],
  "slice_breakdown": [...]
}
```

Output path: `artifacts/evals/validity_report.json` (gitignored).

## Determinism Rules

- Same JSONL input must always produce identical JSON output.
- Sorted keys in output. Stable ordering of lists.
- No random seeds, no timestamps in report.
- No network calls, no model invocations.
- Fail-fast on malformed input records.

## RAG Lane Integration

Current state: standalone. The RAG release-gate runner
(`scripts/evals/run_rag_release_gates.py`) does not yet export item-level
outcome JSONL. Future PR may add optional export of per-item results in
validity-compatible format.

## Judgment Lane Integration

Current state: standalone. The judgment eval
(`core/judgment_eval.py`) uses promote/defer/discard decisions. Future PR
may map judgment outcomes to validity `EvalOutcomeRecord` format.

## Security / Privacy Boundary

- All fixtures are synthetic and curated.
- No PII, no real user data, no API keys, no secrets.
- No network calls anywhere in the substrate.
- No provider routing changes.
- No `.claude/` directory.

## Rollout Plan

1. **PR-1 (this PR)**: Foundation substrate -- contract, runner, fixtures,
   tests, docs.
2. **PR-2 (deferred)**: Integration with RAG release-gate item-level
   artifacts.
3. **PR-3 (deferred)**: Integration with judgment eval outcome export.
4. **PR-4+ (deferred)**: Psychometrics / IRT, adaptive evals, hybrid
   adjudication, tool-use reliability.

## Deferred Follow-ups

- Hybrid adjudication framework.
- Tool-use reliability metrics.
- Psychometrics / IRT item modeling.
- Compositional generalization suites.
- Mechanistic evaluation research lane.
- Adaptive self-improving eval loop.
- RAG release-gate item-level export integration.
- Judgment eval outcome export integration.

## Decision Log

1. Validity metrics are sibling metrics, not replacements for release gates.
2. Item-level artifacts are required before IRT, psychometrics, or adaptive
   evals.
3. Foundation eval fixtures must be deterministic and curated (no LLM
   generation).
4. TypedDict chosen over dataclass for record schemas (repo convention).
5. Tests placed in `tests/evals/` following existing eval-test convention.
6. Opus/Claude used only as operator coding model, never integrated into
   runtime or orchestration identity.
