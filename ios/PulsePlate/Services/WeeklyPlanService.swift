import Foundation

public protocol WeeklyPlanServicing: Sendable {
    func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO
}

public struct WeeklyPlanRequest: Sendable {
    public let endpointPath: String          // e.g. "/api/v1/pro/meal/weekly"
    public let body: Data                   // JSON payload (targets/profile/etc.)
    public let apiKey: String?              // optional

    public init(endpointPath: String, body: Data, apiKey: String? = nil) {
        self.endpointPath = endpointPath
        self.body = body
        self.apiKey = apiKey
    }
}

public final class DefaultWeeklyPlanService: WeeklyPlanServicing, @unchecked Sendable {
    private let apiClient: APIClientProtocol

    public init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    public func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO {
        var headers: [String: String] = [:]
        if let key = request.apiKey {
            headers["X-API-Key"] = key
        }

        return try await apiClient.postRaw(
            path: request.endpointPath,
            body: request.body,
            headers: headers
        )
    }
}
