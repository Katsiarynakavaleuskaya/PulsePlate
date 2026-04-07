# Meilisearch foods index — zero-downtime swap (operator runbook)

This runbook describes how operators run the **offline** build → validate → warm → **swap-indexes**
pipeline using `scripts/meili_food_index_swap.py`. There is **no** public HTTP route; configuration
is env-driven (see `.env.example`).

## Preconditions

- Meilisearch reachable at `MEILI_URL`.
- **Distinct** UIDs: live index (`MEILI_FOODS_INDEX` or `MEILI_SWAP_PRIMARY_INDEX`) and build target
  (`MEILI_SWAP_CANDIDATE_INDEX` or `MEILI_SWAP_CANDIDATE_UID`). Misconfiguration is rejected in code:
  `app/services/meili_swap_orchestration.py:46` (`ensure_distinct_primary_and_candidate`).
- JSONL corpus: one JSON object per line (documents must include Meili primary key, default `id`).

## Commands (repo root)

```bash
. .venv/bin/activate
# Build candidate from JSONL (recreates candidate index by default)
python scripts/meili_food_index_swap.py build --documents /path/to/foods.jsonl

python scripts/meili_food_index_swap.py validate
python scripts/meili_food_index_swap.py warm
# Atomic cutover (server-side swap-indexes)
python scripts/meili_food_index_swap.py swap

# Or full pipeline
python scripts/meili_food_index_swap.py pipeline --documents /path/to/foods.jsonl
```

- Verbose logs: `--verbose` (DEBUG for `meili_food_index_swap` and `app.services.meili_swap_orchestration`).
- Skip swap after warm: `pipeline --skip-swap`.
- Advanced empty-doc recovery: `pipeline --documents /path/to/empty.jsonl --allow-empty-swap` (use with care).

## Swap implementation anchor

Swap is executed via `POST /swap-indexes` and task polling in
`MeiliSwapOrchestrator.perform_index_swap` — `app/services/meili_swap_orchestration.py:254`.

## Failure hints

- **Unreachable / timeout**: errors mention `MEILI_URL` only (no API key in messages); see
  `_meili_unreachable_message` at `app/services/meili_swap_orchestration.py:60`.
- **Task failures**: orchestrator raises with Meilisearch task error payload after polling
  `GET /tasks/{taskUid}` in `MeiliSwapOrchestrator._wait_for_task` (`app/services/meili_swap_orchestration.py:191`).

## Evidence anchors (docs Phase 1)

- `app/services/meili_swap_orchestration.py:46`
- `app/services/meili_swap_orchestration.py:60`
- `app/services/meili_swap_orchestration.py:191`
- `app/services/meili_swap_orchestration.py:254`
- `scripts/meili_food_index_swap.py:1`
