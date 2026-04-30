# PulsePlate RAG Release Gates

**Status:** v1 internal evaluation lane
**Effective date:** 2026-04-20 (`America/New_York`)
**Canonical notebook:** [`notebooks/pulseplate_rag_release_gates.ipynb`](../../notebooks/pulseplate_rag_release_gates.ipynb)
**Canonical runner:** [`scripts/evals/run_rag_release_gates.py`](../../scripts/evals/run_rag_release_gates.py)
**Lane packet:** [`docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md`](../orchestration/PULSEPLATE_RAG_RELEASE_GATES_TASK_PACKET_2026-04-20.md)
**Follow-up packet:** [`docs/orchestration/PULSEPLATE_RAG_RELEASE_GATES_THRESHOLD_REPORTING_TASK_PACKET_2026-04-22.md`](../orchestration/PULSEPLATE_RAG_RELEASE_GATES_THRESHOLD_REPORTING_TASK_PACKET_2026-04-22.md)
**Ledger anchor:** [`ledger-p1-rag-release-gates-lane`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane)

## Purpose

This lane integrates the delivered notebook as an **internal release-gate / evaluation tool**
for PulsePlate RAG and Insight quality. It is not a product-facing dashboard and it does not
introduce new runtime truth for user-facing surfaces.

Primary value:

- catch regressions in retrieval, grounding, philosophy validation, and calibration before merge or release
- produce repeatable weekly / PR evidence using real PulsePlate hooks when available
- preserve a cheap offline smoke mode for routine CI
- define a stable trace/run schema that can later be mirrored into PostgreSQL without changing evaluation logic

## Why This Exists

The repo already has:

- real RAG orchestration via `core.rag.orchestration.retrieve_and_validate_rag(...)`
- real runtime preparation via `core.ai.prepare_insight_runtime(...)`
- traced app-layer execution via `app.services.insight_runtime.generate_traced_insight(...)`
- deterministic input and output safety guards via:
  - `app.security.agent_input_guard.scan_ai_agent_input(...)`
  - `core.insight.philosophy_validator.validate_llm_output(...)`

What the repo did **not** have was a canonical release-gate lane tying these surfaces together
into a deterministic artifact pack that can be used in CI and weekly evaluations.

## Repo Layout

Committed inputs and contracts:

- `notebooks/pulseplate_rag_release_gates.ipynb`
- `data/evals/pulseplate_rag_eval_sample.jsonl`
- `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
- `scripts/evals/run_rag_release_gates.py`

Local / CI-only artifacts:

- `artifacts/rag_eval/<experiment_id>/traces.jsonl`
- `artifacts/rag_eval/<experiment_id>/metrics_summary.json`
- `artifacts/rag_eval/<experiment_id>/gate_report.md`
- `artifacts/rag_eval/<experiment_id>/latest_executed.ipynb`
- optional: `artifacts/rag_eval/<experiment_id>/traces.parquet`
- fallback when Parquet is unavailable: `artifacts/rag_eval/<experiment_id>/traces.csv`

`artifacts/rag_eval/` is gitignored and must never be committed.

## Execution Modes

### v1 cheap deterministic gate

- `RETRIEVER_MODE=local_tfidf`
- `GENERATOR_MODE=extractive_stub`

Properties:

- no paid provider calls
- safe for routine CI and local smoke
- local corpus built from repo files under `docs/`, `core/`, `app/`, `tests/guards/`, `AGENTS.md`, and `RUNBOOK_AGENT.md`

### v1 strict runtime lane

- `RETRIEVER_MODE=pulseplate`
- `GENERATOR_MODE=pulseplate_runtime`

Properties:

- exercises real PulsePlate orchestration and runtime hooks when imports/env are available
- still uses an offline eval stub provider for generation to avoid paid provider calls
- can fall back to the cheap deterministic path for exploratory local runs
- canonical weekly/manual CI should add `--disallow-dataset-fallback --disallow-runtime-fallbacks --require-pass`

### Canonical small-fixture advisory (weekly default input)

When the dataset basename is `pulseplate_rag_eval_sample.jsonl` and the evaluated trace count is at most 16 (constant `SMALL_FIXTURE_NUMERIC_GATES_ADVISORY_MAX_N` in `scripts/evals/run_rag_release_gates.py`):

- Gates `gate_a_recall_at_effective_k`, `gate_b1_evidence_exact_match`, `gate_b2_mean_nli_entailment`, `gate_b3_support_precision`, and `gate_c2_escalation_corridor` are **advisory-only** (reported as PASS in `gate_checks` so `--require-pass` can succeed on the committed tiny fixture).
- Raw pass/fail for those gates before the override is stored in `metrics_summary.json` under `small_fixture_raw_gate_checks`.
- `gate_c1_ece` and `gate_d1_no_runtime_mode_fallbacks` stay **strict** (calibration and runtime-fallback hygiene).
- In `metrics_summary.json`, `threshold_results[].passed` reflects **post-advisory** `gate_checks` (so A/B/C2 rows may show `passed: true` while `small_fixture_raw_gate_checks` records the raw outcome). Automated consumers should use `small_fixture_metric_gates_advisory` plus `small_fixture_raw_gate_checks` when present.

Rationale: aggregate retrieval and faithfulness thresholds, and the escalation-rate corridor, are not statistically meaningful on a handful of rows; the weekly lane still exercises real `pulseplate` / `pulseplate_runtime` imports and fail-closed strict flags.

## Dataset Contract

Environment variable:

- `PULSEPLATE_RAG_EVAL_INPUT`

Supported input formats:

- `.jsonl`
- `.csv`
- `.parquet`

Expected columns:

| Column | Required | Meaning |
|---|---:|---|
| `query_id` | no | Stable query identifier; generated if absent |
| `query_text` | yes | User-like prompt/query |
| `gold_doc_ids` | recommended | Expected doc IDs or path fragments |
| `gold_answer` | recommended | Reference answer |
| `expected_claims` | optional | Expected answer claims |
| `evidence_quotes` | optional | Exact snippets expected in retrieved evidence or answer |
| `user_tier` | optional | `FREE` / `PRO` / `VIP` routing metadata |
| `subject_id` | optional | Tenant/user ID for real retrieval paths |
| `human_label_if_any` | optional | `1` correct / `0` incorrect for calibration |

For repo v1, the full weekly 500-query dataset is **not committed**. Only the sample
fixture and the schema contract live in git.

## Guard and Safety Contract

Before retrieval or generation:

- AI-facing input must pass `scan_ai_agent_input(...)` when available
- unsafe inputs fail closed and are marked `blocked_by_agent_input_guard`

After generation:

- output is checked with `validate_llm_output(...)` when available
- blocker findings contribute to calibration/routing and release gating

This lane must not bypass the shared AI input guard or weaken the repo’s fail-closed policy.

## Metrics and Gates

Retrieval metrics:

- `recall_at_3`
- `recall_at_10`
- `recall_at_50`
- `mrr_at_10`
- `ndcg_at_10`

Faithfulness metrics:

- `evidence_exact_match_rate`
- `mean_nli_entailment`
- `support_precision`

Calibration metrics:

- temperature scaling
- `ece`
- `brier`
- calibrated confidence

Routing metrics:

- escalation rate
- blocked-by-guard rate
- ship-candidate rate

Initial thresholds:

```python
GATE_THRESHOLDS = {
    "evidence_exact_match_rate": 0.70,
    "mean_nli_entailment": 0.85,
    "support_precision": 0.80,
    "ece": 0.08,
    "escalation_min": 0.10,
    "escalation_max": 0.25,
    "recall_at_50": 0.80,
}
```

Release decision:

- `PASS`
- `NO-GO`

The runner does not fail the process on `NO-GO` unless explicitly asked via `--require-pass`.
This keeps PR smoke deterministic while still surfacing release-gate evidence.
Strict weekly/manual runs should also disable dataset/runtime fallbacks.

## Schema Contract

### Run-level schema

Canonical fields:

- `experiment_id`
- `timestamp`
- `git_sha`
- `retriever_mode`
- `generator_mode`
- `sample_size`
- `thresholds`
- `threshold_results`
- `gate_checks`
- `release_decision`
- optional `companion_metrics`

### Trace-level schema

Canonical fields:

- `trace_id`
- `query_id`
- `query_text`
- `user_context_hash`
- `top_k_retrieved`
- `retrieval_stats`
- `generator_output`
- `extracted_claim_spans`
- `per_span_entailment_score`
- `support_flags`
- `generator_logprob`
- `confidence`
- `post_hoc_calibrated_confidence`
- `routing_decision`
- `latency`
- `human_label_if_any`

This schema contract is the intended bridge between:

- artifact JSONL produced by the runner
- future PostgreSQL summary / trace tables

The goal is to avoid a future dashboard migration that re-implements evaluation logic.

## Companion Artifact Bridge

The release-gates lane remains the canonical owner of threshold vocabulary,
gate checks, and `PASS` / `NO-GO` release decisions.

Optional companion RAGAS artifacts are informational only and must not change:

- `thresholds`
- `threshold_results`
- `gate_checks`
- `release_decision`
- `--require-pass`

When provided, the companion artifact must already exist as a local JSON artifact
under the gitignored `artifacts/rag_eval/<experiment_id>/...` family. The
canonical runner may ingest it for reporting, but it does not execute `ragas`
itself and it does not become a second eval source of truth.

Future selective graph-eval work is also subordinate to this lane. The offline
contract in
[`PULSEPLATE_SELECTIVE_GRAPH_EVAL_CONTRACT.md`](./PULSEPLATE_SELECTIVE_GRAPH_EVAL_CONTRACT.md)
may define graph-question fixture/schema inputs, but it must not redefine:

- threshold vocabulary
- `threshold_results`
- gate checks
- `PASS` / `NO-GO`
- release decisions
- `--require-pass`

## Storage Model

### v1 source of truth

The source of truth for run output is the gitignored artifact pack under:

- `artifacts/rag_eval/<experiment_id>/`

PR / CI visibility:

- upload only the safe artifact subset:
  - `gate_report.md`
  - `metrics_summary.json`
  - `rag_gate_result.json`
  - `latest_executed.ipynb`
- write a compact markdown summary to the CI check summary / PR check output
- surface deterministic threshold rows in both the markdown report and the CI summary
- include companion RAGAS metrics only as an informational block when explicitly provided

### Release-control-plane export

The runner also emits `rag_gate_result.json` for the release-control-plane
ML identity contract. The schema and hash rules live in
[`../release/RAG_GATE_RESULT_EXPORT_CONTRACT.md`](../release/RAG_GATE_RESULT_EXPORT_CONTRACT.md).
This export is derived from the existing runner output and does not redefine
threshold vocabulary, gate checks, `PASS` / `NO-GO`, or `--require-pass`.

### v2 persistence

If longer-lived history is needed beyond CI retention:

- persist **summary-level** evaluation history into the existing PostgreSQL path
- keep Cloudflare as an optional edge/access layer only
- preferred future topology: Worker + Hyperdrive -> PostgreSQL

### Explicit non-goal

Do **not** use Cloudflare D1 for this lane.

Reason:

- repo runtime truth is already PostgreSQL-oriented
- D1 reintroduces SQLite semantics and unnecessary storage split-brain
- eval history should not create a second canonical operational store

## How To Run

Cheap smoke:

```bash
python3 scripts/evals/run_rag_release_gates.py \
  --input-path data/evals/pulseplate_rag_eval_sample.jsonl \
  --retriever-mode local_tfidf \
  --generator-mode extractive_stub
```

Optional local composition with a precomputed companion RAGAS artifact:

```bash
python3 scripts/evals/run_rag_release_gates.py \
  --input-path data/evals/pulseplate_rag_eval_sample.jsonl \
  --retriever-mode local_tfidf \
  --generator-mode extractive_stub \
  --companion-metrics-json artifacts/rag_eval/ragas_bootstrap_manual/metrics_summary.json
```

Stricter local lane:

```bash
PULSEPLATE_RAG_EVAL_INPUT=${PULSEPLATE_RAG_EVAL_INPUT:-data/evals/pulseplate_rag_eval_sample.jsonl} \
RETRIEVER_MODE=pulseplate \
GENERATOR_MODE=pulseplate_runtime \
ENABLE_NLI_MODEL=true \
NLI_MODEL_NAME=roberta-large-mnli \
python3 scripts/evals/run_rag_release_gates.py \
  --require-pass \
  --disallow-dataset-fallback \
  --disallow-runtime-fallbacks
```

Notebook execution remains available for analyst-facing review:

```bash
EXPERIMENT_ID=${EXPERIMENT_ID:-manual_notebook_review} \
PULSEPLATE_RAG_EVAL_INPUT=${PULSEPLATE_RAG_EVAL_INPUT:-data/evals/pulseplate_rag_eval_sample.jsonl} \
RETRIEVER_MODE=local_tfidf \
GENERATOR_MODE=extractive_stub \
jupyter nbconvert --to notebook --execute notebooks/pulseplate_rag_release_gates.ipynb \
  --output-dir "artifacts/rag_eval/${EXPERIMENT_ID}" \
  --output latest_executed.ipynb
```

For the strict weekly/manual GitHub lane, inject a larger curated dataset through
the `workflow_dispatch` input `eval_input_path` or the repo variable
`PULSEPLATE_RAG_EVAL_INPUT`; when neither is set, the workflow falls back to the
tracked sample fixture so the lane remains deterministic and runnable from a
clean repo checkout.

## CI Guidance

v1 CI split:

- cheap smoke on the sample fixture by default
- stricter weekly/manual lane for broader datasets and stricter modes

The sample smoke proves:

- runner completes
- artifact pack is emitted
- no paid provider path is required
- threshold reporting is surfaced deterministically

It does **not** claim release readiness by itself.

The PR smoke lane remains advisory/reporting-only. The weekly/manual lane remains
the canonical strict execution path and is the only GitHub path that should pair
this runner with `--require-pass`.

## Security Notes

- Eval artifacts remain local/CI-only and must never be committed
- Avoid storing raw user context or PII; use minimized or hashed identifiers
- If PostgreSQL persistence is added later, store operationally useful summary/trace fields only
- Cloudflare must not become a second storage truth for evaluation history

## Non-goals for v1

- no user-facing dashboard
- no Figma design work
- no Linear automation
- no product marketing surface changes
- no Cloudflare-native metrics database

The lane is intentionally **internal-gates first**.
