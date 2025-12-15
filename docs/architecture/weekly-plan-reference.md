# WeeklyPlan Reference Architecture (MVVM + Adapter)

This document describes WeeklyPlan Reader as a reference implementation for:
- MVVM state management (SwiftUI + @Observable)
- Adapter pattern for resilient API-to-VM normalization
- Strict concurrency safety (Swift 6 readiness)
- Defensive parsing with contract-drift tolerance

## High-level flow

1. View triggers `WeeklyPlanReaderViewModel.load(targets:)`
2. ViewModel builds `WeeklyPlanRequest` (endpointPath + body + apiKey)
3. Service fetches and decodes DTO (`WeeklyPlanDTO`)
4. Adapter normalizes DTO → VM (`WeeklyPlanVM`) with:
   - Safe defaults
   - Clamping (percentages, indices)
   - Key normalization for coverage
5. ViewModel publishes `WeeklyPlanState` to the UI

## Layers and responsibilities

### View (SwiftUI)

```swift
struct WeeklyPlanReaderView: View {
    @State private var vm: WeeklyPlanReaderViewModel

    init(vm: WeeklyPlanReaderViewModel) {
        _vm = State(initialValue: vm)
    }
}
```

**Responsibilities:**
- Renders based on `WeeklyPlanState`
- Calls ViewModel actions (load/retry/navigation)
- No decoding, no normalization, no business rules

### ViewModel (@Observable, @MainActor)

**Responsibilities:**
- Owns UI state: `state`, `currentDayIndex`, `isCoverageExpanded`
- Controls lifecycle: cancellation, retry, safe navigation
- Never parses raw JSON directly; only handles request encoding and orchestration

**Concurrency pattern:**
```swift
@MainActor
@Observable
public final class WeeklyPlanReaderViewModel {
    public private(set) var state: WeeklyPlanState = .idle
    private var loadTask: Task<Void, Never>?

    public func load(targets: JSONValue? = nil) {
        loadTask?.cancel()
        loadTask = Task { [weak self] in
            guard let self else { return }
            await self._load(targets: targets)
        }
    }
}
```

### Service (WeeklyPlanServicing)

**Responsibilities:**
- Constructs network request
- Decodes response into `WeeklyPlanDTO`
- Does not mutate UI state

### Adapter (WeeklyPlanAdapter)

**Responsibilities:**
- Converts DTO to domain VM (`WeeklyPlanVM`)
- Centralizes domain normalization rules:
  - Clamping (coverage %, portions, indices)
  - Stable sorting (days by index, meals by rank)
  - Key prettification for UI labels
- Tolerates missing/partial DTO fields using safe defaults

**Swift patterns used:**
```swift
// Example normalization patterns (Swift)
let clamped = min(300, max(0, value))           // Coverage percentage
let portions = max(1, Int(value))                // Positive portions
let safeIndex = min(max(index, 0), maxValidIndex) // Bounds checking
```

> **Note**: Frontend has a separate TypeScript adapter (`adapter.ts`) with additional hardening concerns (prototype pollution, unsafe keys). Keep those documented in frontend-specific docs.

## Concurrency rules (Swift 6)

- **UI state mutations** are `@MainActor` isolated (ViewModel is `@MainActor`)
- **In-flight tasks** are cancelled on reload/retry to prevent race conditions
- **Networking suspends** the actor; state updates resume safely on MainActor after `await`
- **JSONValue** ensures Sendable compliance across Task boundaries
- If heavy adaptation becomes expensive, consider moving DTO→VM conversion to a nonisolated helper or `Task.detached` (measure first)

## Reference code pointers

- **ViewModel**: `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift`
- **Service**: `ios/PulsePlate/Services/WeeklyPlanService.swift`
- **Adapter**: `ios/PulsePlate/Models/WeeklyPlan/WeeklyPlanAdapter.swift`
- **JSON dynamic types**: `ios/PulsePlate/Utilities/JSON/JSONValue.swift`
- **View**: `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`
- **Tests**: `ios/PulsePlateTests/WeeklyPlanReaderViewSnapshotTests.swift`
- **Mocks**: `ios/PulsePlateTests/Mocks/MockWeeklyPlanService.swift`

## Best practices demonstrated

1. **Defensive parsing**: All adapter functions use safe defaults and type guards
2. **Bounds checking**: Day indices, portions, percentages are clamped
3. **Cancellation handling**: Tasks check `Task.isCancelled` before state updates
4. **Accessibility**: Reduce motion/transparency respected in UI components
5. **Logging**: OSLog.Logger with privacy annotations for debugging
6. **State machine**: Clear `.idle → .loading → .loaded/.empty/.failed` flow
7. **Reference template**: Architecture can be copied for other backend-driven screens

## Testing strategy

- **Unit tests**: Adapter normalization with malformed inputs
- **Integration tests**: Service + Adapter with mock network responses
- **UI tests**: State transitions (loading → loaded, retry after error)
- **Snapshot tests**: Visual regression for each state (see `ios/PulsePlateTests/WeeklyPlanReaderViewSnapshotTests.swift`)

**Mock infrastructure**:
- `ios/PulsePlateTests/Mocks/MockWeeklyPlanService.swift` - Predefined states (loaded/empty/error)
- Factory methods: `.previewLoaded()`, `.previewEmpty()`, `.previewError()`

## Future enhancements

- Add more snapshot test coverage for edge states (partial data, API drift scenarios)
- If profiling shows DTO→VM conversion is expensive, extract to nonisolated helper
- Document migration path from other legacy MVVM implementations
- Add performance benchmarks for large weekly plans (7+ days)
