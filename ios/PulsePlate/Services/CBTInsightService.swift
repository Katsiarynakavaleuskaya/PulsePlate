import Foundation

protocol CBTInsightServicing: Sendable {
    func fetchInsight(query: String, apiKey: String) async throws -> CBTInsightResponseDTO
}

final class DefaultCBTInsightService: CBTInsightServicing, @unchecked Sendable {
    private let apiClient: APIClientProtocol
    private let endpointPath: String

    init(
        apiClient: APIClientProtocol,
        endpointPath: String = "/api/v1/pro/cbt/insight"
    ) {
        self.apiClient = apiClient
        self.endpointPath = endpointPath
    }

    func fetchInsight(query: String, apiKey: String) async throws -> CBTInsightResponseDTO {
        let request = CBTInsightRequestDTO(query: query)
        let headers = ["X-API-Key": apiKey]
        return try await apiClient.post(path: endpointPath, body: request, headers: headers)
    }
}
