import Foundation

public protocol WeeklyPlanServicing: Sendable {
    func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO
}

public struct WeeklyPlanRequest: Sendable {
    public let endpointPath: String          // e.g. "/api/v1/pro/meal/weekly"
    public let body: Data                   // JSON payload (targets/profile/etc.)
    public let apiKey: String?              // optional

    public init(endpointPath: String, body: Data, apiKey: String? = nil) {
        self.endpointPath = endpointPath
        self.body = body
        self.apiKey = apiKey
    }
}

public enum WeeklyPlanServiceError: Error, LocalizedError, Sendable {
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

public final class DefaultWeeklyPlanService: WeeklyPlanServicing, @unchecked Sendable {
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

    public func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO {
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

        let (data, response) = try await session.data(for: urlRequest)

        guard let http = response as? HTTPURLResponse else {
            throw WeeklyPlanServiceError.transport("Invalid response type")
        }

        guard (200..<300).contains(http.statusCode) else {
            // Limit error message to 4KB to avoid excessive memory usage
            let msg = String(data: data.prefix(4096), encoding: .utf8)
            throw WeeklyPlanServiceError.http(http.statusCode, msg)
        }

        // Handle 204 No Content or empty response
        if http.statusCode == 204 || data.isEmpty {
            // Return empty plan as empty JSON object
            let emptyData = Data("{}".utf8)
            return try JSONDecoder().decode(WeeklyPlanDTO.self, from: emptyData)
        }

        do {
            return try JSONDecoder().decode(WeeklyPlanDTO.self, from: data)
        } catch {
            throw WeeklyPlanServiceError.decoding(error.localizedDescription)
        }
    }
}
