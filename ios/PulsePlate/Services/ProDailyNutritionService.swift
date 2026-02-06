import Foundation

// MARK: - PRO Daily Nutrition (canonical Plate endpoint)
//
// RU: Клиент для канонического эндпоинта:
//     GET /api/v1/pro/nutrition/daily
// EN: Client for canonical endpoint:
//     GET /api/v1/pro/nutrition/daily

protocol ProDailyNutritionServicing: Sendable {
    func fetchDailyNutrition(
        date: Date,
        profile: ProNutritionProfile,
        lang: String,
        apiKey: String
    ) async throws -> NutritionData
}

struct ProDailyNutritionRequest: Sendable, Equatable {
    let date: String // YYYY-MM-DD
    let profile: ProNutritionProfile
    let lang: String

    init(date: String, profile: ProNutritionProfile, lang: String) {
        self.date = date
        self.profile = profile
        self.lang = lang
    }

    func path() -> String {
        var components = URLComponents()
        components.path = "/api/v1/pro/nutrition/daily"

        // Deterministic order is important for testing and debugging.
        components.queryItems = [
            URLQueryItem(name: "date", value: date),
            URLQueryItem(name: "sex", value: profile.sex.rawValue),
            URLQueryItem(name: "age", value: String(profile.age)),
            URLQueryItem(name: "height_cm", value: String(profile.heightCm)),
            URLQueryItem(name: "weight_kg", value: String(profile.weightKg)),
            URLQueryItem(name: "activity", value: profile.activity.rawValue),
            URLQueryItem(name: "goal", value: profile.goal.rawValue),
            URLQueryItem(name: "lang", value: lang),
        ]

        // URLComponents with only path+query produces a relative string like:
        // "/api/v1/pro/nutrition/daily?..."
        // APIClient will normalize leading "/" correctly.
        return components.string ?? "/api/v1/pro/nutrition/daily"
    }
}

final class DefaultProDailyNutritionService: ProDailyNutritionServicing, @unchecked Sendable {
    private let apiClient: APIClientProtocol

    init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    func fetchDailyNutrition(
        date: Date,
        profile: ProNutritionProfile,
        lang: String,
        apiKey: String
    ) async throws -> NutritionData {
        let dateString = Self.dateOnlyString(date)
        let request = ProDailyNutritionRequest(date: dateString, profile: profile, lang: lang)

        let headers = ["X-API-Key": apiKey]
        return try await apiClient.get(path: request.path(), headers: headers)
    }

    private static func dateOnlyString(_ date: Date) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        formatter.timeZone = TimeZone(identifier: "UTC")
        return formatter.string(from: date)
    }
}
