# Locale Tests Summary

## Test Suite Overview

The locale test suite provides comprehensive validation for internationalization files across three supported languages: English (en), Spanish (es), and Russian (ru).

## Test Categories

### Structural Validation (12 tests)
Tests that verify the basic integrity and consistency of locale files:

1. **File Loading**: All supported locale files can be loaded without errors
2. **Top-level Structure**: Consistent keys across all locales
3. **JSON Validity**: Proper JSON parsing and structure
4. **Null/Undefined Values**: No null or undefined values in locale data
5. **Nested Structure**: Consistent structure for complex sections (paywall)
6. **Non-empty Strings**: All string values have content
7. **HTML Tags**: No HTML markup in translation strings
8. **Unicode Validity**: Only valid Unicode characters
9. **Type Consistency**: Matching data types across locales
10. **Key Presence**: All expected keys exist in each locale
11. **Object Structure**: Proper object nesting and arrays
12. **Encoding**: UTF-8 compatibility

### Content Validation (13 tests)
Tests that validate the actual content and quality of translations:

1. **Placeholder Detection**: No placeholder patterns (test, todo, fixme, etc.)
2. **String Lengths**: Reasonable lengths for UI components
3. **Terminology Consistency**: Consistent terms across locales
4. **Duplicate Values**: No unintended duplicate translations
5. **Capitalization**: Consistent capitalization patterns
6. **Special Characters**: Proper handling of locale-specific characters
7. **Whitespace**: Proper whitespace handling
8. **Punctuation**: Consistent punctuation across locales
9. **Number Formatting**: Locale-appropriate number formatting
10. **Date/Time Formats**: Consistent date and time representations
11. **Currency Symbols**: Proper currency symbol usage
12. **Measurement Units**: Consistent unit representations
13. **Accessibility**: Screen reader friendly text

## Test Implementation Details

### Placeholder Pattern Detection
The test suite uses tightened regex patterns to avoid false positives:

- **Before**: `/test/i` - incorrectly matched "testosterona", "intestino"
- **After**: `/\btest\b/i` - only matches standalone "test" word
- **Additional patterns**: placeholder, todo, fixme, xxx, tbd (all word-boundary)

### UI Constraints
Maximum recommended lengths for different UI elements:
- **Titles**: 50 characters
- **Subtitles**: 100 characters
- **Buttons**: 30 characters
- **Labels**: 40 characters

### Unicode Validation
- Checks for invalid control characters (except common whitespace)
- Validates character encoding integrity
- Ensures proper Unicode normalization

## Test Results Summary

**Total Tests: 51**
- Structural Validation: 12 tests
- Content Validation: 13 tests

All tests must pass for locale files to be considered production-ready.

## Maintenance Notes

When updating locale files:
1. Run the full test suite to ensure no regressions
2. Update test counts in this document if new tests are added
3. Verify UI layout constraints are still met
4. Test on actual devices to confirm text fits properly
5. Validate with native speakers for cultural appropriateness

## Related Files
- `frontend/src/locales/__tests__/locales.test.ts` - Main test implementation
- `frontend/src/locales/__tests__/README.md` - Test documentation
- `frontend/src/locales/*.json` - Locale data files
