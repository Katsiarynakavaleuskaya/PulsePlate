import Foundation

/// Protocol for BMI service (enables testing via dependency injection).
public protocol BMIServicing: Sendable {
    func calculateBMI(request: BMICalculateRequestDTO) async throws -> BMICalculateResponseDTO
}

/// BMI service — thin wrapper over APIClient.
///
/// Responsibilities:
/// - Call canonical BMI calculate endpoint
/// - Return response DTO as-is
///
/// Forbidden:
/// - No BMI/waist/risk logic
/// - No interpretation
/// - No i18n
/// - No soft paywall logic
public final class BMIService: BMIServicing, Sendable {

    private let apiClient: APIClientProtocol

    public init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    public func calculateBMI(
        request: BMICalculateRequestDTO
    ) async throws -> BMICalculateResponseDTO {
        try await apiClient.post(
            path: "/api/v1/bmi/calculate",
            body: request
        )
    }
}

// MARK: - Convenience Initializer

extension BMIService {
    /// Convenience initializer using AppConfig.baseURL().
    public convenience init(baseURL: URL? = nil) {
        let url = baseURL ?? AppConfig.baseURL()
        let client = APIClient(baseURL: url)
        self.init(apiClient: client)
    }
}
