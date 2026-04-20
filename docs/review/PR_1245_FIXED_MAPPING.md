# PR 1245 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: frontend/src/__tests__/App.test.tsx:1; frontend/src/components/design-system/CanonBoards.tsx:120; frontend/src/components/design-system/BrandAssetPlaceholder.stories.tsx:1
Reason: The Sourcery review-level notes about switching the router test harness and splitting canon boards into smaller modules are advisory refactor suggestions, not correctness defects for the current preview-route scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1245#pullrequestreview-4013361923

Disposition: FIXED
Commit: a127614f
Evidence: frontend/src/components/design-system/BrandAssetPlaceholder.stories.tsx:8
Reason: Merged Storybook `className` overrides so placeholder controls can affect styling without losing the default preview sizing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1245#discussion_r2994234638 -> a127614f

Disposition: FIXED
Commit: a127614f
Evidence: frontend/src/components/brand/FitChefMascot.tsx:23; frontend/src/components/brand/__tests__/BrandAssets.test.tsx:30
Reason: Switched the `wink` variant to the canonical portrait asset family and aligned the mascot alt-text test to the new contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1245#discussion_r2994242791 -> a127614f

Disposition: FIXED
Commit: a127614f
Evidence: frontend/src/components/design-system/CanonBoards.tsx:124; frontend/src/components/design-system/CanonBoards.tsx:230; frontend/src/components/design-system/CanonBoards.tsx:345; frontend/src/components/design-system/CanonBoards.tsx:409; frontend/src/pages/DesignSystemPage.tsx:3; frontend/src/config/__tests__/routes.design-preview.test.ts:4
Reason: Added explicit return types required by repo policy, removed duplicated ordered-list numerals, and applied the nitpick return-type annotations in the route preview test; the CodeRabbit review summary is therefore fully covered by the follow-up patch.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1245#pullrequestreview-4013394269 -> a127614f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1245#discussion_r2994261410 -> a127614f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1245#discussion_r2994261415 -> a127614f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1245#discussion_r2994261428 -> a127614f
