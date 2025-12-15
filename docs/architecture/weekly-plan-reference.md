# WeeklyPlan Reader: Reference Architecture

> **Reference implementation** for backend-driven iOS features using MVVM + Adapter pattern.

This document explains the architectural choices in the `WeeklyPlanReader` feature and serves as a template for implementing similar screens that consume dynamic backend data.

---

## Overview

The WeeklyPlan Reader is a **read-only meal plan viewer** that:
- Fetches dynamic JSON from backend (`/api/v1/pro/meal/weekly`)
- Adapts loosely-typed DTO into strictly-typed ViewModels
- Renders 7-day meal plans with nutritional coverage
- Handles loading/empty/error states gracefully
- Maintains UI stability through deterministic sorting

**Key Philosophy:** Defensive, resilient, testable.

---

## Architecture Pattern: MVVM + Adapter

```
┌─────────────────────────────────────────────────────────┐
│  WeeklyPlanReaderView (SwiftUI)                         │
│  • State-based rendering                                │
│  • Day navigation UI                                    │
└──────────────────┬──────────────────────────────────────┘
                   │ observes @Observable
                   ▼
┌─────────────────────────────────────────────────────────┐
│  WeeklyPlanReaderViewModel (@MainActor)                 │
│  • Manages UI state (loading/loaded/failed/empty)       │
│  • Handles user actions (load/retry/navigate)           │
│  • Cancellable task management                          │
└──────────────────┬──────────────────────────────────────┘
                   │ calls
                   ▼
┌─────────────────────────────────────────────────────────┐
│  WeeklyPlanService (protocol-based)                     │
│  • Network layer (URLSession + async/await)             │
│  • Returns raw DTO (WeeklyPlanDTO)                      │
└──────────────────┬──────────────────────────────────────┘
                   │ returns JSONValue-based DTO
                   ▼
┌─────────────────────────────────────────────────────────┐
│  WeeklyPlanAdapter (pure functions)                     │
│  • DTO → ViewModel transformation                       │
│  • Defensive parsing with safe defaults                 │
│  • Key normalization ("protein_g" → "Protein")          │
│  • Deterministic sorting (days, meals, coverage)        │
└──────────────────┬──────────────────────────────────────┘
                   │ returns
                   ▼
┌─────────────────────────────────────────────────────────┐
│  WeeklyPlanVM (strictly-typed ViewModels)               │
│  • DayPlanVM, MealSectionVM, CoverageItemVM             │
│  • UI-ready data (no optionals where guaranteed)        │
└─────────────────────────────────────────────────────────┘
```

---

## Layer Responsibilities

### View (WeeklyPlanReaderView)

**Location:** `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`

**Responsibilities:**
- Render UI based on ViewModel state
- Handle user interactions (button taps, swipes)
- Navigate between days
- Display loading/empty/error states

**SwiftUI patterns used:**
- `@State` for ViewModel ownership
- `@Bindable` for two-way bindings (e.g., `isCoverageExpanded`)
- `.task` modifier for lifecycle-aware loading
- State-based `@ViewBuilder` content switching

**Example:**
```swift
@ViewBuilder
private var content: some View {
    switch vm.state {
    case .idle:
        EmptyPlanView { vm.load() }
    case .loading:
        WeeklyPlanSkeletonView()
    case .loaded(let plan):
        LoadedPlanView(plan: plan, vm: vm)
    case .failed(let message):
        ErrorPlanView(message: message) { vm.retry() }
    case .empty:
        EmptyPlanView { vm.load() }
    }
}
```

---

### ViewModel (WeeklyPlanReaderViewModel)

**Location:** `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift`

**Responsibilities:**
- Manage UI state (`.idle`, `.loading`, `.loaded`, `.failed`, `.empty`)
- Coordinate service calls and adapter transformations
- Handle task cancellation to prevent race conditions
- Provide user actions (load, retry, navigate days)
- Encode request bodies (targets → JSON)

**Swift concurrency patterns:**
- `@MainActor` isolation for thread-safe UI updates
- `Task` cancellation on reload/retry
- Networking suspends the actor; state updates resume after `await`
- `JSONValue` ensures Sendable compliance

**Example:**
```swift
@MainActor
@Observable
public final class WeeklyPlanReaderViewModel {
    public private(set) var state: WeeklyPlanState = .idle
    private var loadTask: Task<Void, Never>?

    public func load(targets: JSONValue? = nil) {
        loadTask?.cancel()  // Prevent parallel requests
        loadTask = Task {
            await _load(targets: targets)
        }
    }
}
```

---

### Service (WeeklyPlanService)

**Location:** `ios/PulsePlate/Services/WeeklyPlanService.swift`

**Responsibilities:**
- Protocol-based abstraction (`WeeklyPlanServicing`)
- POST request to backend with JSON body
- Error handling (network, HTTP, decoding)
- Return raw DTO (`WeeklyPlanDTO`)

**Protocol enables:**
- Easy mocking for tests/previews
- Dependency injection
- Testable ViewModels without network calls

**Example:**
```swift
protocol WeeklyPlanServicing: Sendable {
    func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO
}
```

---

### Adapter (WeeklyPlanAdapter)

**Location:** `ios/PulsePlate/Models/WeeklyPlan/WeeklyPlanAdapter.swift`

**Responsibilities:**
- Convert DTO to domain ViewModels (`WeeklyPlanVM`)
- Centralize data normalization:
  - Clamping (coverage %, portions, indices)
  - Stable sorting (days by index, meals by type rank)
  - Key prettification for UI labels
- Tolerate missing/partial DTO fields with safe defaults

**Swift patterns used:**
```swift
// Clamping percentages
let clamped = min(300, max(0, value))

// Safe optional chaining
let kcal = mealVal["kcal"].intRounded
        ?? mealVal["totals"]["kcal"].intRounded

// Deterministic sorting
sections.sorted { $0.mealType.sortRank < $1.mealType.sortRank }
```

**Why separate from ViewModel?**
- ViewModel stays focused on UI state management
- Adapter logic is pure (testable without @MainActor)
- Reusable across different UI contexts

---

## Concurrency Rules (Swift 6)

### MainActor Isolation
- **UI state mutations** are `@MainActor` isolated
- **ViewModel class** is `@MainActor` to prevent data races
- **In-flight tasks** are cancelled on reload/retry

### Networking and Suspension
- **Networking suspends** the actor (await service call)
- **State updates** resume on MainActor after await
- **JSONValue** ensures Sendable compliance across actor boundaries

### Performance Considerations
- Adapter work runs on **calling actor context** (MainActor when called from ViewModel)
- If DTO→VM conversion becomes expensive, use `nonisolated` helpers or `Task.detached`
- **Measure first** before optimizing (current approach is simple and safe)

---

## Key Design Decisions

### 1. JSONValue for Dynamic JSON
**Problem:** Backend contract may change; `[String: Any]` is not Sendable
**Solution:** `JSONValue` enum (Codable + Sendable)

**Benefits:**
- Swift 6 safe (no sendability warnings)
- Type-safe pattern matching
- Graceful degradation on missing keys

### 2. Defensive Parsing in Adapter
**Problem:** Backend may return partial/malformed data
**Solution:** Safe defaults + clamping + optional chaining

**Example:**
```swift
let title = dayVal["title"].stringValue
         ?? dayVal["day_name"].stringValue
         ?? "Day \(idx + 1)"
```

### 3. Deterministic Sorting
**Problem:** JSON object order is undefined; UI jitter on reload
**Solution:** Explicit sorting by index/rank

**Stable order:**
- Days: `0 → 6` (index-based)
- Meals: `breakfast → lunch → dinner → snacks → other` (rank-based)
- Coverage: deficits first, then overage (sorted by %)

### 4. Protocol-Based Service
**Problem:** Hard to test ViewModel without network
**Solution:** `WeeklyPlanServicing` protocol

**Enables:**
- `MockWeeklyPlanService` for previews/tests
- Snapshot testing with deterministic data
- Unit testing without URLSession

---

## File Structure

```
ios/PulsePlate/
├── Models/WeeklyPlan/
│   ├── WeeklyPlanDTO.swift              # Raw backend response
│   ├── WeeklyPlanViewModel.swift        # Strictly-typed VMs
│   └── WeeklyPlanAdapter.swift          # DTO→VM transformation
├── ViewModels/
│   └── WeeklyPlanReaderViewModel.swift  # UI state + actions
├── Services/
│   └── WeeklyPlanService.swift          # Network layer
├── Views/WeeklyPlan/
│   ├── WeeklyPlanReaderView.swift       # Main screen
│   ├── Components/
│   │   ├── DayNavigatorView.swift
│   │   ├── MealSectionView.swift
│   │   └── WeeklyCoverageView.swift
│   └── States/
│       ├── EmptyPlanView.swift
│       └── ErrorPlanView.swift
└── Utilities/JSON/
    ├── JSONValue.swift                  # Dynamic JSON wrapper
    └── JSONValue+Helpers.swift          # Encoding/subscript helpers
```

---

## Testing Strategy

### Unit Tests
**Location:** `ios/PulsePlateTests/`

**Coverage:**
- `WeeklyPlanAdapterSmokeTests.swift` - Adapter normalization logic
- `WeeklyPlanServiceTransportTests.swift` - Network encoding/decoding
- `WeeklyPlanMealTypeTests.swift` - Meal type sorting

### Snapshot Tests (Recommended)
**Location:** `ios/PulsePlateTests/WeeklyPlanReaderViewSnapshotTests.swift`

**Test states:**
- Loaded (full plan)
- Empty (no days)
- Error (network failure)
- Loading (skeleton)

**Tools:**
- Swift Testing framework (`@Test`, `@Suite`, `#expect`)
- `MockWeeklyPlanService` for deterministic data

---

## Future Enhancements

1. **Snapshot Test Coverage**
   - Add visual regression tests for all UI states
   - Test day navigation, coverage expansion

2. **Performance Profiling**
   - Measure DTO→VM conversion time for large plans (14+ days)
   - Consider `nonisolated` adapter helpers if needed

3. **Template Extraction**
   - Create reusable MVVM template from WeeklyPlan structure
   - Document "copy-paste-adapt" workflow for new features

4. **Benchmarks**
   - Measure rendering performance for complex plans
   - Optimize ScrollView if needed (lazy loading)

---

## Usage as Template

When implementing a **new backend-driven screen**, copy this pattern:

1. **Define DTO** (raw backend response with `JSONValue`)
2. **Create ViewModels** (strictly-typed, UI-ready structs)
3. **Write Adapter** (DTO→VM with defensive parsing)
4. **Implement Service** (protocol + real + mock implementations)
5. **Build ViewModel** (`@MainActor`, `@Observable`, state management)
6. **Create View** (SwiftUI with state-based rendering)
7. **Add Tests** (adapter unit tests + snapshot tests)

**Key Principles:**
- ✅ Protocol-based services (testability)
- ✅ Defensive parsing (resilience)
- ✅ Deterministic sorting (UI stability)
- ✅ Swift 6 safe (Sendable + MainActor)
- ✅ Reference code markers (help future developers)

---

## Related Documentation

- **iOS API Integration:** `docs/IOS_API_INTEGRATION.md`
- **WeeklyPlan Smoke Checklist:** `docs/WeeklyPlanReaderSmokeChecklist.md`
- **Backend API:** `/api/v1/pro/meal/weekly` endpoint docs

---

**Last Updated:** 2025-12-15
**Status:** Reference Implementation ✅
