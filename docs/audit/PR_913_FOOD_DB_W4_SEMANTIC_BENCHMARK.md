# PR-913 — Food DB W4 Semantic Retrieval Benchmark and Rollback Validation

## Scope

- Program wave: W4-B (semantic retrieval closure bundle).
- Goal: document cost/performance benchmark and prove rollback-safe behavior for semantic search flag.
- Runtime behavior changes in this PR:
  - benchmark harness for semantic retrieval path,
  - deterministic rollback tests for semantic flag-off path.

## Evidence Anchors

- Semantic backend routing and fallback/rollback path:
  - `app/services/food_store.py:300`
  - `app/services/food_store.py:319`
  - `app/services/food_store.py:384`
  - `app/services/food_store.py:481`
- Public food search endpoint using backend resolver:
  - `app/routers/foods.py:43`
  - `app/routers/foods.py:26`
- Rollback deterministic tests:
  - `tests/test_food_store_service.py:348`
  - `tests/test_foods_router_additional.py:303`
- Benchmark harness:
  - `scripts/benchmarks/food_semantic_retrieval_benchmark.py:1`
  - `scripts/benchmarks/food_semantic_retrieval_benchmark.py:187`
  - `scripts/benchmarks/food_semantic_retrieval_benchmark.py:218`
- Raw benchmark artifact:
  - `docs/audit/artifacts/food_w4_semantic_benchmark.json`

## Method

Run command:

```bash
SERVER_SALT=bench-salt \
TESTING=true \
RATE_LIMITING_IN_TESTS=false \
PYTHONPATH=. \
python scripts/benchmarks/food_semantic_retrieval_benchmark.py \
  --iterations 120 \
  --warmup 20 \
  --db-path data/food.sqlite \
  --output-json docs/audit/artifacts/food_w4_semantic_benchmark.json
```

Artifact checksum:

- `shasum -a 256 docs/audit/artifacts/food_w4_semantic_benchmark.json`
- `421b4577e951747d95711c7e0050baea19e1d1a179bdc8d5957f7ceeb452f3c1`

## Results

| Scenario | Semantic flag | Endpoint | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---:|---:|---:|
| legacy_flag_off | false | `/api/v1/foods?query=chicken&limit=20&offset=0` | 0.8975 | 1.0260 | 1.1647 |
| semantic_flag_on | true | `/api/v1/foods?query=chicken&limit=20&offset=0` | 0.8860 | 0.9278 | 1.0894 |
| rollback_flag_off | false | `/api/v1/foods?query=chicken&limit=20&offset=0` | 0.8872 | 0.9388 | 1.1316 |

## Rollback Validation

- Scenario sequence explicitly executes:
  1. `legacy_flag_off`
  2. `semantic_flag_on`
  3. `rollback_flag_off`
- This validates request-time rollback behavior: after semantic path is enabled, switching flag back to `false` returns to non-semantic path without API contract break.
- Additional deterministic unit coverage in this PR:
  - service-level rollback guard (`tests/test_food_store_service.py:348`)
  - router-level rollback guard (`tests/test_foods_router_additional.py:303`)

## Conclusion

- W4 benchmark gate (`p95 < 50ms`) passes for legacy, semantic, and rollback scenarios.
- Rollback-safe deployment path is validated by benchmark scenario order and explicit deterministic tests.
- Non-semantic search remains stable and default-safe when semantic flag is disabled.
