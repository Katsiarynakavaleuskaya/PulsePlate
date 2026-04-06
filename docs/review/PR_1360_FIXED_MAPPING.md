<!-- markdownlint-disable MD034 -->
# PR 1360 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 464ab151
Evidence: `core/food_sources/snapshot_manager.py`: `_resolve_manifest_snapshot_path` resolves relative manifest `file` values against the source manifest directory; `verify_recorded_snapshots` uses it so verification is not CWD-dependent. Tests: `test_verify_recorded_snapshots_resolves_relative_manifest_paths`, `test_record_snapshot_size_mismatch_leaves_manifest_unchanged`. Manifest list/entry schema remains fail-closed via `_load_manifest` (`SnapshotIntegrityError`).
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1360#pullrequestreview-4062160978 -> 464ab151
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1360#discussion_r3039621183 -> 464ab151
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1360#pullrequestreview-4062174939 -> 464ab151
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1360#pullrequestreview-4062189376 -> 464ab151
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1360#discussion_r3039631946 -> 464ab151

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green locally

Notes: Resolve GitHub review threads after this mapping push; re-run merge-readiness locally with `GITHUB_TOKEN`.

<!-- markdownlint-enable MD034 -->
