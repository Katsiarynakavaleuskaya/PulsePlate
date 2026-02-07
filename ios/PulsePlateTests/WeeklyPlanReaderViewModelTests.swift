import XCTest
@testable import PulsePlate

final class WeeklyPlanReaderViewModelTests: XCTestCase {

    func test_load_withoutApiKey_setsFailed_andDoesNotCallService() async {
        let service = CapturingWeeklyPlanService(result: .failure(.unknown("should not be called")))
        let vm = await MainActor.run {
            WeeklyPlanReaderViewModel(service: service, apiKey: nil)
        }

        await MainActor.run {
            vm.load()
        }

        let state = await awaitEventuallyState(vm)
        let callCount = await service.callCount
        XCTAssertEqual(callCount, 0)

        guard case .failed(let message) = state else {
            return XCTFail("Expected failed state, got: \(state)")
        }
        XCTAssertTrue(message.contains("PRO API key not configured"))
    }

    func test_load_maps401_toUserFacingMessage() async {
        let service = CapturingWeeklyPlanService(result: .failure(.api(statusCode: 401, message: "nope")))
        let vm = await MainActor.run {
            WeeklyPlanReaderViewModel(service: service, apiKey: "pp-placeholder") // pragma: allowlist secret
        }

        await MainActor.run {
            vm.load()
        }

        let state = await awaitEventuallyState(vm)
        let callCount = await service.callCount
        XCTAssertEqual(callCount, 1)

        guard case .failed(let message) = state else {
            return XCTFail("Expected failed state, got: \(state)")
        }
        XCTAssertEqual(message, "Unauthorized (HTTP 401). Check your PRO API key.")
    }

    func test_load_maps403_toUserFacingMessage() async {
        let service = CapturingWeeklyPlanService(result: .failure(.api(statusCode: 403, message: "nope")))
        let vm = await MainActor.run {
            WeeklyPlanReaderViewModel(service: service, apiKey: "pp-placeholder") // pragma: allowlist secret
        }

        await MainActor.run {
            vm.load()
        }

        let state = await awaitEventuallyState(vm)
        let callCount = await service.callCount
        XCTAssertEqual(callCount, 1)

        guard case .failed(let message) = state else {
            return XCTFail("Expected failed state, got: \(state)")
        }
        XCTAssertEqual(message, "Forbidden (HTTP 403). Your PRO key may be missing access.")
    }

    // MARK: - Helpers

    private func awaitEventuallyState(_ vm: WeeklyPlanReaderViewModel) async -> WeeklyPlanState {
        // load() runs in an internal Task; we yield + short sleep until it updates state.
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

        // Last attempt with a tiny sleep (keeps tests deterministic enough in CI).
        try? await Task.sleep(for: .milliseconds(10))
        return await MainActor.run { vm.state }
    }
}

// MARK: - Test Double

private actor CapturingWeeklyPlanService: WeeklyPlanServicing {
    private let result: Result<WeeklyPlanDTO, APIError>
    private(set) var callCount: Int = 0

    init(result: Result<WeeklyPlanDTO, APIError>) {
        self.result = result
    }

    func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO {
        callCount += 1
        switch result {
        case .success(let dto):
            return dto
        case .failure(let error):
            throw error
        }
    }
}
