import XCTest
@testable import PulsePlate

/// Tests for BMIService "thinness" — verifies no business logic, only transport.
final class BMIServiceThinAdapterTests: XCTestCase {

    // Test double stores mutable state; safe in tests (single-threaded usage).
    fileprivate final class FakeAPIClient: APIClientProtocol, @unchecked Sendable {
        var lastPath: String?
        var lastBody: BMICalculateRequestDTO?

        func post<Response: Decodable, Body: Encodable>(
            path: String,
            body: Body,
            headers: [String: String]
        ) async throws -> Response {
            lastPath = path
            if let bmiBody = body as? BMICalculateRequestDTO {
                lastBody = bmiBody
            }

            // Return minimal valid response matching BMICalculateResponseDTO
            let json = """
            {
              "bmi": 22.5,
              "category": "normal",
              "group": "general",
              "group_display": "General",
              "interpretation": "Your BMI is within the normal range.",
              "wht_ratio": null,
              "waist_risk": null,
              "notes": [],
              "age_band": "adult",
              "visualization": null,
              "interpretation_v1": null,
              "soft_paywall": null
            }
            """.data(using: .utf8)!

            return try JSONDecoder().decode(Response.self, from: json)
        }
    }

    func test_calculate_callsCanonicalEndpoint() async throws {
        let api = FakeAPIClient()
        let service = BMIService(apiClient: api)

        let req = BMICalculateRequestDTO(weightKg: 70.0, heightCm: 175.0, age: 30)

        let response = try await service.calculateBMI(request: req)

        XCTAssertEqual(api.lastPath, "/api/v1/bmi/calculate")
        XCTAssertNotNil(api.lastBody)
        XCTAssertEqual(api.lastBody?.weightKg, 70.0)
        XCTAssertEqual(api.lastBody?.heightCm, 175.0)
        XCTAssertEqual(api.lastBody?.age, 30)
        XCTAssertEqual(response.bmi, 22.5)
        XCTAssertEqual(response.group, "general")
        XCTAssertEqual(response.category, "normal")
    }

    func test_calculate_returnsBMICalculateResponseDTO() async throws {
        // Integration-style test: verify DTO structure matches contract
        let json = """
        {
          "bmi": 24.69,
          "category": "normal",
          "group": "general",
          "group_display": "General",
          "interpretation": "Your BMI is within the normal range.",
          "wht_ratio": 0.51,
          "waist_risk": {
            "wht_ratio": 0.51,
            "risk_level": "low",
            "notes": []
          },
          "notes": [],
          "age_band": "adult",
          "visualization": {
            "ranges": [
              {"key": "bmi.underweight", "from": 0, "to": 18.5},
              {"key": "bmi.normal", "from": 18.5, "to": 25}
            ]
          },
          "interpretation_v1": null,
          "soft_paywall": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let response = try decoder.decode(BMICalculateResponseDTO.self, from: json)

        XCTAssertEqual(response.bmi, 24.69)
        XCTAssertEqual(response.category, "normal")
        XCTAssertEqual(response.group, "general")
        XCTAssertEqual(response.groupDisplay, "General")
        XCTAssertEqual(response.interpretation, "Your BMI is within the normal range.")
        XCTAssertEqual(response.whtRatio, 0.51)
        XCTAssertNotNil(response.waistRisk)
        XCTAssertEqual(response.waistRisk?.riskLevel, "low")
        XCTAssertEqual(response.ageBand, "adult")
        XCTAssertNotNil(response.visualization)
        XCTAssertEqual(response.visualization?.ranges.count, 2)
        XCTAssertEqual(response.visualization?.ranges.first?.key, "bmi.underweight")
        XCTAssertEqual(response.visualization?.ranges.first?.from, 0)
        XCTAssertEqual(response.visualization?.ranges.first?.to, 18.5)
    }

    func test_calculate_nullableCategory_decodesCorrectly() async throws {
        // Test that category can be nil (child/teen/pregnant)
        let json = """
        {
          "bmi": 18.0,
          "category": null,
          "group": "child",
          "group_display": "Child",
          "interpretation": "BMI categories are not provided for children.",
          "wht_ratio": null,
          "waist_risk": null,
          "notes": [],
          "age_band": "child",
          "visualization": null,
          "interpretation_v1": null,
          "soft_paywall": null
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let response = try decoder.decode(BMICalculateResponseDTO.self, from: json)

        XCTAssertNil(response.category)
        XCTAssertEqual(response.group, "child")
    }
}
