<!-- markdownlint-disable MD034 -->
# PR 1427 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#pullrequestreview-4108772273
Disposition: FIXED
Commit: f167a4d67
Evidence: `frontend/src/components/marketing/SiteFooter.tsx` wraps `MarketingSection` in a semantic `<footer>` so the page exposes a `contentinfo` landmark (Sourcery review summary + inline thread).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#pullrequestreview-4108796619
Disposition: FIXED
Commit: f167a4d67
Evidence: Same `<footer>` landmark addresses the Cubic review “contentinfo” / footer semantics.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082090467
Disposition: FIXED
Commit: f167a4d67
Evidence: `frontend/src/components/marketing/SiteFooter.tsx` outer `<footer>` matches Cubic thread request.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#pullrequestreview-4108807413
Disposition: FIXED
Commit: f167a4d67
Evidence: CodeRabbit “Actionable comments posted: 5” items are covered by `f167a4d67` (types + footer + mapping) and `ba4a367e8` (marketing focus/hover a11y).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082100072
Disposition: FIXED
Commit: f167a4d67
Evidence: This file now includes `## Merge Readiness` with the canonical unchecked checklist (CodeRabbit artifact structure).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082100100
Disposition: FIXED
Commit: f167a4d67
Evidence: `frontend/src/components/marketing/HowItWorksSection.tsx` exports `HowItWorksSection(): JSX.Element`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082100106
Disposition: FIXED
Commit: ba4a367e8
Evidence: `frontend/src/components/marketing/marketing.css` adds `:focus-visible` / link focus treatment (CodeRabbit “Addressed in commit ba4a367”).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082100112
Disposition: FIXED
Commit: f167a4d67
Evidence: `frontend/src/components/marketing/MarketingPrimitives.tsx` adds explicit `JSX.Element` return types for exported primitives.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082100122
Disposition: FIXED
Commit: f167a4d67
Evidence: `frontend/src/pages/Marketing/PulsePlateMarketingPage.tsx` adds `PulsePlateMarketingPage(): JSX.Element`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082131657
Disposition: FIXED
Commit: 38e85ed09
Evidence: `frontend/src/components/marketing/marketing.css:173-190` consolidates `.ppm-hero-link:hover` / `:focus-visible` (removes duplicate `:focus-visible` blocks flagged by CodeRabbit).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082131675
Disposition: NOT-A-BUG
Evidence: `frontend/src/components/marketing/TiersSection.tsx:11`
Reason: Tier rows are static marketing copy; OpenAPI-generated DTOs in `frontend/src/api/schema.ts` model API payloads—importing them into this page would couple marketing strings to backend release cadence without changing UX (thin-client separation).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#discussion_r3082131680
Disposition: FIXED
Commit: 38e85ed09
Evidence: `frontend/src/components/marketing/TiersSection.tsx:97-100` sets `aria-hidden` on decorative `Check` icons next to visible list item text.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1427#pullrequestreview-4108840670
Disposition: FIXED
Commit: 38e85ed09
Evidence: CodeRabbit follow-up review: CSS selector cleanup and tiers layout/a11y updates in `frontend/src/components/marketing/marketing.css` and `frontend/src/components/marketing/TiersSection.tsx` (same commit as threads above).

## Merge Readiness

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
<!-- markdownlint-enable MD034 -->
