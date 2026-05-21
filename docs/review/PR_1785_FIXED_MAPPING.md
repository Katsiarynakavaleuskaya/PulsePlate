# PR #1785 Fixed in Commit Mapping

## Scope

This PR keeps MLflow identity optional for the RAG/ML gate result export and
defers any external MLflow-backed required check to a future governed slice.

## Discussion Thread Pass

- Initial PR open: no GitHub review threads were resolved before this artifact
  was created.
- New review comments must be dispositioned as `FIXED`, `NOT-A-BUG`, or
  `DEFERRED` before resolution.
- Mapping updates must follow code/docs/test fixes, not precede them.

## Fixed in Commit Mapping

### Implementation

- Commit: `e6b081248`
- Disposition: `FIXED`
- Evidence:
  - `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md` documents that external
    MLflow runs are not required PR checks and that repo-native artifacts remain
    canonical.
  - `docs/release/RAG_GATE_RESULT_EXPORT_CONTRACT.md` documents that
    `mlflow_run_id` and `model_version` are optional identity fields only.
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-mlflow-required-check-integration`
    tracks the future MLflow integration criteria.
  - `tests/test_rag_release_gates_runner.py` proves empty MLflow identity is not
    emitted, non-empty identity is schema-constrained, `rag_gate_result_hash`
    changes with identity, `eval_artifact_hash` stays stable, and gate truth
    fields are unchanged.

## Premortem / Role Findings

| Finding | Disposition | Evidence |
| --- | --- | --- |
| External MLflow required check could become a flaky secret/network merge blocker. | FIXED | MLflow required-check status is explicitly rejected in docs and deferred in the ledger. |
| MLflow metrics could become a second source of eval truth. | FIXED | Release contract preserves `threshold_results` and `release_decision` as canonical. |
| Bug-hunter found missing schema/hash negative control for MLflow identity. | FIXED | `tests/test_rag_release_gates_runner.py` now asserts schema properties, required-field absence, hash behavior, and unchanged gate truth. |

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py ...`
- `python3 scripts/orchestration/experiment_bootstrap.py ...`
- Experiment Runner oracle-only result:
  `artifacts/orchestration/experiments/results/exp-7ee534b920ff.json`
- `. .venv/bin/activate && pytest -q tests/test_rag_release_gates_runner.py -k "mlflow_identity or rag_gate_result_schema_declares_all_emitted_fields"`
- `. .venv/bin/activate && pytest -q tests/test_rag_release_gates_runner.py tests/evals`
- `.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md docs/release/RAG_GATE_RESULT_EXPORT_CONTRACT.md docs/roadmap/BACKLOG_LEDGER.md`
- `.venv/bin/python scripts/ci/check_semantic_cache_gate.py`
- `make validate-changed`
- `pre-commit run --all-files`
- Pre-push hooks, including backend pre-push and full-repo Bandit

## Merge Readiness

Not claimed. Current-head CI, bot review, unresolved-thread checks, PR body
mirror, and strict merge-readiness checks are still required before merge.
