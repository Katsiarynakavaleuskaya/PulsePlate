# PR 1092 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `5c49d3fa` replaces import-time `sys.path` mutation with an `ImportError`-guarded CLI fallback in `scripts/orchestration/experiment_promote.py:17`, and updates the experimentation epic plus the PR4 child entry so both now point to the active PR `#1092` in `docs/roadmap/BACKLOG_LEDGER.md:5302` and `docs/roadmap/BACKLOG_LEDGER.md:5363`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#discussion_r2914955472 -> 5c49d3fa
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#pullrequestreview-3925935588 -> 5c49d3fa
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#issuecomment-4034978226 -> 5c49d3fa

Disposition: FIXED
Commit: see mapping entries below
Evidence: `203bea3c` hardens the promotion lane by enforcing a path-safe `experiment_id` contract in `scripts/orchestration/experiment_contract.py:214` and `scripts/orchestration/experiment_promote.py:111`, requiring `failure_class` when a result is `rejected` in `scripts/orchestration/experiment_contract.py:362`, falling back to promotion payload status/failure data in `scripts/orchestration/telemetry_rollup.py:267`, and making optional experiment-context filtering safe for unhashable `benchmark_delta` payloads in `scripts/orchestration/agent_run_summary.py:264`. Regression coverage was added in `tests/test_experiment_promote.py:278`, `tests/test_experiment_promote.py:295`, `tests/test_telemetry_rollup.py:298`, and `tests/test_agent_run_summary_artifact.py:122`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#discussion_r2914958805 -> 203bea3c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#discussion_r2914958806 -> 203bea3c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#discussion_r2914958808 -> 203bea3c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#discussion_r2914971955 -> 203bea3c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#discussion_r2914971957 -> 203bea3c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#discussion_r2914971964 -> 203bea3c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#discussion_r2914971970 -> 203bea3c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1092#pullrequestreview-3925952928 -> 203bea3c
