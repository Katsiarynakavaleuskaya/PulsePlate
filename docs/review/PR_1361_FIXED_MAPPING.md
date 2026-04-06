<!-- markdownlint-disable MD034 -->
# PR 1361 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: a65dd6fe34626341f0832dedcbb040b0d7b58121
Evidence: `core/food_apis/raw_snapshot_gate.py` (`strict` + missing-manifest `SnapshotIntegrityError`; `snapshot_root.expanduser().resolve()`); `scripts/build_food_db.py` (`validate_off_raw_manifest_gate(..., strict=True)`); `core/food_apis/snapshot_sync.py` (`SnapshotManager(resolved, today_provider=today_provider)`); `data/raw/snapshots/README.md` (fail-closed CLI note); `tests/test_food_apis_snapshot_w1.py` (strict missing manifest, `~/` snapshot root, `today_provider` propagation)
Reason: Sourcery fail-closed semantics for `--validate-raw-snapshots`; Sourcery/cubic path normalization for `raw_root` / gate root; Codex P2 — same `today_provider` for `OpenFoodFactsDeltaSource` and `SnapshotManager`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1361#discussion_r3039902451 -> a65dd6fe34626341f0832dedcbb040b0d7b58121
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1361#discussion_r3039910405 -> a65dd6fe34626341f0832dedcbb040b0d7b58121
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1361#discussion_r3039910407 -> a65dd6fe34626341f0832dedcbb040b0d7b58121
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1361#discussion_r3039914070 -> a65dd6fe34626341f0832dedcbb040b0d7b58121

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1361_FIXED_MAPPING.md:1`; Sourcery pull-request summary duplicates the threaded `discussion_r` items mapped above with `Disposition: FIXED`.
Reason: Aggregate review body is not an additional fix thread; per-line comments carry actionable items.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1361#pullrequestreview-4062490555

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1361_FIXED_MAPPING.md:1`; cubic file-level findings match resolved `discussion_r3039910405` and `discussion_r3039910407` (typing + expanduser), addressed on the branch before this mapping commit.
Reason: Avoid duplicate FIXED mapping for the aggregate cubic review URL; threaded URLs are listed in the FIXED block.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1361#pullrequestreview-4062500725

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1361_FIXED_MAPPING.md:1`; Codex connector summary review without a separate actionable thread beyond `discussion_r3039914070`.
Reason: Mirror Sourcery/cubic aggregate handling; single inline thread captured in FIXED block.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1361#pullrequestreview-4062505328

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green locally

Notes: Resolve any remaining review threads in GitHub UI after push; re-run `check_merge_ready.py` before merge.

<!-- markdownlint-enable MD034 -->
