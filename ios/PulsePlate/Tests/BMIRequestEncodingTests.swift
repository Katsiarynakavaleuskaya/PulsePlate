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
        let data = try encoder.encode(req)
        let obj = try JSONSerialization.jsonObject(with: data, options: [])
        let dict = obj as? [String: Any]

        XCTAssertNotNil(dict)
        XCTAssertNotNil(dict?["weight_kg"])
        XCTAssertNotNil(dict?["height_cm"])
        XCTAssertNotNil(dict?["age"])
        XCTAssertNotNil(dict?["gender"])
        XCTAssertNotNil(dict?["waist_cm"])
        XCTAssertNotNil(dict?["lang"])
    }
}
