# PR 1081 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `c39aed12` normalizes mutable-path inputs against `REPO_ROOT` before allowlist checks so traversal segments cannot escape `core/insight/*` or `core/rag/*`, and adds regression coverage for both escape rejection and safe in-root normalization in `tests/test_experiment_bootstrap.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#discussion_r2911995342 -> c39aed12
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#pullrequestreview-3922735414 -> c39aed12

Disposition: NOT-A-BUG
Evidence: `_resolve_experiment_domain()` only receives `validated_paths`, not raw CLI input; `build_experiment_packet()` first calls `validate_mutable_candidate_surface()` and then passes the normalized allowlisted result into `_resolve_experiment_domain()`.
Reason: the traversal risk reported on the secondary prefix check is already eliminated by the normalization and allowlist gate before this function runs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#discussion_r2912043419

Disposition: FIXED
Commit: see mapping entries below
Evidence: `97fac0da` adds shared lexical normalization in `scripts/orchestration/context_pack.py`, applies it in `scripts/orchestration/skill_router.py` and `scripts/orchestration/experiment_bootstrap.py`, enriches the metrics payload with deterministic `baseline_reference` and `acceptance_threshold` fields, rejects budget overrides above protocol hard caps, restricts `--output` to `artifacts/orchestration/experiments`, and updates `tests/test_experiment_bootstrap.py` with typed fixtures, `pytest.raises`, and hard-cap/output regressions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#pullrequestreview-3922730750 -> 97fac0da
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#pullrequestreview-3922764200 -> 97fac0da
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#discussion_r2912067885 -> 97fac0da
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#discussion_r2912067889 -> 97fac0da
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#discussion_r2912067893 -> 97fac0da

Disposition: FIXED
Commit: see mapping entries below
Evidence: `887a094c` removes the drift-prone hard-coded line numbers from the `NOT-A-BUG` evidence block and switches that proof to symbol-based references, keeping the canonical artifact stable across later edits.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1081#pullrequestreview-3922810255 -> 887a094c
