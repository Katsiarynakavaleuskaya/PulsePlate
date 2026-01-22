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
    private let decoder: JSONDecoder

    public init(
        session: URLSession = .shared,
        decoder: JSONDecoder = JSONDecoder()
    ) {
        self.session = session
        self.decoder = decoder
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
            return try decode(data, as: T.self)

        case 422:
            throw try decodeValidationError(from: data)

        case 400, 401, 403, 500, 501:
            throw try decodeAPIError(from: data, statusCode: httpResponse.statusCode)

        default:
            throw APIError.unhandledStatusCode(httpResponse.statusCode)
        }
    }

    // MARK: - Private Helpers

    private func decode<T: Decodable>(_ data: Data, as type: T.Type) throws -> T {
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            let message = error.localizedDescription
            throw APIError.decodingFailed(message)
        }
    }

    private func decodeValidationError(from data: Data) throws -> APIError {
        do {
            let error = try decoder.decode(ValidationErrorResponse.self, from: data)
            return .validation(error)
        } catch {
            // If validation error response itself fails to decode, treat as decoding error
            throw APIError.decodingFailed("Failed to decode validation error: \(error.localizedDescription)")
        }
    }

    private func decodeAPIError(from data: Data, statusCode: Int) throws -> APIError {
        do {
            let error = try decoder.decode(SimpleErrorResponse.self, from: data)
            return .api(statusCode: statusCode, message: error.detail)
        } catch {
            // If simple error response fails to decode, try to extract detail as plain string
            // This handles edge cases where backend might return non-JSON error
            if let errorString = String(data: data, encoding: .utf8) {
                return .api(statusCode: statusCode, message: errorString)
            }
            throw APIError.decodingFailed("Failed to decode API error: \(error.localizedDescription)")
        }
    }
}
