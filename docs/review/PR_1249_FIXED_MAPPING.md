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

Disposition: NOT-A-BUG
Evidence: `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:98`
Reason: The preview metadata card is an explicitly reviewer-oriented surface, so keeping canonical locale codes (`ru · en · es`) is intentional; the labels around that field are localized, while the raw codes remain the most useful debugging signal for route/content parity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#pullrequestreview-4017292336

Disposition: FIXED
Commit: e5a395a9
Evidence: `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:53`; `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:65`; `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:99`; `frontend/src/locales/en.json:58`; `frontend/src/locales/es.json:38`; `frontend/src/locales/ru.json:58`
Reason: Made the locale helper contract explicit with a named return type, added a negative assertion that the preview render does not persist `has_seen_welcome_v1`, and aligned the screen-1 footer branding with PulsePlate across all shipped locales so the latest CodeRabbit actionable review is fully addressed on the current head.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#discussion_r2997692278 -> e5a395a9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#pullrequestreview-4017372495 -> e5a395a9

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
