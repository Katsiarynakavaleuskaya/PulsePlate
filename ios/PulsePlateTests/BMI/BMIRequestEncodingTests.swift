import Testing
import Foundation
@testable import PulsePlate

struct BMIRequestEncodingTests {
    @Test func encodesSnakeCaseKeys() throws {
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

        #expect(json.contains("\"weight_kg\""))
        #expect(json.contains("\"height_cm\""))
        #expect(json.contains("\"age\""))
        #expect(json.contains("\"gender\""))
        #expect(json.contains("\"waist_cm\""))
        #expect(json.contains("\"lang\""))
    }
}
