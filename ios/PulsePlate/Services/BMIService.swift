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

// MARK: - Legacy Compatibility (temporary, until UI migration)

/// Legacy BMI service using old types (BMIRequest/BMIResponse).
/// This is a compatibility shim for existing UI code.
/// TODO: Remove after UI migration to BMICalculate*DTO (tracked in BACKLOG_LEDGER.md)
public protocol LegacyBMIServicing: Sendable {
    func calculateBMI(request: BMIRequest) async throws -> BMIResponse
}

/// Legacy error type for backward compatibility with UI.
/// TODO: Migrate UI to APIError (tracked in BACKLOG_LEDGER.md)
public enum BMIServiceError: Error, LocalizedError, Sendable, Equatable {
    case http(Int, String?)
    case encoding(String)
    case decoding(String)
    case transport(String)
    case validation([ValidationError])

    public struct ValidationError: Codable, Sendable, Equatable {
        public let type: String
        public let loc: [String]
        public let msg: String
        public let input: AnyCodable?
    }

    public var errorDescription: String? {
        switch self {
        case .http(let code, let msg):
            return "Server error \(code)\(msg.map { ": \($0)" } ?? "")"
        case .encoding(let msg):
            return "Encode error: \(msg)"
        case .decoding(let msg):
            return "Decode error: \(msg)"
        case .transport(let msg):
            return "Network error: \(msg)"
        case .validation(let errors):
            return errors.map(\.msg).joined(separator: "\n")
        }
    }
}

/// Legacy BMI service implementation (temporary compatibility shim).
/// TODO: Remove after UI migration (tracked in BACKLOG_LEDGER.md)
public final class DefaultBMIService: LegacyBMIServicing, @unchecked Sendable {
    private let baseURL: URL
    private let session: URLSession

    public init(baseURL: URL? = nil, session: URLSession? = nil) {
        self.baseURL = baseURL ?? AppConfig.baseURL()
        if let session {
            self.session = session
        } else {
            let cfg = URLSessionConfiguration.ephemeral
            cfg.timeoutIntervalForRequest = 30
            cfg.timeoutIntervalForResource = 60
            self.session = URLSession(configuration: cfg)
        }
    }

    public func calculateBMI(request: BMIRequest) async throws -> BMIResponse {
        let url = baseURL.appendingPathComponent("api/v1/bmi/calculate")

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.setValue("application/json", forHTTPHeaderField: "Accept")

        do {
            let encoder = JSONEncoder()
            encoder.keyEncodingStrategy = .convertToSnakeCase
            urlRequest.httpBody = try encoder.encode(request)
        } catch {
            throw BMIServiceError.encoding(error.localizedDescription)
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: urlRequest)
        } catch {
            throw BMIServiceError.transport((error as NSError).localizedDescription)
        }

        guard let http = response as? HTTPURLResponse else {
            throw BMIServiceError.transport("Invalid response type")
        }

        if http.statusCode == 422 {
            if let parsed = try? JSONDecoder().decode(ValidationErrorResponse.self, from: data) {
                throw BMIServiceError.validation(parsed.detail.map { err in
                    BMIServiceError.ValidationError(
                        type: err.type,
                        loc: err.loc,
                        msg: err.msg,
                        input: nil // Legacy doesn't decode input
                    )
                })
            }
        }

        guard (200..<300).contains(http.statusCode) else {
            let msg = String(data: data.prefix(4096), encoding: .utf8)
            throw BMIServiceError.http(http.statusCode, msg)
        }

        do {
            return try JSONDecoder().decode(BMIResponse.self, from: data)
        } catch {
            throw BMIServiceError.decoding(error.localizedDescription)
        }
    }
}

// Note: ValidationErrorResponse is imported from Networking/ErrorsDTO.swift

/// Minimal AnyCodable for validation payloads.
/// (Keeps tests deterministic; not intended for general use.)
///
/// NOTE:
/// AnyCodable is @unchecked Sendable by design.
/// Used only for decoding backend validation payloads in tests.
/// Must not cross actor boundaries with non-primitive values.
public struct AnyCodable: Codable, Equatable {
    public let value: Any

    public init(_ value: Any) { self.value = value }

    public init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let v = try? c.decode(Bool.self) { value = v; return }
        if let v = try? c.decode(Int.self) { value = v; return }
        if let v = try? c.decode(Double.self) { value = v; return }
        if let v = try? c.decode(String.self) { value = v; return }
        value = "unsupported"
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch value {
        case let v as Bool: try c.encode(v)
        case let v as Int: try c.encode(v)
        case let v as Double: try c.encode(v)
        case let v as String: try c.encode(v)
        default: try c.encode("unsupported")
        }
    }

    public static func == (lhs: AnyCodable, rhs: AnyCodable) -> Bool {
        // Type-safe equality: only compare values of the same type
        switch (lhs.value, rhs.value) {
        case (let l as Bool, let r as Bool): return l == r
        case (let l as Int, let r as Int): return l == r
        case (let l as Double, let r as Double): return l == r
        case (let l as String, let r as String): return l == r
        default: return false
        }
    }
}

// Explicitly mark as unchecked Sendable (used only for test payloads)
extension AnyCodable: @unchecked Sendable {}
