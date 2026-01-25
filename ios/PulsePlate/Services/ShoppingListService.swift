import Foundation

public protocol ShoppingListServicing: Sendable {
    func fetchShoppingList(request: ShoppingListRequest) async throws -> ShoppingListDTO
}

public struct ShoppingListRequest: Sendable {
    public let endpointPath: String          // e.g. "/api/v1/pro/meal/shopping-list"
    public let body: Data                   // JSON payload (plan_data + preferences)
    public let apiKey: String?              // PRO tier API key

    public init(endpointPath: String, body: Data, apiKey: String? = nil) {
        self.endpointPath = endpointPath
        self.body = body
        self.apiKey = apiKey
    }
}

public final class DefaultShoppingListService: ShoppingListServicing, @unchecked Sendable {
    private let apiClient: APIClientProtocol

    public init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    public func fetchShoppingList(request: ShoppingListRequest) async throws -> ShoppingListDTO {
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
