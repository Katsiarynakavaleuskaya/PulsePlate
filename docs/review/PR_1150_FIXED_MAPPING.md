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

## Merge Readiness
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
