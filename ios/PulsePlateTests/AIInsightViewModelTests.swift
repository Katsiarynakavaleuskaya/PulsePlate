import XCTest
@testable import PulsePlate

final class AIInsightViewModelTests: XCTestCase {

    func test_submit_withoutApiKey_setsFailed_andDoesNotCallService() async {
        let service = CapturingCBTInsightService(result: .failure(.unknown("unused")))
        let vm = await MainActor.run {
            let viewModel = AIInsightViewModel(service: service, apiKeyProvider: { nil })
            viewModel.query = "Help me challenge a negative thought"
            return viewModel
        }

        await MainActor.run {
            vm.submit()
        }

        let state = await awaitEventuallyState(vm)
        let callCount = await service.callCount
        XCTAssertEqual(callCount, 0)

        guard case .failed(let message) = state else {
            return XCTFail("Expected failed state, got: \(state)")
        }
        XCTAssertEqual(message, NSLocalizedString("ai_insight.error.missing_key", comment: ""))
    }

    func test_submit_success_setsLoadedResponse() async {
        let response = CBTInsightResponseDTO(
            insight: "Notice the thought, then test the evidence for it.",
            ragUsed: true,
            sources: [
                CBTInsightSourceDTO(
                    chunkId: "chunk-1",
                    file: "docs/cbt/thought_records.md",
                    preview: "Thought records can slow down automatic thoughts.",
                    score: 0.88
                )
            ],
            confidence: 0.88,
            uncertainty: 0.12,
            warnings: ["source_content_redacted"],
            mode: "auto-safe",
            quotaState: "consumed"
        )
        let service = CapturingCBTInsightService(result: .success(response))
        let vm = await MainActor.run {
            let viewModel = AIInsightViewModel(
                service: service,
                apiKeyProvider: { "pp-placeholder" } // pragma: allowlist secret -- test API key sentinel / тестовый маркер ключа
            )
            viewModel.query = "How can I respond to self-criticism after overeating?"
            return viewModel
        }

        await MainActor.run {
            vm.submit()
        }

        let state = await awaitEventuallyState(vm)
        let callCount = await service.callCount
        let query = await service.lastQuery
        let apiKey = await service.lastAPIKey

        XCTAssertEqual(callCount, 1)
        XCTAssertEqual(query, "How can I respond to self-criticism after overeating?")
        XCTAssertEqual(
            apiKey,
            "pp-placeholder" // pragma: allowlist secret -- test API key sentinel / тестовый маркер ключа
        )

        guard case .loaded(let loaded) = state else {
            return XCTFail("Expected loaded state, got: \(state)")
        }
        XCTAssertEqual(loaded, response)
    }

    func test_submit_maps429ToUserFacingQuotaMessage() async {
        let service = CapturingCBTInsightService(
            result: .failure(.api(statusCode: 429, message: "quota_exceeded"))
        )
        let vm = await MainActor.run {
            let viewModel = AIInsightViewModel(
                service: service,
                apiKeyProvider: { "pp-placeholder" } // pragma: allowlist secret -- test API key sentinel / тестовый маркер ключа
            )
            viewModel.query = "I need help staying consistent"
            return viewModel
        }

        await MainActor.run {
            vm.submit()
        }

        let state = await awaitEventuallyState(vm)
        guard case .failed(let message) = state else {
            return XCTFail("Expected failed state, got: \(state)")
        }
        XCTAssertEqual(message, NSLocalizedString("ai_insight.error.quota_exceeded", comment: ""))
    }

    private func awaitEventuallyState(_ vm: AIInsightViewModel) async -> AIInsightState {
        for _ in 0..<200 {
            let state = await MainActor.run { vm.state }
            if case .idle = state {
                await Task.yield()
                continue
            }
            if case .loading = state {
                await Task.yield()
                continue
            }
            return state
        }

        try? await Task.sleep(for: .milliseconds(10))
        return await MainActor.run { vm.state }
    }
}

private actor CapturingCBTInsightService: CBTInsightServicing {
    private let result: Result<CBTInsightResponseDTO, APIError>
    private(set) var callCount: Int = 0
    private(set) var lastQuery: String?
    private(set) var lastAPIKey: String?

    init(result: Result<CBTInsightResponseDTO, APIError>) {
        self.result = result
    }

    func fetchInsight(query: String, apiKey: String) async throws -> CBTInsightResponseDTO {
        callCount += 1
        lastQuery = query
        lastAPIKey = apiKey

        switch result {
        case .success(let response):
            return response
        case .failure(let error):
            throw error
        }
    }
}
