import Foundation

public protocol BMIServicing: Sendable {
    func calculateBMI(request: BMIRequest) async throws -> BMIResponse
}

public enum BMIServiceError: Error, LocalizedError, Sendable, Equatable {
    case http(Int, String?)
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
        case .decoding(let msg):
            return "Decode error: \(msg)"
        case .transport(let msg):
            return "Network error: \(msg)"
        case .validation(let errors):
            return errors.map(\.msg).joined(separator: "\n")
        }
    }
}

public final class DefaultBMIService: BMIServicing, @unchecked Sendable {
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
            urlRequest.httpBody = try JSONEncoder().encode(request)
        } catch {
            throw BMIServiceError.decoding(error.localizedDescription)
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
                throw BMIServiceError.validation(parsed.detail)
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

private struct ValidationErrorResponse: Codable {
    let detail: [BMIServiceError.ValidationError]
}

/// Minimal AnyCodable for validation payloads.
/// (Keeps tests deterministic; not intended for general use.)
public struct AnyCodable: Codable, Sendable, Equatable {
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
        String(describing: lhs.value) == String(describing: rhs.value)
    }
}
