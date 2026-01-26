import Foundation

/// Unified API error model for thin HTTP adapter.
///
/// Distinguishes between validation errors (422) and API errors (400/500/501)
/// as per audit contract: 422 = detail array (plain English), 400/500 = detail string (localized).
public enum APIError: Error, Equatable, Sendable {
    /// Validation errors (422): FastAPI RequestValidationError format
    case validation(ValidationErrorResponse)

    /// API errors (400/401/403/500/501): localized detail string
    case api(statusCode: Int, message: String)

    /// Transport succeeded (2xx) but the server returned no body (204 or empty data).
    ///
    /// Contract: `HTTPClient.send(_:responseType:)` throws this so callers can present an explicit "empty"
    /// UX state without conflating it with API failures or JSON decoding errors.
    case emptyResponse(statusCode: Int)

    /// Request-body encoding failed (before the request was sent).
    case encodingFailed(String)

    /// JSON decoding failed
    case decodingFailed(String)

    /// Invalid HTTP response (not HTTPURLResponse)
    case invalidResponse

    /// Unhandled status code
    case unhandledStatusCode(Int)
}

extension APIError: LocalizedError {
    public var errorDescription: String? {
        switch self {
        case .validation(let response):
            return response.detail.map(\.msg).joined(separator: "\n")
        case .api(let statusCode, let message):
            return "Server error \(statusCode): \(message)"
        case .emptyResponse(let statusCode):
            return "Empty response (HTTP \(statusCode))"
        case .encodingFailed(let message):
            return message
        case .decodingFailed(let message):
            return "Decoding failed: \(message)"
        case .invalidResponse:
            return "Invalid HTTP response"
        case .unhandledStatusCode(let code):
            return "Unhandled status code: \(code)"
        }
    }
}
