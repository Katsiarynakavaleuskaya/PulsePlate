# PR 1247 — Fixed in Commit Mapping

Carryover note: supersedes closed PR #1246 after its base branch (`feat/design-canon-preview-route`) merged via PR #1245 and was removed. Review-thread evidence below originates from PR #1246 and remains the canonical proof for the carried-over fixes on this branch.

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

Disposition: FIXED
Commit: f2882f59
Evidence: frontend/src/components/insight/AiInsightPanel.tsx:67; frontend/src/components/insight/AiInsightPanel.tsx:94; frontend/src/components/insight/AiInsightPanel.tsx:186; frontend/src/pages/Home.tsx:112; frontend/src/pages/Home.tsx:139; frontend/src/pages/Home.tsx:266; frontend/src/pages/BMI/BMICalculatePage.tsx:58; frontend/src/pages/BMI/BMICalculatePage.tsx:112; frontend/src/pages/BMI/BMICalculatePage.tsx:143; frontend/src/pages/Onboarding/WelcomeGateV1.tsx:41; frontend/src/pages/Onboarding/WelcomeGateV1.tsx:76; frontend/src/pages/Onboarding/WelcomeGateV1.tsx:163; frontend/src/locales/es.json:22
Reason: Addressed the current PR #1247 review bundle by replacing locale-specific AI panel defaults with neutral English defaults, disabling/loading-guarding the submit control, rendering action labels as non-interactive unless handlers exist, restoring Home fallback tags and duplicate-submit protection, clearing stale BMI results during re-submit while making SegmentedChoice generic, wiring WelcomeGate skip to /setup, adding local goal-selection state with aria-pressed, and translating the remaining Spanish onboarding strings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#pullrequestreview-4014981725 -> f2882f59
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#pullrequestreview-4015157775 -> f2882f59
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#pullrequestreview-4015161126 -> f2882f59

Disposition: FIXED
Commit: f2882f59
Evidence: frontend/src/pages/Onboarding/WelcomeGateV1.tsx:76; frontend/src/pages/Onboarding/__tests__/WelcomeGateV1.test.tsx:22
Reason: The first-screen Skip control now performs an explicit router transition to /setup and is covered by the WelcomeGate preview test.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995593913 -> f2882f59
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995753852 -> f2882f59
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995757044 -> f2882f59

Disposition: FIXED
Commit: f2882f59
Evidence: frontend/src/locales/es.json:22; frontend/src/locales/es.json:39; frontend/src/locales/es.json:58; frontend/src/locales/es.json:76
Reason: Remaining onboarding welcome strings that were still English in the Spanish locale bundle were translated to keep the es surface language-consistent.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995753859 -> f2882f59

Disposition: FIXED
Commit: f2882f59
Evidence: frontend/src/components/insight/AiInsightPanel.tsx:67; frontend/src/pages/Home.tsx:266
Reason: Home now passes an explicit English placeholder and the shared AI panel no longer defaults to Russian copy when a caller does not override the text.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995753864 -> f2882f59
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995757030 -> f2882f59

Disposition: FIXED
Commit: f2882f59
Evidence: frontend/src/components/insight/AiInsightPanel.tsx:12; frontend/src/components/insight/AiInsightPanel.tsx:186
Reason: AiInsightPanel now models optional action handlers and only renders interactive buttons when a handler is present, falling back to non-clickable badges otherwise.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995757024 -> f2882f59

Disposition: FIXED
Commit: f2882f59
Evidence: frontend/src/components/insight/AiInsightPanel.tsx:94; frontend/src/pages/Home.tsx:112; frontend/src/pages/Home.tsx:139; frontend/src/pages/__tests__/Home.test.tsx:318; frontend/src/pages/__tests__/Home.test.tsx:323
Reason: Home now short-circuits duplicate in-flight submissions, the visible AI submit control is disabled while loading or empty, and the tags fallback is restored with regression coverage for both empty sources and duplicate-submit protection.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995593905 -> f2882f59
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2995757037 -> f2882f59

Disposition: FIXED
Commit: d096f114
Evidence: frontend/src/pages/BMI/BMICalculatePage.tsx:70; frontend/src/pages/BMI/BMICalculatePage.tsx:85; frontend/src/pages/BMI/BMICalculatePage.tsx:286; frontend/src/pages/BMI/BMICalculatePage.tsx:319; frontend/src/pages/BMI/__tests__/BMICalculatePage.test.tsx:64; frontend/src/pages/BMI/__tests__/BMICalculatePage.test.tsx:80; frontend/src/pages/Home.tsx:117; frontend/src/pages/__tests__/Home.test.tsx:227
Reason: Added fieldset-plus-pressed semantics to BMI segmented controls and context toggles, promoted validation errors to an assertive alert region, and removed non-functional Home result action labels with regression checks so the card no longer advertises unavailable actions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2996145157 -> d096f114
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2996145163 -> d096f114
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1247#discussion_r2996145184 -> d096f114
