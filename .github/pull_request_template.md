# Pull Request

## 📋 Checklist

### Code Quality

- [ ] **ESLint Clean**: lint script passes with 0 warnings
- [ ] **TypeScript Clean**: type-check script passes with 0 errors
- [ ] **Tests Pass**: All tests pass and coverage is maintained or improved
- [ ] **Security/Secrets**: No secrets/PII committed; dependency audit passes
- [ ] **Privacy/Compliance**: User-data handling unchanged or documented
- [ ] **Accessibility (a11y)**: Keyboard/focus/ARIA validated; screenshots include alt text
- [ ] **i18n/l10n**: User-facing strings externalized; formats (date/number/currency) correct
- [ ] **Performance**: No obvious regressions; heavy UI paths profiled if changed
- [ ] **Docs/Changelog**: Relevant docs/README/ADR/CHANGELOG updated
- [ ] **CI**: All workflows green for this PR

### Duplication Prevention

- [ ] **No Duplication**: I have checked for and removed any duplicate code, imports, or logic
- [ ] **Static Analysis**: ESLint rules for duplication are satisfied
- [ ] **Shared Components**: Common UI patterns are extracted to reusable components
- [ ] **Business Logic**: Repeated logic is moved to custom hooks or services
- [ ] **No exact duplicate tests in the same test suite** (tests that cover the same functionality in different contexts (unit vs integration) or distinct edge cases are allowed)

### Testing Checklist

- [ ] **Unit Tests**: New functionality has unit tests
- [ ] **Integration Tests**: Critical paths are covered
- [ ] **Snapshot Tests**: UI changes have snapshot tests where appropriate
- [ ] **E2E/Smoke**: Key flows covered by E2E or smoke tests (if applicable)
- [ ] **Visual Regression**: Visual checks run for changed UI (if applicable)

### Additional Considerations

- [ ] **Documentation**: Code is properly documented and README updated if needed
- [ ] **Breaking Changes**: Any breaking changes are documented and migration path provided
- [ ] **Performance**: No significant performance regressions introduced
- [ ] **Security**: Security implications have been considered and addressed
- [ ] **Accessibility**: Changes meet WCAG 2.1 AA standards where applicable

## 🎯 Description

<!-- Describe what this PR does -->

## 🚦 Rollout / Feature Flags

<!-- List flags introduced/changed and rollout details -->
- Flag keys and default values:
- Exposure/targeting plan (e.g., % rollout, cohorts):
- Kill switch and monitoring:
- Telemetry/analytics events added:
- Cleanup plan/timeline:

## 🔍 Duplication Check

<!-- List any potential duplications you found and how you addressed them -->

## 🧪 Testing Details

<!-- How was this tested? Include test coverage information -->

## ⚠️ Breaking Changes / Migrations

<!-- Note any breaking API/route/schema changes and required migrations or client updates -->

## 📸 Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

## 🔗 Related Issues

<!-- Link to related issues -->

## 📋 Project-Specific Requirements

- [ ] **If applicable**: API types are generated from OpenAPI schema

---

**Note**: This PR template helps maintain code quality and prevents duplication. Please check all relevant boxes before requesting review.
