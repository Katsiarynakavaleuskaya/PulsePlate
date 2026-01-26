import Foundation
import Observation

/// Reference MVVM implementation for backend-driven features
/// Use this as a template for new screens consuming dynamic API data
///
/// Observable ViewModel for Weekly Plan Reader screen
/// Manages loading state, day navigation, and UI interactions
@MainActor
@Observable
public final class WeeklyPlanReaderViewModel {
    // MARK: - Published State

    public private(set) var state: WeeklyPlanState = .idle
    public private(set) var currentDayIndex: Int = 0
    public var isCoverageExpanded: Bool = false

    // MARK: - Dependencies

    private let service: WeeklyPlanServicing
    private let endpointPath: String
    private let apiKey: String?

    // MARK: - Private State

    private var lastTargets: JSONValue?
    private var loadTask: Task<Void, Never>?

    // MARK: - Initialization

    public init(
        service: WeeklyPlanServicing,
        endpointPath: String = "/api/v1/pro/meal/weekly",
        apiKey: String? = nil
    ) {
        self.service = service
        self.endpointPath = endpointPath
        self.apiKey = apiKey
    }

    // MARK: - Public Actions

    /// Load weekly plan from backend
    /// Cancels any previous in-flight requests to prevent race conditions
    public func load(targets: JSONValue? = nil) {
        // Cancel previous task to prevent parallel requests
        loadTask?.cancel()

        loadTask = Task { [weak self] in
            guard let self else { return }
            await self._load(targets: targets)
        }
    }

    /// Internal load implementation (runs off main thread for network)
    private func _load(targets: JSONValue? = nil) async {
        // Store targets for retry
        lastTargets = targets

        state = .loading

        do {
            // Check for cancellation before starting work
            try Task.checkCancellation()

            // Prepare request body
            let body = try Self.encodeTargetsBody(targets)
            let request = WeeklyPlanRequest(
                endpointPath: endpointPath,
                body: body,
                apiKey: apiKey
            )

            // Fetch from service (off main thread)
            let dto = try await service.fetchWeeklyPlan(request: request)

            // Check for cancellation after network call
            try Task.checkCancellation()

            // Adapt to VM (off main thread)
            let planVM = WeeklyPlanAdapter.toVM(dto: dto)

            // Update state on main thread
            if planVM.isEmpty {
                state = .empty
            } else {
                // Clamp current day index to valid range [0, days.count-1]
                let maxIndex = max(0, planVM.days.count - 1)
                currentDayIndex = max(0, min(currentDayIndex, maxIndex))
                state = .loaded(planVM)
            }
        } catch is CancellationError {
            // Ignore cancellation - don't set failed state
            return
        } catch let error as APIError {
            // Transport contract: 2xx empty body is signaled as `.emptyResponse`.
            if case .emptyResponse = error {
                state = .empty
                return
            }
            state = .failed(error.localizedDescription)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    /// Navigate to next day (wraps around)
    public func nextDay(totalDays: Int) {
        guard totalDays > 0 else { return }
        currentDayIndex = (currentDayIndex + 1) % totalDays
    }

    /// Navigate to previous day (wraps around)
    public func prevDay(totalDays: Int) {
        guard totalDays > 0 else { return }
        currentDayIndex = (currentDayIndex - 1 + totalDays) % totalDays
    }

    /// Set day index with bounds checking (for external navigation)
    public func setDayIndex(_ index: Int, totalDays: Int) {
        guard totalDays > 0 else { return }
        currentDayIndex = max(0, min(index, totalDays - 1))
    }

    /// Toggle coverage section expansion
    public func toggleCoverage() {
        isCoverageExpanded.toggle()
    }

    /// Retry loading after error (uses last targets)
    public func retry() {
        loadTask?.cancel()
        loadTask = Task { [weak self] in
            guard let self else { return }
            await self._load(targets: self.lastTargets)
        }
    }

    // MARK: - Encoding helpers

    /// Encodes targets to JSON request body. Uses JSONValue to stay Sendable (Swift 6 safe).
    private static func encodeTargetsBody(_ targets: JSONValue?) throws -> Data {
        let payload = targets ?? .emptyObject()
        return try payload.encodeSorted()
    }
}
