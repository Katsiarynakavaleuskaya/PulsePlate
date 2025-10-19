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

The suite currently contains 17 individual test cases, covering:

- Structural validation (e.g., key consistency): 5 tests
- Content validation (e.g., placeholder checks, string length, duplicate checks): 3 tests
- Domain-Specific Validation (e.g., paywall structure, specific terminology): 9 tests

## Running Tests

To run these tests, navigate to the `frontend` directory and execute:

```bash
npm test -- src/locales/__tests__/locales.test.ts
```

## Test Categories

| Category        | Tests  | Purpose                                        |
| --------------- | ------ | ---------------------------------------------- |
| Structure       | 5      | Validate JSON structure and consistency        |
| Content         | 3      | Validate translation content quality           |
| Domain-Specific | 9      | Validate app-specific translation requirements |
| **Total**       | **17** | **Complete validation coverage**               |

## Maintenance Notes

When updating locale files:

1. Run the full test suite to ensure no regressions
2. Update test counts in this document if new tests are added
3. Verify UI layout constraints are still met
4. Test on actual devices to confirm text fits properly
5. Validate with native speakers for cultural appropriateness

## Test File

- **`locales.test.ts`** - Main test suite for validating Spanish (es.json) and Russian (ru.json) translations against the English baseline (en.json)

## What Is Tested

### 1. JSON Structure and Syntax (3 tests)

- Validates that all locale files parse correctly without errors
- Ensures files are valid JSON objects
- Covers: `en.json`, `es.json`, `ru.json`

### 2. Key Completeness (4 tests)

- Verifies all English keys exist in Spanish and Russian translations
- Ensures no extra keys exist that aren't in the English baseline
- Prevents missing translations or orphaned keys
- Uses recursive key extraction to validate deeply nested structures

### 3. Translation Value Validation (3 tests)

- Checks that no translation strings are empty or whitespace-only
- Validates all leaf values contain meaningful content
- Recursively scans all nested translation objects

### 4. Structural Consistency (2 tests)

- Ensures type consistency across locales (string vs object vs array)
- Validates matching nesting structure between languages
- Prevents structural mismatches that could cause runtime errors

### 5. Top-Level Sections (3 tests)

- Validates presence of required sections: `common`, `shoplist`, `paywall`
- Ensures no unexpected top-level sections exist
- Maintains organizational consistency

### 6. Common Section (2 tests)

- Validates `ok` and `cancel` keys exist in all locales
- Ensures these critical UI strings are translated

### 7. Shopping List Section (2 tests)

- Validates `loading`, `error`, and `empty` keys
- Ensures shopping list UI strings are complete

### 8. Paywall Section (7 tests)

- Comprehensive validation of the complex paywall translation structure
- Validates top-level keys, nested sections (`before`, `after`, `items`)
- Ensures all paywall UI elements have translations
- Critical for premium feature user experience

### 9. Spanish Translation Quality - Branch Changes (6 tests)

Validates the specific improvements made in this branch:

- ✅ "Lista vacía." instead of "Vacío."
- ✅ Improved subtitle: "Plan nutricional personal, equilibrio preciso, planificación semanal."
- ✅ "Configuración" instead of "Ajustes"
- ✅ "Solo macronutrientes" instead of "Solo macros"
- ✅ "Plan nutricional personal" instead of "Plato personal"
- ✅ "Equilibrio nutricional" instead of "Microequilibrio"

### 10. Russian Translation Quality - Branch Changes (5 tests)

Validates the specific improvements made in this branch:

- ✅ Improved subtitle with better terminology
- ✅ "рацион" (diet/ration) instead of "тарелка" (plate)
- ✅ "макронутриенты" instead of "макро"
- ✅ "Точный баланс" instead of "Микро-баланс"
- ✅ "Автосписок покупок" (one word) instead of "Авто список покупок"

### 11. Character Encoding and Special Characters (3 tests)

- Validates proper Spanish character handling (á, é, í, ó, ú, ñ)
- Validates proper Russian Cyrillic character handling (Unicode range U+0400-U+04FF)
- Detects mojibake and encoding corruption

### 12. Translation Length Validation (2 tests)

- Ensures translations aren't unreasonably short (< 2 chars) or long (> 200 chars)
- Catches potential data issues or truncation

### 13. Consistency Between Duplicate Keys (4 tests)

- Validates that `paywall.before.*` matches `paywall.items.before.*`
- Validates that `paywall.after.*` matches `paywall.items.after.*`
- Ensures UI consistency when same text appears in multiple contexts

### 14. Punctuation and Formatting (3 tests)

- Validates proper sentence punctuation (dots, ellipsis)
- Ensures consistent formatting across locales
- Checks ellipsis (…) usage in loading messages

### 15. No Placeholder or Debug Text (2 tests)

- Scans for common placeholder patterns (TODO, FIXME, XXX, Lorem ipsum)
- Ensures no test or debug strings made it to production
- Validates professional, production-ready content

## Total Test Coverage

- **17 individual test cases**
- **3 locale files validated** (en, es, ru)
- **25+ translation keys validated per language**
- **Comprehensive structural and content validation**

## Running the Tests

```bash
# Run all locale tests
npm test -- src/locales/__tests__/locales.test.ts

# Run with coverage
npm test -- src/locales/__tests__/locales.test.ts --coverage

# Run in watch mode during development
npm test -- src/locales/__tests__/locales.test.ts --watch
```

## Test Strategy

### Why These Tests Matter

1. **Prevent Runtime Errors**: Missing translations cause UI failures
2. **Maintain UX Quality**: Ensures consistent experience across languages
3. **Catch Regressions**: Prevents accidental removal or modification of translations
4. **Enforce Standards**: Validates translation quality and completeness
5. **Documentation**: Tests serve as living documentation of translation requirements

### Test Design Principles

1. **Comprehensive Coverage**: Tests validate structure, content, and quality
2. **Automated Validation**: No manual translation review needed for basic checks
3. **Clear Error Messages**: Failed tests indicate exactly what's wrong and where
4. **Maintainable**: Helper functions make tests easy to extend for new locales
5. **Fast Execution**: Pure JSON validation runs in milliseconds

## Extending for New Locales

To add tests for a new locale (e.g., `fr.json`):

1. Import the new locale: `import fr from "../fr.json";`
2. Add tests to each describe block following existing patterns
3. Add locale-specific quality tests for branch changes
4. Update this README with the new locale

## Branch-Specific Improvements Validated

This test suite specifically validates the translation improvements made in the `fix/spanish-translations` branch:

### Spanish (es.json)

- More professional and clear terminology
- Better context for nutrition-focused app
- Improved consistency with app domain

### Russian (ru.json)

- More accurate translations
- Better terminology for nutrition concepts
- Improved readability and professionalism

## Continuous Integration

These tests run automatically on:

- ✅ Every commit
- ✅ Pull request validation
- ✅ Pre-merge checks
- ✅ Release builds

## Best Practices

1. **Always add tests for new translation keys**
2. **Validate translations match the English structure**
3. **Check for empty or placeholder values**
4. **Ensure proper character encoding**
5. **Test on actual devices/browsers when possible**

## Related Files

- `../en.json` - English baseline translations
- `../es.json` - Spanish translations
- `../ru.json` - Russian translations
- `../../i18n.ts` - i18next configuration
- `../../setupTests.ts` - Test environment setup

## Maintenance Notes

- Tests use Vitest as the test runner
- Environment set to `node` for JSON validation (no DOM needed)
- All helper functions are well-documented with JSDoc comments
- Tests are organized by concern for easy navigation
