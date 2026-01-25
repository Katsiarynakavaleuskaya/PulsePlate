import Foundation

/// Protocol for API client (enables testing via dependency injection).
public protocol APIClientProtocol: Sendable {
    func postRaw<Response: Decodable>(
        path: String,
        body: Data,
        headers: [String: String]
    ) async throws -> Response

    func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String]
    ) async throws -> Response

    func get<Response: Decodable>(
        path: String,
        headers: [String: String]
    ) async throws -> Response
}

extension APIClientProtocol {
    /// Convenience method with default empty headers.
    public func postRaw<Response: Decodable>(
        path: String,
        body: Data
    ) async throws -> Response {
        try await postRaw(path: path, body: body, headers: [:])
    }

    /// Convenience method with default empty headers.
    public func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body
    ) async throws -> Response {
        try await post(path: path, body: body, headers: [:])
    }

    /// Convenience method with default empty headers.
    public func get<Response: Decodable>(path: String) async throws -> Response {
        try await get(path: path, headers: [:])
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
    private let makeEncoder: @Sendable () -> JSONEncoder

    public init(
        baseURL: URL,
        httpClient: HTTPClientProtocol = HTTPClient(),
        makeEncoder: @escaping @Sendable () -> JSONEncoder = {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            return encoder
        }
    ) {
        self.baseURL = baseURL
        self.httpClient = httpClient
        self.makeEncoder = makeEncoder
    }

    private func normalizePath(_ path: String) -> String {
        // IMPORTANT:
        // `URL.appendingPathComponent()` expects a *path component*, not an absolute path.
        // Leading "/" can cause incorrect URL construction (drops existing path / normalizes unexpectedly).
        return path.hasPrefix("/") ? String(path.drop(while: { $0 == "/" })) : path
    }

    public func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String]
    ) async throws -> Response {
        var request = URLRequest(url: baseURL.appendingPathComponent(normalizePath(path)))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        headers.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }

        do {
            request.httpBody = try makeEncoder().encode(body)
        } catch {
            throw APIError.encodingFailed("Failed to encode request body: \(error.localizedDescription)")
        }

        return try await httpClient.send(request, responseType: Response.self)
    }

    public func postRaw<Response: Decodable>(
        path: String,
        body: Data,
        headers: [String: String]
    ) async throws -> Response {
        var request = URLRequest(url: baseURL.appendingPathComponent(normalizePath(path)))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        headers.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }

        request.httpBody = body
        return try await httpClient.send(request, responseType: Response.self)
    }

    public func get<Response: Decodable>(
        path: String,
        headers: [String: String]
    ) async throws -> Response {
        var request = URLRequest(url: baseURL.appendingPathComponent(normalizePath(path)))
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        headers.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }

        return try await httpClient.send(request, responseType: Response.self)
    }
}
