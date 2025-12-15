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

public enum ShoppingListServiceError: Error, LocalizedError, Sendable {
    case http(Int, String?)
    case decoding(String)
    case transport(String)

    public var errorDescription: String? {
        switch self {
        case .http(let code, let msg):
            return "Server error \(code)\(msg.map { ": \($0)" } ?? "")"
        case .decoding(let msg):
            return "Failed to decode response: \(msg)"
        case .transport(let msg):
            return "Network error: \(msg)"
        }
    }
}

public final class DefaultShoppingListService: ShoppingListServicing, @unchecked Sendable {
    private let baseURL: URL
    private let session: URLSession

    public init(baseURL: URL, session: URLSession? = nil) {
        self.baseURL = baseURL
        if let session {
            self.session = session
        } else {
            let cfg = URLSessionConfiguration.ephemeral
            cfg.timeoutIntervalForRequest = 30
            cfg.timeoutIntervalForResource = 60
            self.session = URLSession(configuration: cfg)
        }
    }

    public func fetchShoppingList(request: ShoppingListRequest) async throws -> ShoppingListDTO {
        // Clean leading slash from endpoint path for safe URL construction
        let cleanPath = request.endpointPath.hasPrefix("/")
            ? String(request.endpointPath.dropFirst())
            : request.endpointPath

        let url = baseURL.appendingPathComponent(cleanPath)

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.setValue("application/json", forHTTPHeaderField: "Accept")

        if let key = request.apiKey {
            urlRequest.setValue(key, forHTTPHeaderField: "X-API-Key")
        }

        urlRequest.httpBody = request.body

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: urlRequest)
        } catch {
            // Wrap URLSession errors (network timeout, connection refused, etc.) as transport errors
            let message = (error as NSError).localizedDescription
            throw ShoppingListServiceError.transport(message)
        }

        guard let http = response as? HTTPURLResponse else {
            throw ShoppingListServiceError.transport("Invalid response type")
        }

        guard (200..<300).contains(http.statusCode) else {
            // Limit error message to 4KB to avoid excessive memory usage
            let msg = String(data: data.prefix(4096), encoding: .utf8)
            throw ShoppingListServiceError.http(http.statusCode, msg)
        }

        // Handle 204 No Content or empty response
        if http.statusCode == 204 || data.isEmpty {
            // Return empty shopping list as minimal valid DTO
            let emptyData = Data("""
            {
                "categories": [],
                "total_items": 0,
                "generated_at": "\(ISO8601DateFormatter().string(from: Date()))",
                "meta": {"source": "inline_plan", "unit_system": "metric", "warnings": ["empty_response"]}
            }
            """.utf8)
            return try JSONDecoder().decode(ShoppingListDTO.self, from: emptyData)
        }

        do {
            return try JSONDecoder().decode(ShoppingListDTO.self, from: data)
        } catch {
            throw ShoppingListServiceError.decoding(error.localizedDescription)
        }
    }
}
