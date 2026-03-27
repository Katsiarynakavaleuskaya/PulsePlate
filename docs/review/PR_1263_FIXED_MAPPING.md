# PR 1263 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1263#pullrequestreview-4020996186 -> 66e37726
Disposition: FIXED
Commit: 66e37726
Evidence: frontend/src/config/routes.ts:12; frontend/src/config/routes.ts:35; frontend/src/config/routes.ts:55; frontend/src/pages/Onboarding/welcomeGateV1Policy.ts:4; frontend/src/pages/Onboarding/welcomeGateV1Policy.ts:5

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1263#discussion_r3000851555 -> 66e37726
Disposition: FIXED
Commit: 66e37726
Evidence: frontend/src/config/__tests__/routes.design-preview.test.ts:5; frontend/src/config/__tests__/routes.design-preview.test.ts:30

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1263#discussion_r3000860263
Disposition: NOT-A-BUG
Evidence: docs/roadmap/BACKLOG_LEDGER.md:1498; frontend/src/stories/PulsePlateDesignSystemGuidelines.mdx:12; frontend/src/__tests__/App.test.tsx:126; frontend/src/__tests__/App.test.tsx:136
Reason: previewOnly classifies hidden mirror routes for design-review governance; direct route access remains intentional for `/design-system` and `/welcome-gate-v1`, and the repo already tests that these mirrors stay directly routable while hidden from the tab bar.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1263#pullrequestreview-4021005715 -> 5f08d7ad
Disposition: FIXED
Commit: 5f08d7ad
Evidence: frontend/src/config/routes.ts:12; frontend/src/config/routes.ts:35; frontend/src/config/routes.ts:55; frontend/src/pages/Onboarding/welcomeGateV1Policy.ts:4; frontend/src/pages/Onboarding/welcomeGateV1Policy.ts:5; frontend/src/pages/Onboarding/welcomeGateV1Policy.ts:6

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Final post-bot wait cycle completed
- [ ] Pre-commit green
- [ ] `make verify` green
