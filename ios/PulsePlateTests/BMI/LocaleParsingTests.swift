import XCTest
import Foundation


final class LocaleParsingTests: XCTestCase {
    private func parseDouble(_ text: String, locale: Locale = .current) -> Double? {
        let formatter = NumberFormatter()
        formatter.locale = locale
        formatter.numberStyle = .decimal
        return formatter.number(from: text)?.doubleValue
    }

    func test_parsesDotDecimalInEnLocale() throws {
        let locale = Locale(identifier: "en_US")
        XCTAssertEqual(try XCTUnwrap(parseDouble("70.5", locale: locale)), 70.5, accuracy: 0.0001)
        XCTAssertEqual(try XCTUnwrap(parseDouble("175.0", locale: locale)), 175.0, accuracy: 0.0001)
    }

    func test_parsesCommaDecimalInRuLocale() throws {
        let locale = Locale(identifier: "ru_RU")
        XCTAssertEqual(try XCTUnwrap(parseDouble("70,5", locale: locale)), 70.5, accuracy: 0.0001)
        XCTAssertEqual(try XCTUnwrap(parseDouble("175,0", locale: locale)), 175.0, accuracy: 0.0001)
    }

    func test_parsesCommaDecimalInEsLocale() throws {
        let locale = Locale(identifier: "es_ES")
        XCTAssertEqual(try XCTUnwrap(parseDouble("70,5", locale: locale)), 70.5, accuracy: 0.0001)
        XCTAssertEqual(try XCTUnwrap(parseDouble("175,0", locale: locale)), 175.0, accuracy: 0.0001)
    }

    func test_handlesInvalidInputGracefully() throws {
        let locale = Locale(identifier: "en_US")
        XCTAssertNil(parseDouble("invalid", locale: locale))
        XCTAssertNil(parseDouble("", locale: locale))
        XCTAssertNil(parseDouble("abc123", locale: locale))
        XCTAssertEqual(try XCTUnwrap(parseDouble(" 70.5 ", locale: locale)), 70.5, accuracy: 0.0001)
        XCTAssertEqual(try XCTUnwrap(parseDouble("-70.5", locale: locale)), -70.5, accuracy: 0.0001)
        XCTAssertEqual(try XCTUnwrap(parseDouble("1,000.5", locale: locale)), 1000.5, accuracy: 0.0001)
    }

    func test_handlesIntegerInput() throws {
        let locale = Locale(identifier: "en_US")
        XCTAssertEqual(try XCTUnwrap(parseDouble("70", locale: locale)), 70.0, accuracy: 0.0001)
        XCTAssertEqual(try XCTUnwrap(parseDouble("175", locale: locale)), 175.0, accuracy: 0.0001)
    }
}
