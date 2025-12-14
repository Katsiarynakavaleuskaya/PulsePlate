import Foundation
import Observation

/// Observable ViewModel for Weekly Plan Reader screen
/// Manages loading state, day navigation, and UI interactions
@Observable
public final class WeeklyPlanReaderViewModel {
    // MARK: - Published State

    public private(set) var state: WeeklyPlanState = .idle
    public var currentDayIndex: Int = 0
    public var isCoverageExpanded: Bool = false

    // MARK: - Dependencies

    private let service: WeeklyPlanServicing
    private let endpointPath: String
    private let apiKey: String?

    // MARK: - Private State

    private var lastTargets: [String: Any]?
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
    public func load(targets: [String: Any]? = nil) {
        // Cancel previous task to prevent parallel requests
        loadTask?.cancel()

        loadTask = Task { [weak self] in
            guard let self else { return }
            await self._load(targets: targets)
        }
    }

    /// Internal load implementation (runs off main thread for network)
    private func _load(targets: [String: Any]? = nil) async {
        // Store targets for retry
        await MainActor.run { lastTargets = targets }

        await MainActor.run { state = .loading }

        do {
            // Prepare request body
            let body = try JSONSerialization.data(withJSONObject: targets ?? [:])
            let request = WeeklyPlanRequest(
                endpointPath: endpointPath,
                body: body,
                apiKey: apiKey
            )

            // Fetch from service (off main thread)
            let dto = try await service.fetchWeeklyPlan(request: request)

            // Adapt to VM (off main thread)
            let planVM = WeeklyPlanAdapter.toVM(dto: dto)

            // Update state on main thread
            await MainActor.run {
                if planVM.isEmpty {
                    state = .empty
                } else {
                    // Clamp current day index to valid range
                    currentDayIndex = min(currentDayIndex, max(0, planVM.days.count - 1))
                    state = .loaded(planVM)
                }
            }
        } catch {
            await MainActor.run { state = .failed(error.localizedDescription) }
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

    /// Toggle coverage section expansion
    public func toggleCoverage() {
        isCoverageExpanded.toggle()
    }

    /// Retry loading after error (uses last targets)
    public func retry() {
        loadTask?.cancel()
        loadTask = Task { [weak self] in
            guard let self else { return }
            let targets = await MainActor.run { self.lastTargets }
            await self._load(targets: targets)
        }
    }
}
