import Foundation

/// Protocol for API client (enables testing via dependency injection).
public protocol APIClientProtocol: Sendable {
    func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String]
    ) async throws -> Response
}

extension APIClientProtocol {
    /// Convenience method with default empty headers.
    public func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body
    ) async throws -> Response {
        try await post(path: path, body: body, headers: [:])
    }
}

/// Base API client for PulsePlate backend.
///
/// Responsibilities:
/// - Build URLRequest with baseURL
/// - Set headers (Content-Type, X-API-Key if provided)
/// - JSON encode request body
/// - Delegate sending & error handling to HTTPClient
///
/// Forbidden:
/// - No business logic
/// - No endpoint-specific behavior
public final class APIClient: APIClientProtocol, Sendable {

    private let baseURL: URL
    private let httpClient: HTTPClientProtocol
    private let encoder: JSONEncoder

    public init(
        baseURL: URL,
        httpClient: HTTPClientProtocol = HTTPClient(),
        encoder: JSONEncoder = JSONEncoder()
    ) {
        self.baseURL = baseURL
        self.httpClient = httpClient
        self.encoder = encoder
    }

    public func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String] = [:]
    ) async throws -> Response {

        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        headers.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }

        do {
            request.httpBody = try encoder.encode(body)
        } catch {
            throw APIError.decodingFailed("Failed to encode request body: \(error.localizedDescription)")
        }

        return try await httpClient.send(request, responseType: Response.self)
    }
}
