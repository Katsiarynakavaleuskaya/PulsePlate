import Foundation
import Observation

enum FitChefSupportFlowFailure: Equatable, Sendable {
    case unavailable
    case retryable
    case restartRequired
    case terminal
}

enum FitChefSupportFlowState: Equatable, Sendable {
    case selecting(FitChefSupportNeed?)
    case requesting(FitChefSupportNeed)
    case handoffFailed(FitChefSupportNeed, FitChefSupportFlowFailure)
    case presenting(FitChefSupportHandoffDescriptor)
    case recording(FitChefSupportHandoffDescriptor, FitChefSupportOutcomeAttempt)
    case outcomeFailed(
        FitChefSupportHandoffDescriptor,
        FitChefSupportOutcomeAttempt,
        FitChefSupportFlowFailure
    )
    case completed(
        FitChefSupportHandoffDescriptor,
        FitChefSupportOutcome,
        FitChefSupportOutcomeState
    )
}

@MainActor
@Observable
final class FitChefSupportFlowViewModel {
    private(set) var state: FitChefSupportFlowState = .selecting(nil)

    @ObservationIgnored private let service: FitChefSupportServicing
    @ObservationIgnored private let apiKeyProvider: @Sendable () -> String?
    @ObservationIgnored private let makeClientEventID: @Sendable () -> UUID
    @ObservationIgnored private var operationGeneration: UInt = 0
    @ObservationIgnored private var pinnedAPIKey: String?

    init(
        service: FitChefSupportServicing,
        apiKeyProvider: @escaping @Sendable () -> String?,
        makeClientEventID: @escaping @Sendable () -> UUID
    ) {
        self.service = service
        self.apiKeyProvider = apiKeyProvider
        self.makeClientEventID = makeClientEventID
    }

    func select(_ need: FitChefSupportNeed) {
        guard case .selecting = state else { return }
        transition(to: .selecting(need))
    }

    func clearSelection() {
        guard case .selecting = state else { return }
        transition(to: .selecting(nil))
    }

    func confirm() {
        guard case .selecting(let need?) = state else { return }
        guard
            let providedAPIKey = apiKeyProvider(),
            !providedAPIKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else {
            pinnedAPIKey = nil
            transition(to: .handoffFailed(need, .unavailable))
            return
        }

        let apiKey = providedAPIKey
        pinnedAPIKey = apiKey
        let generation = beginOperation()
        transition(to: .requesting(need))
        Task {
            await performHandoff(for: need, apiKey: apiKey, generation: generation)
        }
    }

    func retryHandoff() {
        guard
            case .handoffFailed(let need, .retryable) = state,
            let apiKey = pinnedAPIKey
        else {
            return
        }

        let generation = beginOperation()
        transition(to: .requesting(need))
        Task {
            await performHandoff(for: need, apiKey: apiKey, generation: generation)
        }
    }

    func acknowledge() {
        recordFirstOutcome(.acknowledged)
    }

    func dismissResult() {
        recordFirstOutcome(.dismissed)
    }

    func retryOutcome() {
        guard
            case .outcomeFailed(let descriptor, let attempt, .retryable) = state,
            let apiKey = pinnedAPIKey
        else {
            return
        }

        let generation = beginOperation()
        transition(to: .recording(descriptor, attempt))
        Task {
            await performOutcome(
                attempt,
                for: descriptor,
                apiKey: apiKey,
                generation: generation
            )
        }
    }

    func cancel() {
        resetLifecycle()
    }

    func startNewLifecycle() {
        resetLifecycle()
    }

    var userFacingMessageKey: String? {
        switch state {
        case .selecting, .presenting:
            return nil
        case .requesting:
            return "fitchef.support_flow.loading"
        case .handoffFailed(_, let failure):
            return failure == .unavailable
                ? "fitchef.support_flow.unavailable"
                : "fitchef.support_flow.handoff_failed"
        case .recording:
            return "fitchef.support_flow.recording"
        case .outcomeFailed(_, _, let failure):
            switch failure {
            case .retryable:
                return "fitchef.support_flow.outcome_retryable"
            case .restartRequired:
                return "fitchef.support_flow.outcome_restart"
            case .terminal, .unavailable:
                return "fitchef.support_flow.outcome_terminal"
            }
        case .completed(_, _, let receiptState):
            return receiptState == .recorded
                ? "fitchef.support_flow.recorded"
                : "fitchef.support_flow.replayed"
        }
    }

    var targetDisplayKey: String? {
        guard let descriptor = descriptorInCurrentState else { return nil }
        switch descriptor.action.targetSurface {
        case .proDailyPlate:
            return "fitchef.support_flow.result.target.daily"
        case .proWeeklyPlan:
            return "fitchef.support_flow.result.target.weekly"
        }
    }

    var canRetryHandoff: Bool {
        guard case .handoffFailed(_, .retryable) = state else { return false }
        return true
    }

    var canRetryOutcome: Bool {
        guard case .outcomeFailed(_, _, .retryable) = state else { return false }
        return true
    }

    var requiresNewLifecycle: Bool {
        switch state {
        case .handoffFailed(_, .restartRequired),
             .outcomeFailed(_, _, .restartRequired):
            return true
        default:
            return false
        }
    }

    private var descriptorInCurrentState: FitChefSupportHandoffDescriptor? {
        switch state {
        case .presenting(let descriptor),
             .recording(let descriptor, _),
             .outcomeFailed(let descriptor, _, _),
             .completed(let descriptor, _, _):
            return descriptor
        case .selecting, .requesting, .handoffFailed:
            return nil
        }
    }

    private func performHandoff(
        for need: FitChefSupportNeed,
        apiKey: String,
        generation: UInt
    ) async {
        do {
            let descriptor = try await service.requestHandoff(for: need, apiKey: apiKey)
            try Task.checkCancellation()
            guard isCurrent(generation) else { return }
            transition(to: .presenting(descriptor))
        } catch is CancellationError {
            return
        } catch {
            guard isCurrent(generation) else { return }
            let failure = handoffFailure(for: error)
            if failure != .retryable {
                pinnedAPIKey = nil
            }
            transition(to: .handoffFailed(need, failure))
        }
    }

    private func handoffFailure(for error: Error) -> FitChefSupportFlowFailure {
        if let contractError = error as? FitChefSupportContractError {
            return contractError == .invalidHandoffDescriptor ? .retryable : .terminal
        }
        guard let apiError = error as? APIError else {
            return .terminal
        }
        switch apiError {
        case .validation, .encodingFailed:
            return .terminal
        case .api(let statusCode, _):
            switch statusCode {
            case 401, 403:
                return .restartRequired
            case 500...599:
                return .retryable
            default:
                return .terminal
            }
        case .emptyResponse, .transport, .decodingFailed, .invalidResponse:
            return .retryable
        case .unknown, .unhandledStatusCode:
            return .terminal
        }
    }

    private func recordFirstOutcome(_ outcome: FitChefSupportOutcome) {
        guard
            case .presenting(let descriptor) = state,
            let apiKey = pinnedAPIKey
        else {
            return
        }

        let attempt = FitChefSupportOutcomeAttempt(
            supportNeed: descriptor.supportNeed,
            outcome: outcome,
            clientEventID: makeClientEventID().uuidString.lowercased()
        )
        let generation = beginOperation()
        transition(to: .recording(descriptor, attempt))
        Task {
            await performOutcome(
                attempt,
                for: descriptor,
                apiKey: apiKey,
                generation: generation
            )
        }
    }

    private func performOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        for descriptor: FitChefSupportHandoffDescriptor,
        apiKey: String,
        generation: UInt
    ) async {
        do {
            let receipt = try await service.recordOutcome(attempt, apiKey: apiKey)
            try Task.checkCancellation()
            guard isCurrent(generation) else { return }
            pinnedAPIKey = nil
            transition(to: .completed(descriptor, attempt.outcome, receipt.state))
        } catch is CancellationError {
            return
        } catch {
            guard isCurrent(generation) else { return }
            let failure = outcomeFailure(for: error)
            if failure != .retryable {
                pinnedAPIKey = nil
            }
            transition(to: .outcomeFailed(descriptor, attempt, failure))
        }
    }

    private func outcomeFailure(for error: Error) -> FitChefSupportFlowFailure {
        if error is FitChefSupportContractError {
            return .retryable
        }
        guard let apiError = error as? APIError else {
            return .retryable
        }
        switch apiError {
        case .validation:
            return .terminal
        case .api(let statusCode, _):
            switch statusCode {
            case 401, 403:
                return .restartRequired
            case 409, 422:
                return .terminal
            case 429, 500...599:
                return .retryable
            default:
                return .terminal
            }
        case .emptyResponse, .transport, .decodingFailed, .invalidResponse,
             .unknown, .unhandledStatusCode:
            return .retryable
        case .encodingFailed:
            return .terminal
        }
    }

    private func beginOperation() -> UInt {
        operationGeneration &+= 1
        return operationGeneration
    }

    private func isCurrent(_ generation: UInt) -> Bool {
        generation == operationGeneration && !Task.isCancelled
    }

    private func resetLifecycle() {
        operationGeneration &+= 1
        pinnedAPIKey = nil
        transition(to: .selecting(nil))
    }

    private func transition(to newState: FitChefSupportFlowState) {
        state = newState
    }

    // Teardown reads no actor-isolated state and must not require an executor hop.
    nonisolated deinit {}

    #if DEBUG
    init(
        previewState: FitChefSupportFlowState,
        service: FitChefSupportServicing
    ) {
        self.service = service
        apiKeyProvider = { nil }
        makeClientEventID = { UUID() }
        state = previewState
    }
    #endif
}
