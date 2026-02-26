# PR-914 — Food DB W4 Semantic Retrieval Benchmark and Rollback Validation

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

Run command (exact, single line):

```bash
SERVER_SALT=bench-salt TESTING=true RATE_LIMITING_IN_TESTS=false PYTHONPATH=. python scripts/benchmarks/food_semantic_retrieval_benchmark.py --iterations 120 --warmup 20 --db-path data/food.sqlite --output-json docs/audit/artifacts/food_w4_semantic_benchmark.json
```

Observed output (truncated):

- `legacy_flag_off | False | \`/api/v1/foods?query=chicken&limit=20&offset=0\` | 0.90 | 0.96 | 1.12`
- `semantic_flag_on | True | \`/api/v1/foods?query=chicken&limit=20&offset=0\` | 0.89 | 0.99 | 1.11`
- `rollback_flag_off | False | \`/api/v1/foods?query=chicken&limit=20&offset=0\` | 0.90 | 0.97 | 1.18`
- `exit code: 0`

Artifact checksum command:

- `shasum -a 256 docs/audit/artifacts/food_w4_semantic_benchmark.json`
- `b6e21d23f724e5a768f6af513452b30165c27619b3ecde47440e6346fd849cb6`
- `exit code: 0`

## Results

| Scenario | Semantic flag | Endpoint | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---:|---:|---:|
| legacy_flag_off | false | `/api/v1/foods?query=chicken&limit=20&offset=0` | 0.8977 | 0.9564 | 1.1212 |
| semantic_flag_on | true | `/api/v1/foods?query=chicken&limit=20&offset=0` | 0.8896 | 0.9871 | 1.1070 |
| rollback_flag_off | false | `/api/v1/foods?query=chicken&limit=20&offset=0` | 0.8975 | 0.9713 | 1.1810 |

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
