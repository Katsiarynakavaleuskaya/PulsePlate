# PR 1249 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b9dc55af
Evidence: `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:11`; `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:95`; `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:101`
Reason: Removed the redundant `aria-label` from `StepIndicator` and moved preview-flow/policy values into locale files so the preview metadata panel no longer mixes localized labels with hard-coded English values.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#discussion_r2997554306 -> b9dc55af

Disposition: FIXED
Commit: b9dc55af
Evidence: `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:52`; `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:69`; `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:86`
Reason: Reworked the WelcomeGateV1 test to use locale-derived expectations and semantic queries instead of hard-coded localized copy, reducing brittleness in the i18n-backed assertions called out in the bot review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#pullrequestreview-4017228292 -> b9dc55af

Disposition: FIXED
Commit: a61b032e
Evidence: `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:34`; `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:82`; `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:13`; `frontend/src/locales/ru.json:40`; `frontend/src/locales/en.json:40`; `frontend/src/locales/es.json:20`
Reason: Localized the route-mirror badge and hero alt text, translated the Russian eyebrow copy, and cleaned up the i18n initialization listener on timeout so the remaining cubic and CodeRabbit thread findings are addressed on the current head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#discussion_r2997570137 -> a61b032e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#discussion_r2997590692 -> a61b032e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#discussion_r2997590700 -> a61b032e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#discussion_r2997590704 -> a61b032e

Disposition: NOT-A-BUG
Evidence: Individual cubic actionable thread is mapped explicitly to `a61b032e`.
Reason: The cubic review-level wrapper aggregates the same route-mirror issue already tracked by `discussion_r2997570137`; no separate code delta is required beyond that mapped fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#pullrequestreview-4017244473

Disposition: FIXED
Commit: 0618ea21
Evidence: `frontend/src/locales/en.json:40`; `frontend/src/locales/ru.json:40`; `frontend/src/locales/es.json:20`
Reason: Ran Prettier on the touched locale JSON files to normalize indentation, closing the remaining CodeRabbit formatting nitpick while keeping the new localized Welcome Gate keys in canonical JSON form.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#pullrequestreview-4017264980 -> 0618ea21

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
