import Foundation

/// Protocol for HTTP client (enables testing via URLProtocol stubs).
public protocol HTTPClientProtocol: Sendable {
    func send<T: Decodable>(
        _ request: URLRequest,
        responseType: T.Type
    ) async throws -> T
}

/// Thin HTTP client: URLSession wrapper with JSON encode/decode and error mapping.
///
/// Responsibilities (strictly transport-only):
/// - Build URLRequest
/// - JSON encode/decode
/// - Distinguish 422 (validation) vs 400/500 (API errors) per audit contract
///
/// Forbidden:
/// - No BMI/waist/risk logic
/// - No business rule interpretation
/// - No i18n localization (error messages are passed through as-is)
public final class HTTPClient: HTTPClientProtocol, @unchecked Sendable {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    private func makeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }

    public func send<T: Decodable>(
        _ request: URLRequest,
        responseType: T.Type
    ) async throws -> T {
        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            // Treat empty successful responses as "no content" for callers that want `.empty` UX.
            // This keeps transport semantics centralized and avoids ad-hoc URLSession handling in services/VMs.
            if httpResponse.statusCode == 204 || data.isEmpty {
                throw APIError.api(statusCode: httpResponse.statusCode, message: "Empty response body")
            }
            return try decode(data, as: T.self)

        case 422:
            throw try decodeValidationError(from: data, statusCode: httpResponse.statusCode)

        case 400, 401, 403, 404, 409, 429, 500, 501, 502, 503, 504:
            throw try decodeAPIError(from: data, statusCode: httpResponse.statusCode)

        default:
            // Best-effort: try to surface server body text for debugging even on non-standard codes.
            throw try decodeAPIError(from: data, statusCode: httpResponse.statusCode)
        }
    }

    // MARK: - Private Helpers

    private func decode<T: Decodable>(_ data: Data, as type: T.Type) throws -> T {
        do {
            return try makeDecoder().decode(T.self, from: data)
        } catch {
            let message = error.localizedDescription
            throw APIError.decodingFailed(message)
        }
    }

    private func decodeValidationError(from data: Data, statusCode: Int) throws -> APIError {
        do {
            let error = try makeDecoder().decode(ValidationErrorResponse.self, from: data)
            return .validation(error)
        } catch {
            // Keep 422 branch distinct, but don't lose server message if payload is malformed.
            if let errorString = String(data: data, encoding: .utf8) {
                return .api(statusCode: statusCode, message: errorString)
            }
            return .api(statusCode: statusCode, message: "Unknown error (unable to decode server response)")
        }
    }

    private func decodeAPIError(from data: Data, statusCode: Int) throws -> APIError {
        do {
            let error = try makeDecoder().decode(SimpleErrorResponse.self, from: data)
            return .api(statusCode: statusCode, message: error.detail)
        } catch {
            // If simple error response fails to decode, try to extract detail as plain string
            // This handles edge cases where backend might return non-JSON error
            if let errorString = String(data: data, encoding: .utf8) {
                return .api(statusCode: statusCode, message: errorString)
            }
            // Preserve statusCode context even if payload is malformed/binary.
            return .api(
                statusCode: statusCode,
                message: "Unknown error (unable to decode server response)"
            )
        }
    }
}
