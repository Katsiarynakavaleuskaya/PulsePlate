# PR 1246 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 74ac64ef
Evidence: frontend/src/pages/Onboarding/WelcomeGateV1.tsx:6; frontend/src/pages/Onboarding/WelcomeGateV1.tsx:60; frontend/src/pages/Onboarding/WelcomeGateV1.tsx:68
Reason: Centralized the preview screen-count metadata, switched the step label to i18n interpolation, and localized the main landmark aria-label so the onboarding preview stays aligned with translated copy.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1246#pullrequestreview-4013359470 -> 74ac64ef
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1246#discussion_r2994232587 -> 74ac64ef
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1246#discussion_r2994232588 -> 74ac64ef

Disposition: FIXED
Commit: fc1651db
Evidence: frontend/src/pages/Onboarding/WelcomeGateV1.stories.tsx:3
Reason: Storybook now initializes the shared frontend i18n runtime before rendering the onboarding preview, so localized copy is shown instead of raw translation keys.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1246#discussion_r2994272623 -> fc1651db

Disposition: FIXED
Commit: fc1651db
Evidence: frontend/src/pages/Home.tsx:14; frontend/src/pages/Home.tsx:161; frontend/src/pages/Home.tsx:269
Reason: Reintroduced deterministic MAX_AI_QUERY_LENGTH clamping before storing the AI query, covering both free-form input and suggestion clicks.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1246#discussion_r2995253177 -> fc1651db

Disposition: FIXED
Commit: fc1651db
Evidence: frontend/src/pages/BMI/BMICalculatePage.tsx:23; frontend/src/pages/BMI/BMICalculatePage.tsx:160; frontend/src/pages/BMI/BMICalculatePage.tsx:230; frontend/src/locales/en.json:327
Reason: BMI age parsing now rejects non-integer values instead of truncating them, and all newly introduced visible BMI copy was moved into locale resources for EN/RU/ES.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1246#pullrequestreview-4014587807 -> fc1651db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1246#discussion_r2995253202 -> fc1651db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1246#discussion_r2995253208 -> fc1651db
