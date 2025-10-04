# Locale Tests Documentation

This directory contains unit tests for the application's internationalization (i18n) locale files.

## Purpose
The tests ensure:
- Consistency of translation keys across all supported languages (English, Russian, Spanish).
- Absence of placeholder strings or problematic patterns in production translations.
- Correctness of domain-specific terminology.
- UI layout compatibility (e.g., translated strings do not overflow).

## Test Structure
- `locales.test.ts`: Contains the main test suite for locale validation.

## Test Cases
The suite currently contains 12 distinct test cases, covering:
- Structural validation (e.g., key consistency, null checks, empty strings): 5 tests
- Content validation (e.g., placeholder checks, length validation, duplicates): 3 tests
- Domain-specific validation (e.g., paywall structure, translation quality): 4 tests

## Running Tests
To run these tests, navigate to the `frontend` directory and execute:
```bash
npm test -- src/locales/__tests__/locales.test.ts
```

## Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| Structure | 5 | Validate JSON structure and consistency |
| Content | 3 | Validate translation content quality |
| Domain-Specific | 4 | Validate app-specific translation requirements |
| **Total** | **12** | **Complete validation coverage** |

## Maintenance Notes

When updating locale files:
1. Run the full test suite to ensure no regressions
2. Update test counts in this document if new tests are added
3. Verify UI layout constraints are still met
4. Test on actual devices to confirm text fits properly
5. Validate with native speakers for cultural appropriateness
