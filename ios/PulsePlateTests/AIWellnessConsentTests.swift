import XCTest
@testable import PulsePlate

// MARK: - AI Wellness Consent Tests

final class AIWellnessConsentTests: XCTestCase {

    // MARK: - Consent Store Tests

    func test_consentStore_defaultIsFalse() {
        let store = AIWellnessConsentStore(userDefaults: ephemeralDefaults())
        XCTAssertFalse(store.hasAccepted(), "Consent must default to false")
    }

    func test_consentStore_markAcceptedPersistsTrue() {
        let defaults = ephemeralDefaults()
        let store = AIWellnessConsentStore(userDefaults: defaults)
        store.markAccepted()
        XCTAssertTrue(store.hasAccepted(), "Consent must be true after markAccepted()")
        // Verify persistence via a second instance
        let store2 = AIWellnessConsentStore(userDefaults: defaults)
        XCTAssertTrue(store2.hasAccepted(), "Consent must persist across instances")
    }

    // MARK: - ViewModel Consent Gate Tests

    func test_submit_withoutConsent_setsConsentRequired() async {
        let service = StubInsightService(result: .success(makeResponse()))
        let store = AIWellnessConsentStore(userDefaults: ephemeralDefaults())

        let vm = await MainActor.run {
            let viewModel = AIInsightViewModel(
                service: service,
                apiKeyProvider: { "test-key" },
                consentProvider: store
            )
            viewModel.query = "test question"
            return viewModel
        }

        await MainActor.run { vm.submit() }
        let state = await awaitState(vm)

        guard case .consentRequired = state else {
            return XCTFail("Expected .consentRequired, got: \(state)")
        }

        let callCount = await service.callCount
        XCTAssertEqual(callCount, 0, "Service must not be called without consent")
    }

    func test_acceptConsent_marksConsentAndSubmits() async {
        let service = StubInsightService(result: .success(makeResponse()))
        let defaults = ephemeralDefaults()
        let store = AIWellnessConsentStore(userDefaults: defaults)

        let vm = await MainActor.run {
            let viewModel = AIInsightViewModel(
                service: service,
                apiKeyProvider: { "test-key" },
                consentProvider: store
            )
            viewModel.query = "test question"
            return viewModel
        }

        await MainActor.run { vm.acceptConsent() }
        let state = await awaitState(vm)

        XCTAssertTrue(store.hasAccepted(), "Consent must be persisted after acceptConsent()")

        guard case .loaded = state else {
            return XCTFail("Expected .loaded after acceptConsent(), got: \(state)")
        }

        let callCount = await service.callCount
        XCTAssertEqual(callCount, 1, "Service must be called once after consent")
    }

    func test_declineConsent_returnsToIdle() async {
        let service = StubInsightService(result: .success(makeResponse()))
        let store = AIWellnessConsentStore(userDefaults: ephemeralDefaults())

        let vm = await MainActor.run {
            let viewModel = AIInsightViewModel(
                service: service,
                apiKeyProvider: { "test-key" },
                consentProvider: store
            )
            viewModel.query = "test question"
            return viewModel
        }

        // First submit triggers consentRequired
        await MainActor.run { vm.submit() }
        // Then decline
        await MainActor.run { vm.declineConsent() }

        let state = await MainActor.run { vm.state }
        guard case .idle = state else {
            return XCTFail("Expected .idle after declineConsent(), got: \(state)")
        }

        XCTAssertFalse(store.hasAccepted(), "Consent must not be persisted after decline")
    }

    func test_submit_afterConsentAccepted_proceedsNormally() async {
        let service = StubInsightService(result: .success(makeResponse()))
        let defaults = ephemeralDefaults()
        let store = AIWellnessConsentStore(userDefaults: defaults)
        store.markAccepted()

        let vm = await MainActor.run {
            let viewModel = AIInsightViewModel(
                service: service,
                apiKeyProvider: { "test-key" },
                consentProvider: store
            )
            viewModel.query = "test question"
            return viewModel
        }

        await MainActor.run { vm.submit() }
        let state = await awaitState(vm)

        guard case .loaded = state else {
            return XCTFail("Expected .loaded when consent already accepted, got: \(state)")
        }
    }

    // MARK: - Helpers

    private func ephemeralDefaults() -> UserDefaults {
        UserDefaults(suiteName: UUID().uuidString)!
    }

    private func makeResponse() -> CBTInsightResponseDTO {
        CBTInsightResponseDTO(
            insight: "Test insight",
            confidence: 0.9,
            uncertainty: 0.1,
            ragUsed: false,
            mode: "auto_safe",
            quotaState: "consumed",
            warnings: [],
            sources: []
        )
    }

    private func awaitState(_ vm: AIInsightViewModel) async -> AIInsightState {
        for _ in 0..<200 {
            let state = await MainActor.run { vm.state }
            if case .idle = state { await Task.yield(); continue }
            if case .loading = state { await Task.yield(); continue }
            return state
        }
        try? await Task.sleep(for: .milliseconds(10))
        return await MainActor.run { vm.state }
    }
}

// MARK: - Test Mock

private actor StubInsightService: CBTInsightServicing {
    private let result: Result<CBTInsightResponseDTO, APIError>
    private(set) var callCount: Int = 0

    init(result: Result<CBTInsightResponseDTO, APIError>) {
        self.result = result
    }

    func fetchInsight(query: String, apiKey: String) async throws -> CBTInsightResponseDTO {
        callCount += 1
        switch result {
        case .success(let response): return response
        case .failure(let error): throw error
        }
    }
}
