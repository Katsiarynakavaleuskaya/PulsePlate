import XCTest
import Foundation
@testable import PulsePlate


final class BMIResponseDecodingTests: XCTestCase {
    func test_decodesSuccess() throws {
        let dto = try JSONDecoder().decode(BMIResponse.self, from: BMIFixtures.successJSON())
        XCTAssertEqual(dto.group, "general")
        XCTAssertEqual(dto.groupDisplay, "General")
        XCTAssertNotNil(dto.visualization)
    }

    func test_decodesPregnantNullables() throws {
        let dto = try JSONDecoder().decode(BMIResponse.self, from: BMIFixtures.pregnantJSON())
        XCTAssertNil(dto.category)
        XCTAssertNil(dto.visualization)
    }
}
