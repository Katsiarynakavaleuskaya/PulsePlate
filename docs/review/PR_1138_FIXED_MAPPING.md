# PR 1138 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: 4053286edc7a69bd57df1d48e9f3d6cf04ea1476
Evidence: `docs/figma/ios_prototype_v2/plate.html:53` through `docs/figma/ios_prototype_v2/plate.html:74` now use semantic `<ul>/<li>` markup for the Plate segment breakdown, and `docs/figma/ios_prototype_v2/styles.css:1041` through `docs/figma/ios_prototype_v2/styles.css:1058` keep the same visual treatment on the list elements.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#discussion_r2925130125 -> 4053286edc7a69bd57df1d48e9f3d6cf04ea1476

Disposition: FIXED
Commit: 4053286edc7a69bd57df1d48e9f3d6cf04ea1476
Evidence: `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:278` through `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:339` keep the original BMI/onboarding request sequence contiguous, while `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:459` through `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md:551` move the Plate/Progress evidence to a clean later block with non-overlapping request numbers.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#discussion_r2925133420 -> 4053286edc7a69bd57df1d48e9f3d6cf04ea1476
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#discussion_r2925137193 -> 4053286edc7a69bd57df1d48e9f3d6cf04ea1476
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#pullrequestreview-3937188522 -> 4053286edc7a69bd57df1d48e9f3d6cf04ea1476

Disposition: NOT-A-BUG
Evidence: `docs/figma/ios_prototype_v2/home.html:2` and `docs/figma/ios_prototype_v2/progress.html:2` both use `lang="ru"` while mixing localized descriptive copy with product nouns such as `PulsePlate`, `Progress`, and `PRO`; `docs/figma/ios_prototype_v2/styles.css:1329` through `docs/figma/ios_prototype_v2/styles.css:1342` now scope the small-screen override to layout grids only, so the earlier body/screen-wide mobile override concern is no longer present on current head.
Reason: The remaining high-level language note in the Sourcery review is consistent with the existing localized iOS prototype convention; the actionable structural part of that review is tracked separately and fixed above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#pullrequestreview-3937179944

Disposition: FIXED
Commit: f09a02d4839bb72a4abe8444369cd98a45f0f129
Evidence: `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md:90` and `docs/figma/FIGMA_IOS_PROTOTYPE_V2_RECONCILIATION.md:93` now point to the current runtime-backed Plate and Progress source ranges, while `docs/figma/ios_prototype_v2/progress.html:123` aligns the transport/API recovery CTA label with the shared `Retry` contract used by the main-state issue cards.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#discussion_r2930877361 -> f09a02d4839bb72a4abe8444369cd98a45f0f129
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#discussion_r2930877373 -> f09a02d4839bb72a4abe8444369cd98a45f0f129
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#discussion_r2930877375 -> f09a02d4839bb72a4abe8444369cd98a45f0f129
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1138#pullrequestreview-3943656290 -> f09a02d4839bb72a4abe8444369cd98a45f0f129

## Merge Readiness
- [x] Local gates passed on current head
- [ ] All required checks green
- [ ] No unresolved review threads remain
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] Wait-window after latest bot/review activity observed

Local validation evidence on current content:
- `git diff --check`
- `pre-commit run --all-files`
- `make lint`
- `mypy --no-incremental --cache-dir=/dev/null app core`
- `make test-fast`
- `coverage run -m pytest -q tests/edges tests/test_remaining_modules.py --maxfail=3`
- `diff-cover coverage.xml --compare-branch=origin/main --fail-under=97`
