import Testing
import Foundation
@testable import PulsePlate

struct BMIResponseDecodingTests {
    @Test func decodesSuccess() throws {
        let dto = try JSONDecoder().decode(BMIResponse.self, from: BMIFixtures.successJSON())
        #expect(dto.group == "general")
        #expect(dto.groupDisplay == "General")
        #expect(dto.visualization != nil)
    }

    @Test func decodesPregnantNullables() throws {
        let dto = try JSONDecoder().decode(BMIResponse.self, from: BMIFixtures.pregnantJSON())
        #expect(dto.category == nil)
        #expect(dto.visualization == nil)
    }
}
