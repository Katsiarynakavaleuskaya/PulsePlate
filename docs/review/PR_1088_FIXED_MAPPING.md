# PR 1088 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `69744238` makes `validate_experiment_packet()` fail closed on incompatible packet schemas in `scripts/orchestration/experiment_contract.py:191`, converts sandbox execution exceptions into deterministic `infra_flake` outcomes in `scripts/orchestration/experiment_runner.py:356`, enforces total `wall_clock_seconds` across the full oracle sequence in `scripts/orchestration/experiment_runner.py:330`, and adds regression coverage for schema rejection, sandbox exception mapping, and cross-oracle budget exhaustion in `tests/test_experiment_runner.py:104`, `tests/test_experiment_runner.py:281`, and `tests/test_experiment_runner.py:319`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#pullrequestreview-3925158278 -> 69744238
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914207490 -> 69744238
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914214557 -> 69744238
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914214559 -> 69744238
