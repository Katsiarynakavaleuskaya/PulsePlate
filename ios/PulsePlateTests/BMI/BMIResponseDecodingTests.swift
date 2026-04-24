import XCTest
import Foundation
@testable import PulsePlate

final class BMIResponseDecodingTests: XCTestCase {
    func test_decodesSuccess() throws {
        let dto = try JSONDecoder().decode(BMICalculateResponseDTO.self, from: BMIFixtures.successJSON())
        XCTAssertEqual(dto.bmi, 22.86, accuracy: 0.0001)
        XCTAssertEqual(dto.category, "normal")
        XCTAssertEqual(dto.group, "general")
        XCTAssertEqual(dto.groupDisplay, "General")
        XCTAssertNotNil(dto.visualization)
        XCTAssertEqual(dto.nextBestAction?.type, "unlock_targets")
        XCTAssertEqual(dto.nextBestAction?.recommendedSurface, "pro_targets")
        XCTAssertEqual(dto.nextBestAction?.recommendedTier, "PRO")
        XCTAssertEqual(dto.nextBestAction?.triggerReason, "post_bmi")
        XCTAssertEqual(dto.nextBestAction?.whyNow, "post_bmi_baseline_body_metrics")
    }

    func test_decodesPregnantNullables() throws {
        let dto = try JSONDecoder().decode(BMICalculateResponseDTO.self, from: BMIFixtures.pregnantJSON())
        XCTAssertNil(dto.category)
        XCTAssertNil(dto.visualization)
        XCTAssertNil(dto.nextBestAction)
    }
}
