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

The RAG release-gate runner (`scripts/evals/run_rag_release_gates.py`) emits
validity sidecar artifacts via `scripts/evals/rag_release_gate_validity.py`.
Each RAG trace is mapped to an `EvalOutcomeRecord` with per-item pass/fail
derived from the same gate B1/B2/B3 thresholds.

Current limitations: only `variant_family="canonical"` rows are emitted.
Full invariance/mutation coverage requires explicit variant families in
future datasets and is not inferred from canonical-only rows.

Sidecar artifacts remain sibling artifacts and do not override the canonical
RAG release-gate PASS/NO-GO decision.

## Judgment Lane Integration

Current state: **sidecar integrated** (PR-3).

The FitChef judgment replay eval runner (`scripts/orchestration/judgment_eval.py`)
now emits optional validity sidecar artifacts alongside the canonical decision
artifact:

- `judgment_validity_items.jsonl` -- one `EvalOutcomeRecord` per evaluated case.
- `judgment_validity_report.json` -- the validity report built from those outcomes.

### Decision-to-outcome mapping

| Judgment decision | `passed` | `score` | Rationale |
|-------------------|----------|---------|-----------|
| `promote` | `True` | `1.0` | Fully supported, safe to surface. |
| `defer` | `True` | `0.5` | Safe but under-supported; not a failure. |
| `discard` | `False` | `0.0` | Failed safety or evidence checks. |

The `decision` field in each `EvalOutcomeRecord` carries the original judgment
string (`"promote"` / `"defer"` / `"discard"`), not a pass/fail label.

Slice tags include `"judgment"`, the `boundary_class` value, and `"hard_fail"`
when hard-fail reasons are present.

### Limitations

Current judgment replay sidecar datasets (emitted by `judgment_eval.py`) contain
only canonical items. The validity report from sidecar-emitted data shows
`invariance_score=0.0` and `mutation_drop.overall=0.0` for canonical-only data.

### Judgment Invariance and Mutation Fixtures (PR-4a)

Curated deterministic variant fixture set at
`data/evals/pulseplate_judgment_eval_validity_variants.jsonl` provides
canonical, invariance, and mutation families so the validity report measures
robustness instead of canonical-only coverage.

Fixture families:

- **canonical** -- one canonical row per group; baseline decision and score.
- **invariance** -- semantically equivalent variants (format_rewrite,
  context_order, surface_rewrite); expected relation: `same_decision`.
- **mutation** -- controlled degradation variants (missing_evidence,
  partial_support, contradicted_evidence, unsupported_claim, distractor_context,
  absent_evidence); expected relation: `controlled_drop`.

Slice tags cover `claim_type:*`, `support_status:*`, `evidence_mode:*`,
`invariance`, and `mutation` for fine-grained breakdown.

**Limitations:**

- These are deterministic curated fixtures, not LLM-generated paraphrases.
  They measure a limited surface and are not proof of full production robustness.
- Canonical-fail invariance groups (PR-5) add at least one canonical row with
  `decision: "fail"` and invariance rows that preserve the failing decision.
  This tests fail-to-fail stability alongside the existing pass-to-pass coverage.
- `invariance_score` is 1.0 for this fixture set because all invariance rows
  match their canonical decision. Tests assert `> 0.0` to catch canonical-only
  regressions but will not flag a drop from 1.0 to 0.8 as a failure.
- Canonical-fail invariance fixtures are deterministic negative-control
  measurement inputs. They test whether known-failing canonical outcomes remain
  failing under semantically equivalent transformations. They do not modify
  judgment taxonomy, claim-to-evidence records, uncertainty split, or canonical
  promote/defer/discard decisions.

### Invariant

Judgment validity sidecar artifacts are informational measurement artifacts.
They do not override claim taxonomy, claim-to-evidence records, uncertainty
split, or canonical promote/defer/discard decisions.

## Security / Privacy Boundary

- All fixtures are synthetic and curated.
- No PII, no real user data, no API keys, no secrets.
- No network calls anywhere in the substrate.
- No provider routing changes.
- No `.claude/` directory.

## Rollout Plan

1. **PR-1 (merged, #1632)**: Foundation substrate -- contract, runner,
   fixtures, tests, docs.
2. **PR-2 (current, #1648)**: RAG release-gate validity sidecar --
   item-level artifacts emitted via adapter.
3. **PR-3 (merged, #1656)**: Judgment replay validity sidecar -- item-level
   artifacts emitted via adapter, CLI wiring with graceful degradation.
4. **PR-4a (merged, #1657)**: Judgment invariance and mutation fixture families --
    deterministic curated variant fixtures for robustness measurement.
5. **PR-4b (current)**: RAG release-gate invariance and mutation fixture families --
    deterministic curated variant fixtures for RAG validity robustness measurement.
6. **PR-5+ (deferred)**: Psychometrics / IRT, adaptive evals, hybrid
    adjudication, tool-use reliability.

### RAG Release-Gate Invariance and Mutation Fixtures (PR-4b)

Curated deterministic variant fixture set at
`data/evals/pulseplate_rag_release_gate_validity_variants.jsonl` provides
canonical, invariance, and mutation families so the RAG validity report measures
robustness instead of canonical-only coverage.

Fixture families:

- **canonical** -- one canonical row per group; baseline decision and score.
- **invariance** -- semantically equivalent variants (format_rewrite,
  query_surface, evidence_order); expected relation: `same_decision`.
- **mutation** -- controlled degradation variants (missing_evidence,
  partial_support, distractor_context, contradicted_evidence, absent_evidence,
  degraded_retrieval); expected relation: `controlled_drop`.

Slice tags cover `evidence_exact_match:*`, `support_status:*`, `gate_b1`,
`gate_b2`, `gate_b3`, `invariance`, and `mutation` for fine-grained breakdown.

**Limitations:**

- These are deterministic curated fixtures, not LLM-generated paraphrases.
  They measure a limited surface and are not proof of full production robustness.
- Canonical-fail invariance groups (PR-5) add at least one canonical row with
  `decision: "fail"` and invariance rows that preserve the failing decision.
  This tests fail-to-fail stability alongside the existing pass-to-pass coverage.
- `invariance_score` is 1.0 for this fixture set because all invariance rows
  match their canonical decision. Tests assert `> 0.0` to catch canonical-only
  regressions but will not flag a drop from 1.0 to 0.8 as a failure.
- Canonical-fail invariance fixtures are deterministic negative-control
  measurement inputs. They test whether known-failing canonical outcomes remain
  failing under semantically equivalent transformations. They do not modify
  RAG release-gate thresholds, threshold_results, or canonical PASS/NO-GO
  decisions.

## Evaluation Item Metadata Registry

The item metadata registry (`data/evals/eval_item_metadata_registry.jsonl`) is
a **psychometric-readiness layer**.  It records stable item metadata for future
item weighting, IRT, and adaptive eval design, but it **does not implement
psychometric scoring** and **does not change validity metrics, RAG release-gate
decisions, or judgment decisions**.

Registry contract: `scripts/evals/eval_item_registry.py`

### Schema

Each registry row is an `EvalItemMetadataRecord` with these fields:

- `canonical_id` -- matches fixture canonical_id exactly.
- `lane` -- `"rag"` or `"judgment"`.
- `domain` -- e.g., `"claim_support"`, `"release_gate"`.
- `skill_dimension` -- e.g., `"claim_support"`, `"retrieval_faithfulness"`,
  `"hard_fail_detection"`, `"degraded_retrieval"`.
- `difficulty_band` -- `"low"`, `"medium"`, `"high"` (heuristic label, not
  calibrated IRT estimate).
- `expected_decision` -- must match canonical fixture row decision.
- `expected_score_band` -- `"fail"`, `"partial"`, `"pass"`.
- `variant_family_coverage` -- actual variant families for this canonical_id.
- `anchor_item` -- `true` for stable representative items per lane.
- `source_fixture` -- filename of the source JSONL fixture.
- `notes` -- human-readable notes; no IRT claims.

### Coverage rules

- Exactly one row per canonical_id across all variant fixtures.
- No orphan registry rows (every registry canonical_id must be in a fixture).
- No missing fixture canonical_ids (every fixture canonical_id must be in the
  registry).

### Limitations

- Difficulty bands are explicit heuristic labels derived from observable score
  patterns, not calibrated psychometric difficulty parameters.
- The registry does not implement IRT, item information functions, or adaptive
  item selection.
- The registry does not override EvalOutcomeRecord data or validity metrics.

### Future follow-up

- IRT / item information modeling (requires empirical run data).
- Item weighting based on registry metadata.
- Adaptive item selection using registry anchors.

## Deferred Follow-ups

- Hybrid adjudication framework.
- Tool-use reliability metrics.
- Psychometrics / IRT item modeling.
- Compositional generalization suites.
- Mechanistic evaluation research lane.
- Adaptive self-improving eval loop.
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
