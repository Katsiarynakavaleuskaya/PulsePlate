# PR 1249 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b9dc55af
Evidence: `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:11`; `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:95`; `frontend/src/pages/Onboarding/WelcomeGateV1.tsx:101`; `frontend/src/locales/en.json:97`; `frontend/src/locales/ru.json:97`; `frontend/src/locales/es.json:77`
Reason: Removed the redundant `aria-label` from `StepIndicator` and moved preview-flow/policy values into locale files so the preview metadata panel no longer mixes localized labels with hard-coded English values.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#discussion_r2997554306 -> b9dc55af

Disposition: FIXED
Commit: b9dc55af
Evidence: `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:51`; `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:67`; `frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:84`
Reason: Reworked the WelcomeGateV1 test to use locale-derived expectations and semantic queries instead of hard-coded localized copy, reducing brittleness in the i18n-backed assertions called out in the bot review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1249#pullrequestreview-4017228292 -> b9dc55af

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
