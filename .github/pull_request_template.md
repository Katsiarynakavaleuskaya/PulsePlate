# Pull Request

## 📋 Checklist

### Code Quality
- [ ] **No Duplication**: I have checked for and removed any duplicate code, imports, or logic
- [ ] **ESLint Clean**: `npm run lint` passes with 0 warnings
- [ ] **TypeScript Clean**: `npm run type-check` passes with 0 errors
- [ ] **Tests Pass**: All tests pass and coverage is maintained or improved

### Duplication Prevention
- [ ] **Static Analysis**: ESLint rules for duplication are satisfied
- [ ] **Shared Components**: Common UI patterns are extracted to reusable components
- [ ] **Business Logic**: Repeated logic is moved to custom hooks or services
- [ ] **No exact duplicate tests in the same test suite** (tests that cover the same functionality in different contexts (unit vs integration) or distinct edge cases are allowed)

### Testing Checklist
- [ ] **Unit Tests**: New functionality has unit tests
- [ ] **Integration Tests**: Critical paths are covered
- [ ] **Snapshot Tests**: UI changes have snapshot tests where appropriate

### Additional Considerations
- [ ] **Documentation**: Code is properly documented and README updated if needed
- [ ] **Breaking Changes**: Any breaking changes are documented and migration path provided
- [ ] **Performance**: No significant performance regressions introduced
- [ ] **Security**: Security implications have been considered and addressed
- [ ] **Accessibility**: Changes meet WCAG 2.1 AA standards where applicable

## 🎯 Description

<!-- Describe what this PR does -->

## 🧪 Testing Details

<!-- How was this tested? Include test coverage information -->

## 📸 Screenshots (if applicable)

<!-- Add screenshots for UI changes -->

## 🔗 Related Issues

<!-- Link to related issues -->

## 📋 Project-Specific Requirements

- [ ] **If applicable**: API types are generated from OpenAPI schema

---

**Note**: This PR template helps maintain code quality and prevents duplication. Please check all relevant boxes before requesting review.
