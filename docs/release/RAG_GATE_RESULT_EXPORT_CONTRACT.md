# RAG Gate Result Export Contract

**Schema version:** `release-rag-gate-result.v1`
**Release-control-plane slice:** PR-2, `release/release-control-plane-pr2-rag-gate-export`
**Schema:** [`RAG_GATE_RESULT_EXPORT_CONTRACT.schema.json`](RAG_GATE_RESULT_EXPORT_CONTRACT.schema.json)

## Purpose

This contract defines the ML identity portion of the internal release packet.
It is produced by the existing RAG release-gates runner and keeps
`scripts/evals/run_rag_release_gates.py` as the only source of truth for RAG
gate execution, thresholds, gate checks, and the `PASS` / `NO-GO` eval
decision.

PR-2 does not add the final `ALLOW` / `BLOCK` release decision. That remains
scoped to the later release manifest and CI decision slices.

## Output Artifact

The runner writes `rag_gate_result.json` under the existing gitignored run
directory:

```text
artifacts/rag_eval/<experiment_id>/rag_gate_result.json
```

The artifact is generated beside the existing `metrics_summary.json`,
`gate_report.md`, `traces.jsonl`, flat trace export, and executed notebook.
Generated paths inside the export are run-directory-relative and must not
contain absolute local filesystem paths.

## Hash Fields

| Field | Source | Format |
| --- | --- | --- |
| `rag_gate_result_hash` | Canonical JSON export payload excluding this self-hash | SHA-256 lowercase hex, no prefix |
| `eval_artifact_hash` | Canonical JSON manifest of safe eval artifact file hashes | SHA-256 lowercase hex, no prefix |

JSON canonicalization uses sorted keys, compact separators, UTF-8 bytes, and
exactly one trailing LF. Hash fields are lowercase 64-character SHA-256
hexadecimal without a `sha256:` prefix.

## Contract Payload

The deterministic export includes:

```json
{
  "schema_version": "release-rag-gate-result.v1",
  "hash_algorithm": "sha256",
  "canonicalization": "json-sorted-compact-utf8-single-trailing-newline",
  "rag_gate_result_hash": "<64 lowercase hex>",
  "eval_artifact_hash": "<64 lowercase hex>",
  "release_decision": "PASS",
  "gate_checks": {},
  "threshold_results": [],
  "strict_violations": [],
  "runtime_warnings": [],
  "dataset_path_used": "data/evals/pulseplate_rag_eval_sample.jsonl",
  "dataset_fallback_used": false,
  "sample_size": 4,
  "git_sha": "<git sha>",
  "retriever_mode": "local_tfidf",
  "generator_mode": "extractive_stub",
  "source_artifacts": []
}
```

`mlflow_run_id` and `model_version` are reserved optional fields. The runner
emits them only when a future explicitly scoped integration supplies non-empty
values in the metrics summary.

## Boundaries

This PR-2 contract does not:

- change RAG retrieval, generation, thresholds, calibration, or route behavior;
- create a product dashboard or second eval source of truth;
- upload artifacts outside the existing GitHub Actions artifact mechanism;
- read secrets, provider credentials, App Store credentials, or protected
  release environments;
- generate the final release manifest;
- produce the release-control-plane `ALLOW` / `BLOCK` decision.
