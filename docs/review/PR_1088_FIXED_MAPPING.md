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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914207499 -> 69744238
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914214557 -> 69744238
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914214559 -> 69744238

Disposition: FIXED
Commit: see mapping entries below
Evidence: `bd020a6e` makes `evaluate_candidate()` consume `budgets.retry_budget` for transient `infra_flake` failures in `scripts/orchestration/experiment_runner.py:401` while preserving isolated temp-checkout cleanup, and adds a deterministic retry regression in `tests/test_experiment_runner.py:411` proving the runner retries once and then accepts a recovered oracle run instead of rejecting on the first transient failure.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914207496 -> bd020a6e

Disposition: FIXED
Commit: see mapping entries below
Evidence: `9b1da1c9` makes experiment packets valid by construction by enforcing the oracle binary allowlist in `scripts/orchestration/experiment_contract.py:122`, requiring an explicit primary metric in `scripts/orchestration/experiment_contract.py:152`, preserving unknown budget keys for fail-closed validation in `scripts/orchestration/experiment_contract.py:263`, tracking `rename from` sources during patch parsing in `scripts/orchestration/experiment_runner.py:125`, and tightening deterministic runner regressions for forbidden renames, absolute `git` resolution, non-allowlisted oracle binaries, unknown budget keys, and timeout simulation in `tests/test_experiment_runner.py:17`, `tests/test_experiment_runner.py:121`, `tests/test_experiment_runner.py:150`, `tests/test_experiment_runner.py:253`, and `tests/test_experiment_runner.py:341`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245125 -> 9b1da1c9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245134 -> 9b1da1c9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245141 -> 9b1da1c9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245147 -> 9b1da1c9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245161 -> 9b1da1c9

Disposition: FIXED
Commit: see mapping entries below
Evidence: `1d823d20` narrows patch-source tracking in `scripts/orchestration/experiment_runner.py:148` so only `rename from` contributes to mutable-surface validation, and adds the regression `tests/test_experiment_runner.py:282` proving `copy from` does not create a false policy/budget rejection by injecting an immutable source path into `mutated_paths`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914383243 -> 1d823d20

Disposition: FIXED
Commit: see mapping entries below
Evidence: `8467f024` hardens the runner boundary conditions by letting a `wall_clock_seconds=1` packet start its first oracle in `scripts/orchestration/experiment_runner.py:331`, forcing default result paths through the containment check in `scripts/orchestration/experiment_runner.py:382`, and applying the exact validated in-memory patch text via stdin in `scripts/orchestration/experiment_runner.py:204`, `scripts/orchestration/experiment_runner.py:272`, and `scripts/orchestration/experiment_runner.py:444`. Regression coverage was added for the one-second budget boundary, default output-path escape rejection, and TOCTOU-resistant patch application in `tests/test_experiment_runner.py:385`, `tests/test_experiment_runner.py:673`, and `tests/test_experiment_runner.py:689`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914406881 -> 8467f024
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914406888 -> 8467f024
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914406892 -> 8467f024

Disposition: FIXED
Commit: see mapping entries below
Evidence: `e99083fd` moves runner preflight reads into the fail-closed path in `scripts/orchestration/experiment_runner.py:402`, so missing patch files or failed shared-tree status probes now return deterministic `infra_flake` results instead of escaping out of `main()`. Regression coverage was added in `tests/test_experiment_runner.py:616` for the missing-patch preflight path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914458229 -> e99083fd

Disposition: FIXED
Commit: see mapping entries below
Evidence: `1814f699` updates the experimentation epic and PR3 runner ledger traceability in `docs/roadmap/BACKLOG_LEDGER.md:5243`, replaces stale placeholders with the in-flight PR reference `#1088` in `docs/roadmap/BACKLOG_LEDGER.md:5281`, and swaps stale philosophical-runtime links for the actual runner/bootstrap evidence surfaces in `docs/roadmap/BACKLOG_LEDGER.md:5290` and `docs/roadmap/BACKLOG_LEDGER.md:5356`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245106 -> 1814f699
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245117 -> 1814f699

Disposition: FIXED
Commit: see mapping entries below
Evidence: `1d05dd87` adds the required same-PR scoped agent-instructions update in `scripts/AGENTS.md:12`, documenting the governed experimentation runner entrypoints, repo-root execution requirement, isolated temp-checkout rule, SoT pointer for mutable/oracle constraints, and local-only result-artifact contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245099 -> 1d05dd87

Disposition: FIXED
Commit: see mapping entries below
Evidence: `145d6ce0` closes the post-comment sandbox follow-up by clarifying the deterministic `infra_flake` error path in `scripts/orchestration/experiment_runner.py:352` and extending the regression assertion in `tests/test_experiment_runner.py:372` so sandbox exceptions are emitted as rejected result artifacts instead of uncaught CLI failures. This was the final actionable item from CodeRabbit review `3925189381`; the PR body mirror was also updated with the required `Deferred / Follow-ups` section linking the PR4 ledger item.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#discussion_r2914245155 -> 145d6ce0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1088#pullrequestreview-3925189381 -> 145d6ce0
