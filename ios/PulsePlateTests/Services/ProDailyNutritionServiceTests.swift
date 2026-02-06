import XCTest
@testable import PulsePlate

final class ProDailyNutritionServiceTests: XCTestCase {

    func test_requestPath_isDeterministicAndSnakeCase() {
        let profile = ProNutritionProfile(
            sex: .female,
            age: 30,
            heightCm: 170,
            weightKg: 70,
            activity: .moderate,
            goal: .maintain
        )

        let req = ProDailyNutritionRequest(date: "2026-02-07", profile: profile, lang: "ru")
        XCTAssertEqual(
            req.path(),
            "/api/v1/pro/nutrition/daily?date=2026-02-07&sex=female&age=30&height_cm=170&weight_kg=70&activity=moderate&goal=maintain&lang=ru"
        )
    }

    func test_service_fetchDailyNutrition_sendsXApiKeyHeaderAndPath() async throws {
        // Fixed date in UTC to avoid timezone drift in date-only formatting.
        var comps = DateComponents()
        comps.calendar = Calendar(identifier: .gregorian)
        comps.timeZone = TimeZone(secondsFromGMT: 0)
        comps.year = 2026
        comps.month = 2
        comps.day = 7
        comps.hour = 12
        let date = try XCTUnwrap(comps.date)

        let profile = ProNutritionProfile(
            sex: .male,
            age: 40,
            heightCm: 180,
            weightKg: 85,
            activity: .active,
            goal: .gain
        )

        let api = CapturingAPIClient(
            result: NutritionData(
                date: "2026-02-07",
                segments: [],
                totalProgress: 0.0,
                dailyGoals: DailyGoals(vegetables: 4, protein: 1, carbs: 1, fats: 1)
            )
        )
        let service = DefaultProDailyNutritionService(apiClient: api)

        let result = try await service.fetchDailyNutrition(
            date: date,
            profile: profile,
            lang: "en",
            apiKey: "pp-placeholder" // pragma: allowlist secret
        )

        XCTAssertEqual(result.date, "2026-02-07")
        XCTAssertEqual(api.lastGetHeaders?["X-API-Key"], "pp-placeholder")
        XCTAssertEqual(
            api.lastGetPath,
            "/api/v1/pro/nutrition/daily?date=2026-02-07&sex=male&age=40&height_cm=180&weight_kg=85&activity=active&goal=gain&lang=en"
        )
    }
}

// MARK: - Test Double

// Test double stores mutable state; safe in tests (single-threaded usage).
private final class CapturingAPIClient: APIClientProtocol, @unchecked Sendable {
    var lastGetPath: String?
    var lastGetHeaders: [String: String]?
    private let result: NutritionData

    init(result: NutritionData) {
        self.result = result
    }

    func postRaw<Response: Decodable>(
        path: String,
        body: Data,
        headers: [String: String]
    ) async throws -> Response {
        fatalError("Not used in this test")
    }

    func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String]
    ) async throws -> Response {
        fatalError("Not used in this test")
    }

    func get<Response: Decodable>(
        path: String,
        headers: [String: String]
    ) async throws -> Response {
        lastGetPath = path
        lastGetHeaders = headers

        if Response.self == NutritionData.self {
            // swiftlint:disable:next force_cast
            return result as! Response
        }
        fatalError("Unexpected response type: \(Response.self)")
    }
}
