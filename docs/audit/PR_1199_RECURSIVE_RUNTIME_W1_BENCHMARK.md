# PR 1199 Recursive Runtime W1 Benchmark

## Scope

This artifact records the narrow C3 benchmark evidence for recursive runtime W1.
It validates the bounded optimization slice added behind the inner feature flag
without changing the public API surface.

Implementation anchors:

- `app/utils/feature_flags.py:57` adds `FEATURE_RAG_RECURSIVE_OPTIMIZATION`
- `app/services/insight_runtime.py:90` resolves the optimization flag in app-layer tracing code before entering core orchestration
- `core/rag/orchestration.py:121` accepts `optimization_enabled` as explicit input and keeps `core/` free from `app.*` imports
- `core/rag/recursive_retrieval.py:72` keeps optimization diagnostics typed and attached only on the enabled path
- `core/rag/recursive_retrieval.py:122` reuses request-scope refinement tokenization for repeated evidence
- `core/rag/recursive_retrieval.py:297` allows one more refinement hop on repeated chunks before deciding no new usable evidence exists
- `core/rag/recursive_retrieval.py:355` records `no_new_usable_chunks` only after the repeated-evidence refinement fails to change the query materially
- `core/rag/recursive_retrieval.py:369` preserves fail-safe fallback on internal exceptions

## Method

- Source snapshot: `docs/audit/artifacts/pr_1199_recursive_runtime_w1_benchmark.json`
- Local generation source: `artifacts/agent_runs/c3_recursive_runtime_w1_benchmark.json`
- Measurement style: deterministic micro-benchmark with patched retrieval fixtures derived from covered unit-test scenarios
- Purpose: merge-gate evidence for rollback safety, flag-off parity, repeated-evidence refinement caching, and deterministic early-stop behavior
- Non-goal: production throughput or capacity forecasting

## Results

### Baseline Flag-Off

- Average latency: `0.0802 ms`
- P95 latency: `0.1373 ms`
- Retrieval calls per run: `3`
- Hops: `3`
- Confidence: `0.9`
- Optimization diagnostics attached: `false`
- Old behavior preserved: `true`

### Optimized Flag-On

- Average latency: `0.0534 ms`
- P95 latency: `0.1064 ms`
- Average retrieval calls per run: `3`
- Cache hits per run: `2`
- Refinement cache hits per run: `2`
- Early-stop hit count: `200`
- Final stop reason: `no_new_usable_chunks`
- Hops: `3`
- Confidence: `0.9`
- Chunk count: `1`

### Fallback Safety

- Fallback safe: `true`
- Returned chunks on internal exception: `0`
- Returned confidence on internal exception: `0.0`
- Stop reason on internal exception fallback: `completed`

## Assertions

- `flag_off_old_behavior_preserved = true`
- `flag_off_has_no_diagnostics_payload = true`
- `api_contract_preserved = true`
- `confidence_non_regression = true`
- `latency_non_negative = true`

## Validation Commands

- Command: `pytest -q tests/test_recursive_rag.py tests/test_rag_orchestration.py tests/test_insight_rag_response_fields.py tests/test_philosophical_runtime.py tests/test_app_remaining_coverage.py`
  - Raw output:
    - `........................................................................ [ 58%]`
    - `...................................................                      [100%]`
    - `tests/test_insight_rag_response_fields.py: 12 warnings`
  - Exit code: `0`
- Command: `pre-commit run --all-files`
  - Raw output:
    - `check yaml...............................................................Passed`
    - `backend tests (pytest, changed files)....................................Passed`
    - `ios syntax check (swift).................................................Passed`
  - Exit code: `0`
- Command: `make verify`
  - Raw output:
    - `verify-env: local verify environment passed.`
    - `Success: no issues found in 295 source files`
    - `Coverage: 100%`
  - Exit code: `0`

## Notes

- The optimized path intentionally remains off by default and is rollout-safe.
- The flag-off path now keeps `optimization_stats=None`, which preserves a clean disabled-state contract for downstream consumers.
- The optimized path now uses only refinement-token memoization; retrieval-call memoization was removed because the recursive query progression does not revisit prior lookup keys in production.
- The artifact is narrow by design: it proves bounded refinement caching, deterministic early stopping after repeated-evidence refinement, flag-off parity, and safe fallback, but does not claim broader runtime gains.
