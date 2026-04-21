# PulsePlate RAGAS Companion Bootstrap

## Purpose
- This lane adds a narrow offline `evals/ragas/*` companion bootstrap for
  report-only RAGAS scoring.
- It is intentionally subordinate to the canonical release-gates lane in
  `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`.
- It does not change runtime behavior, request-path logic, provider selection, or CI gate policy.

## Boundary From Release-Gates
- `scripts/evals/run_rag_release_gates.py` remains the canonical CI-friendly release-gates runner.
- `evals/ragas/run_ragas_eval.py` is a local report-only companion surface for
  curated RAGAS metrics.
- This companion lane does not own threshold vocabulary such as `PASS`, `NO-GO`,
  or canonical gate semantics.
- If you need canonical runtime-grounded release evidence, use the release-gates lane instead.

## Scope
- Dataset inspiration surface: `/api/v1/pro/cbt/insight`
- Dataset ownership: local curated CBT-first offline JSONL only
- Metrics:
  - `faithfulness`
  - `answer_relevancy`
  - `context_precision`
- Report mode: report-only

## Hard Rules
- Do not import `evals/` from `app/`, `core/`, `frontend/`, or `ios/`
- Do not add `ragas` or `datasets` to `requirements.txt` or `requirements-dev.txt`
- Keep `ragas` imports lazy inside the runner entrypoint
- Do not call live providers or runtime routes from this lane
- Do not claim a second canonical evaluation source of truth beside
  `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
- Keep outputs out of tracked repo paths by default

## Dataset Contract
Each JSONL row must include:

```json
{
  "question": "How can I reduce evening snacking?",
  "answer": "Candidate answer already chosen for offline scoring",
  "contexts": [
    "Relevant CBT or psychology chunk 1",
    "Relevant CBT or psychology chunk 2"
  ],
  "reference": "Expected grounded answer"
}
```

Accepted reference keys:
- `reference`
- `ground_truth`

Notes:
- `answer` is the candidate answer being scored offline.
- `reference` or `ground_truth` is the expected grounded answer.
- If both `reference` and `ground_truth` are present in one row, they must match.
- `contexts` must stay a non-empty `list[str]`.
- Only synthetic or curated content is allowed in the committed dataset.

## Installation
```bash
pip install -r requirements-evals.txt
```

## Usage
```bash
python -m evals.ragas.run_ragas_eval \
  --dataset evals/ragas/testset.jsonl \
  --output-json artifacts/rag_eval/ragas_bootstrap_manual/metrics_summary.json \
  --output-md artifacts/rag_eval/ragas_bootstrap_manual/ragas_summary.md
```

Default output is stdout only. Optional file outputs may reuse the existing
gitignored `artifacts/rag_eval/<experiment_id>/...` family, but this companion
lane does not redefine that artifact contract.

## Output Contract
Stdout prints a deterministic Markdown summary:

```text
Metric | Score
--- | ---:
faithfulness | 0.84
answer_relevancy | 0.79
context_precision | 0.88
```

Optional JSON output shape:

```json
{
  "dataset_path": "evals/ragas/testset.jsonl",
  "sample_count": 12,
  "report_only": true,
  "metrics": {
    "faithfulness": 0.84,
    "answer_relevancy": 0.79,
    "context_precision": 0.88
  }
}
```

## Validation
```bash
pytest -q tests/evals/test_ragas_dataset_contract.py
pytest -q tests/evals/test_ragas_metrics_config.py
pytest -q tests/evals/test_ragas_runner_contract.py
```
