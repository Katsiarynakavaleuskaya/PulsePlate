import Testing
import Foundation

/// Tests for locale-aware decimal parsing in BMI input.
///
/// Verifies that UI correctly normalizes user input (comma/dot separators)
/// without adding BMI business logic.
struct LocaleParsingTests {
    /// Helper to parse decimal with locale-aware NumberFormatter.
    private func parseDouble(_ text: String, locale: Locale = .current) -> Double? {
        let formatter = NumberFormatter()
        formatter.locale = locale
        formatter.numberStyle = .decimal
        return formatter.number(from: text)?.doubleValue
    }

    @Test("Parses dot decimal in EN locale")
    func parsesDotDecimalInEnLocale() {
        let locale = Locale(identifier: "en_US")
        #expect(parseDouble("70.5", locale: locale) == 70.5)
        #expect(parseDouble("175.0", locale: locale) == 175.0)
    }

    @Test("Parses comma decimal in RU locale")
    func parsesCommaDecimalInRuLocale() {
        let locale = Locale(identifier: "ru_RU")
        #expect(parseDouble("70,5", locale: locale) == 70.5)
        #expect(parseDouble("175,0", locale: locale) == 175.0)
    }

    @Test("Parses comma decimal in ES locale")
    func parsesCommaDecimalInEsLocale() {
        let locale = Locale(identifier: "es_ES")
        #expect(parseDouble("70,5", locale: locale) == 70.5)
        #expect(parseDouble("175,0", locale: locale) == 175.0)
    }

    @Test("Handles invalid input gracefully")
    func handlesInvalidInput() {
        let locale = Locale(identifier: "en_US")
        #expect(parseDouble("invalid", locale: locale) == nil)
        #expect(parseDouble("", locale: locale) == nil)
        #expect(parseDouble("abc123", locale: locale) == nil)
    }

    @Test("Handles integer input")
    func handlesIntegerInput() {
        let locale = Locale(identifier: "en_US")
        #expect(parseDouble("70", locale: locale) == 70.0)
        #expect(parseDouble("175", locale: locale) == 175.0)
    }
}
