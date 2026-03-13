# PR 1150 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: ae4b0927
Evidence: ios/Scripts/generate_app_icons.py:19
Reason: The generator now uses one de-duplicated canonical output list, so shared filenames are created once instead of being overwritten and overcounted.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1150#discussion_r2928965214 -> ae4b0927

Disposition: FIXED
Commit: ae4b0927
Evidence: tests/test_fitchef_asset_taxonomy.py:35
Reason: The taxonomy guard now fails on stale unreferenced PNGs inside FitChef `.imageset` buckets, not just on missing referenced files.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1150#discussion_r2928965215 -> ae4b0927

Disposition: FIXED
Commit: ae4b0927
Evidence: docs/roadmap/BACKLOG_LEDGER.md:1542
Reason: The new FitChef P2 backlog item was moved into the canonical `### P2` section after the remaining P1 block.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1150#discussion_r2928965216 -> ae4b0927

Disposition: FIXED
Commit: ae4b0927
Evidence: docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md:97
Reason: The evidence anchors now point to the actual PR-2 taxonomy references in the foundation and visual contracts.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1150#discussion_r2928965219 -> ae4b0927

Disposition: FIXED
Commit: ae4b0927
Evidence: ios/Scripts/move_mascot.sh:72
Reason: Both mascot copy scripts now write the canonical `FitChefDefault@*.png` filenames consumed by `Image("FitChef")`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1150#discussion_r2928970665 -> ae4b0927

Disposition: FIXED
Commit: 0b06c432
Evidence: ios/move_mascot.sh:37
Reason: The root mascot move script now uses a non-failing increment under `set -e`, so the PNG listing loop completes instead of aborting on the first file.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1150#discussion_r2929977567 -> 0b06c432

Disposition: FIXED
Commit: 0b06c432
Evidence: ios/Scripts/move_mascot.sh:74
Reason: The iOS mascot copy helper now removes legacy `fitchef@*.png` files before writing canonical `FitChefDefault@*.png` outputs, preventing stale files after reruns.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1150#discussion_r2929977571 -> 0b06c432

Disposition: FIXED
Commit: 9f584026
Evidence: ios/move_mascot.sh:57
Reason: Both mascot move scripts now reject non-PNG filenames before the existence check, so inputs like `Contents.json` cannot be copied into the `FitChefDefault@*.png` assets.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1150#discussion_r2930060303 -> 9f584026

## Merge Readiness
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
