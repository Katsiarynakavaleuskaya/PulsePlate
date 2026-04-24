import XCTest
@testable import PulsePlate

final class CBTInsightServiceTests: XCTestCase {

    func test_fetchInsight_sendsCanonicalPathBodyAndHeader() async throws {
        let response = CBTInsightResponseDTO(
            insight: "Try reframing the thought.",
            ragUsed: true,
            sources: [
                CBTInsightSourceDTO(
                    chunkId: "chunk-1",
                    file: "docs/cbt/cognitive_restructuring.md",
                    preview: "Reframing helps challenge distorted thoughts.",
                    score: 0.92
                )
            ],
            confidence: 0.92,
            uncertainty: 0.08,
            warnings: [],
            mode: "auto-safe",
            quotaState: "consumed"
        )
        let api = CapturingInsightAPIClient(result: response)
        let service = DefaultCBTInsightService(apiClient: api)

        let result = try await service.fetchInsight(
            query: "How do I stop all-or-nothing thinking?",
            apiKey: "pp-placeholder" // pragma: allowlist secret -- test API key sentinel / тестовый маркер ключа
        )

        XCTAssertEqual(result.insight, "Try reframing the thought.")
        XCTAssertEqual(api.lastPath, "/api/v1/pro/cbt/insight")
        XCTAssertEqual(
            api.lastHeaders?["X-API-Key"],
            "pp-placeholder" // pragma: allowlist secret -- test API key sentinel / тестовый маркер ключа
        )
        XCTAssertEqual(api.lastBody?.query, "How do I stop all-or-nothing thinking?")
    }
}

private final class CapturingInsightAPIClient: APIClientProtocol, @unchecked Sendable {
    var lastPath: String?
    var lastHeaders: [String: String]?
    var lastBody: CBTInsightRequestDTO?
    private let result: CBTInsightResponseDTO

    init(result: CBTInsightResponseDTO) {
        self.result = result
    }

    func postRaw<Response: Decodable>(
        path: String,
        body: Data,
        headers: [String: String]
    ) async throws -> Response {
        fatalError("Not used in this test")
    }

    func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String]
    ) async throws -> Response {
        lastPath = path
        lastHeaders = headers
        lastBody = body as? CBTInsightRequestDTO

        if Response.self == CBTInsightResponseDTO.self {
            // swiftlint:disable:next force_cast
            return result as! Response
        }
        fatalError("Unexpected response type: \(Response.self)")
    }

    func get<Response: Decodable>(
        path: String,
        headers: [String: String]
    ) async throws -> Response {
        fatalError("Not used in this test")
    }
}
