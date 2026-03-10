# PR 1081 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `c39aed12` normalizes mutable-path inputs against `REPO_ROOT` before allowlist checks so traversal segments cannot escape `core/insight/*` or `core/rag/*`, and adds regression coverage for both escape rejection and safe in-root normalization in `tests/test_experiment_bootstrap.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#discussion_r2911995342 -> c39aed12

Disposition: NOT-A-BUG
Evidence: `_resolve_experiment_domain()` only receives `validated_paths`, not raw CLI input; `build_experiment_packet()` calls `validate_mutable_candidate_surface()` first at `scripts/orchestration/experiment_bootstrap.py:268` and passes the normalized allowlisted result into `_resolve_experiment_domain()` at `scripts/orchestration/experiment_bootstrap.py:277`.
Reason: the traversal risk reported on the secondary prefix check is already eliminated by the normalization and allowlist gate before this function runs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#discussion_r2912043419
