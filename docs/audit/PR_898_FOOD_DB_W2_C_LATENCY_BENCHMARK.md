# PR-898 — Food DB Wave 2-C Latency Benchmark Report

## Scope

- Program wave: W2-C (search modernization follow-up benchmark/report).
- Goal: measure local-first latency for the existing food API surface and barcode error paths.
- Runtime behavior changes: none (benchmark/report only).

## Evidence Anchors

- Router contract:
  - `app/routers/foods.py:43` (`GET /api/v1/foods`)
  - `app/routers/foods.py:67` (`GET /api/v1/foods/search` alias)
  - `app/routers/foods.py:88` (`GET /api/v1/foods/barcode/{barcode}`)
- Search/barcode service paths:
  - `app/services/food_store.py:478` (`search_foods`)
  - `app/services/food_store.py:518` (`_normalize_barcode`)
  - `app/services/food_store.py:533` (`get_food_by_barcode`)
- Benchmark harness:
  - `scripts/benchmarks/food_api_latency_benchmark.py`
- Raw artifact:
  - `docs/audit/artifacts/food_w2c_latency_benchmark.json`

## Method

Run command (UTC run timestamp: `2026-02-25 07:53:58 UTC`):

```bash
SERVER_SALT=bench-salt \
TESTING=true \
RATE_LIMITING_IN_TESTS=false \
PYTHONPATH=. \
python scripts/benchmarks/food_api_latency_benchmark.py \
  --iterations 120 \
  --warmup 20 \
  --db-path data/food.sqlite \
  --output-json docs/audit/artifacts/food_w2c_latency_benchmark.json
```

Artifact checksum:

- `sha256 docs/audit/artifacts/food_w2c_latency_benchmark.json`
- `90331d10b53daf2ac8096f374f5851883fee4c904d7f384440f0b5af5ebe53f0`

## Results

| Scenario | Endpoint | Expected status | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---:|---:|---:|---:|
| foods_list_hit | `/api/v1/foods?query=chicken&limit=20&offset=0` | 200 | 0.8991 | 1.0875 | 1.1198 |
| foods_search_alias_hit | `/api/v1/foods/search?query=chicken&limit=20&offset=0` | 200 | 0.8900 | 1.0288 | 1.1326 |
| foods_list_no_results | `/api/v1/foods?query=zzzzzzzzzz&limit=20&offset=0` | 200 | 0.8796 | 1.0901 | 1.3637 |
| barcode_miss | `/api/v1/foods/barcode/9999999999999` | 404 | 0.7822 | 0.9978 | 1.0959 |
| barcode_malformed | `/api/v1/foods/barcode/abc` | 422 | 0.6859 | 0.8576 | 0.9255 |

## Conclusion

- W2 latency budget objective (`<50ms p50`) is satisfied for measured local-first paths by a wide margin.
- Alias route (`/api/v1/foods/search`) shows parity with `/api/v1/foods` under the same query/load settings.
- Barcode validation/miss paths are fast and deterministic for current contract behavior (422/404).

## Open Issue (Tracked)

- Optional `barcode_hit` scenario remains disabled by default in the benchmark harness.
- Reason: on seeded local DB rows, response serialization can fail at `app/routers/foods.py:105` because `FoodItem.flags` expects `List[str]` (`app/schemas/food.py:40`) while stored value may be stringified.
- Follow-up is tracked in backlog for contract normalization before enabling `--include-barcode-hit` as default gate.
