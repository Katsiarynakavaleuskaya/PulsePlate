import XCTest
import Foundation
@testable import PulsePlate


final class BMIRequestEncodingTests: XCTestCase {
    func test_encodesSnakeCaseKeys() throws {
        let req = BMIRequest(
            weightKg: 70,
            heightCm: 175,
            age: 30,
            gender: "female",
            waistCm: 80,
            lang: "en"
        )
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let data = try encoder.encode(req)
        let json = String(data: data, encoding: .utf8) ?? ""

        XCTAssertTrue(json.contains("\"weight_kg\""))
        XCTAssertTrue(json.contains("\"height_cm\""))
        XCTAssertTrue(json.contains("\"age\""))
        XCTAssertTrue(json.contains("\"gender\""))
        XCTAssertTrue(json.contains("\"waist_cm\""))
        XCTAssertTrue(json.contains("\"lang\""))
    }
}
