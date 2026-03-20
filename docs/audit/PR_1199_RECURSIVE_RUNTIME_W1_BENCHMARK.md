# PR 1199 Recursive Runtime W1 Benchmark

## Scope

This artifact records the narrow C3 benchmark evidence for recursive runtime W1.
It validates the bounded optimization slice added behind the inner feature flag
without changing the public API surface.

Implementation anchors:

- `app/utils/feature_flags.py:57` adds `FEATURE_RAG_RECURSIVE_OPTIMIZATION`
- `core/rag/orchestration.py:187` wires the inner optimization flag into the recursive path
- `core/rag/recursive_retrieval.py:177` keeps optimization behind `optimization_enabled`
- `core/rag/recursive_retrieval.py:228` applies request-scope retrieval memoization
- `core/rag/recursive_retrieval.py:286` applies deterministic early stop when no new usable chunks appear
- `core/rag/recursive_retrieval.py:299` preserves confidence-gain bounds
- `core/rag/recursive_retrieval.py:325` applies deterministic no-material-query-change stop
- `core/rag/recursive_retrieval.py:333` preserves fail-safe fallback on internal exceptions

## Method

- Source snapshot: `docs/audit/artifacts/pr_1199_recursive_runtime_w1_benchmark.json`
- Local generation source: `artifacts/agent_runs/c3_recursive_runtime_w1_benchmark.json`
- Measurement style: deterministic micro-benchmark with patched retrieval fixtures derived from covered unit-test scenarios
- Purpose: merge-gate evidence for rollback safety, flag-off parity, cache hits, and early-stop behavior
- Non-goal: production throughput or capacity forecasting

## Results

### Baseline Flag-Off

- Average latency: `0.0278 ms`
- P95 latency: `0.0261 ms`
- Retrieval calls per run: `2.0`
- Hops: `2`
- Optimization diagnostics attached: `false`
- Old behavior preserved: `true`

### Optimized Flag-On

- Average latency: `0.0366 ms`
- P95 latency: `0.0420 ms`
- Average retrieval calls per run: `2`
- Cache hits per run: `1`
- Early-stop hit count: `200`
- Final stop reason: `no_new_usable_chunks`
- Hops: `3`
- Confidence: `0.8`
- Chunk count: `2`

### Fallback Safety

- Fallback safe: `true`
- Returned chunks on internal exception: `0`
- Returned confidence on internal exception: `0.0`

## Assertions

- `flag_off_old_behavior_preserved = true`
- `flag_off_has_no_diagnostics_payload = true`
- `api_contract_preserved = true`
- `confidence_non_regression = true`
- `latency_non_negative = true`

## Validation Commands

- `pytest -q tests/test_recursive_rag.py tests/test_rag_orchestration.py tests/test_insight_rag_response_fields.py tests/test_philosophical_runtime.py tests/test_app_remaining_coverage.py`
- `pre-commit run --all-files`
- `make verify`

## Notes

- The optimized path intentionally remains off by default and is rollout-safe.
- The flag-off path now keeps `optimization_stats=None`, which preserves a clean disabled-state contract for downstream consumers.
- The artifact is narrow by design: it proves bounded memoization, deterministic early stopping, flag-off parity, and safe fallback, but does not claim broader runtime gains.
