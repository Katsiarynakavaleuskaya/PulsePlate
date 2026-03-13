# PR 1145 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Initial PR body aligned to project canon
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927303389 -> 9ced10a7
Disposition: FIXED
Commit: 9ced10a7
Evidence: docs/design/FITCHEF_MASCOT_ASSET_CANON.md:71; docs/design/FITCHEF_MASCOT_ASSET_CANON.md:75
Reason: markdownlint-triggering example text was normalized from a collision-style filename fragment to `image 1.png`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927303406 -> 9ced10a7
Disposition: FIXED
Commit: 9ced10a7
Evidence: docs/review/PR_1145_FIXED_MAPPING.md:63
Reason: merge-readiness checklist stays unchecked until the final head-specific governance pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927310711 -> 9ced10a7
Disposition: FIXED
Commit: 9ced10a7
Evidence: ios/Scripts/move_mascot.sh:73; ios/Scripts/move_mascot.sh:76; ios/move_mascot.sh:39; ios/move_mascot.sh:42
Reason: mascot runtime mirrors now generate true 1x/2x/3x renditions instead of duplicating the same bitmap across every asset slot.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927325245
Disposition: NOT-A-BUG
Evidence: ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/icon_iphone_20pt@2x.png
Evidence: ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/icon_iphone_20pt@3x.png
Evidence: ios/PulsePlate/Assets.xcassets/AppIcon.appiconset/icon_marketing_1024.png
Reason: the referenced AppIcon rasters already exist in the app icon catalog; the review comment was based on a stale file listing rather than a missing asset on the current head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927325248 -> 9ced10a7
Disposition: FIXED
Commit: 9ced10a7
Evidence: ios/Scripts/move_mascot.sh:75; ios/Scripts/move_mascot.sh:76; ios/Scripts/move_mascot.sh:77; ios/move_mascot.sh:41; ios/move_mascot.sh:42; ios/move_mascot.sh:43
Reason: both mascot migration scripts now write the canonical neutral filenames instead of the stale `fitchef@Nx` pattern.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927325250
Disposition: NOT-A-BUG
Evidence: frontend/src/assets/brand/fitchef-static.png
Evidence: frontend/src/components/brand/FitChefMascot.tsx:1; frontend/src/components/brand/FitChefMascot.tsx:21
Reason: the legacy static alias still exists and remains a live frontend consumer contract for the default mascot variant.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927325252 -> 9ced10a7
Disposition: FIXED
Commit: 9ced10a7
Evidence: docs/design/FITCHEF_MASCOT_ASSET_CANON.md:71; docs/design/FITCHEF_MASCOT_ASSET_CANON.md:75
Reason: duplicate markdownlint complaint covered by the same forbidden-filename wording fix in the asset canon.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#pullrequestreview-3939658196
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927303389; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927303406
Reason: this CodeRabbit review entry is a summary shell for the actionable child threads dispositioned separately above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#pullrequestreview-3939681965
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927325245; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927325248; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927325250; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1145#discussion_r2927325252
Reason: this cubic review entry is a summary shell for the actionable child threads dispositioned separately above.

## Merge Readiness
- [ ] Local gates passed on current head
- [ ] All required checks green
- [ ] No unresolved review threads remain
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] Wait-window after latest bot/review activity observed
