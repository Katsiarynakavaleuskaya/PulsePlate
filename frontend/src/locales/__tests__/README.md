# Locale Tests

This directory contains comprehensive tests for the application's internationalization (i18n) locale files.

## Test Coverage

The test suite validates locale files across multiple dimensions:

### Structural Validation (12 tests)
- File loading and parsing
- Consistent top-level structure across locales
- Valid JSON structure
- No undefined or null values
- Consistent nested structure for complex sections
- Non-empty string values
- No HTML tags in translations

### Content Validation (13 tests)
- No placeholder patterns (tightened regex to avoid false positives)
- Reasonable string lengths for UI components
- Valid Unicode characters only
- Consistent terminology across locales
- No duplicate values within locales
- Consistent capitalization patterns

**Total: 51 individual test cases**

## Placeholder Detection

The test suite includes sophisticated placeholder detection that avoids false positives:

- Uses word-boundary regex (`/\btest\b/i`) instead of broad patterns like `/test/i`
- Prevents false matches on legitimate words like "testosterona" or "intestino" in Spanish
- Covers common placeholder patterns: test, placeholder, todo, fixme, xxx, tbd

## Running Tests

```bash
# Run all locale tests
npm test -- src/locales/__tests__/

# Run specific test file
npm test -- src/locales/__tests__/locales.test.ts

# Run with coverage
npm test -- --coverage src/locales/__tests__/
```

## Test Maintenance

When adding new locales or modifying existing ones:

1. Update `SUPPORTED_LOCALES` array in `locales.test.ts`
2. Ensure new locale files follow the same structure as existing ones
3. Test string lengths fit within UI constraints
4. Verify no placeholder patterns are introduced
5. Update test counts in this README if new tests are added

## Locale File Structure

All locale files should follow this structure:

```json
{
  "common": {
    "ok": "OK",
    "cancel": "Cancel"
  },
  "paywall": {
    "title": "Premium Title",
    "subtitle": "Description of premium features",
    "cta": "Continue",
    "legal": "Legal text for subscriptions"
  }
}
```

## Error Messages

The tests provide detailed error messages to help identify issues:

- **Placeholder detection**: Shows which pattern was matched and in which key
- **Structure validation**: Identifies missing keys or type mismatches
- **Length validation**: Shows actual vs. maximum allowed lengths
- **Unicode validation**: Reports invalid character codes and positions
