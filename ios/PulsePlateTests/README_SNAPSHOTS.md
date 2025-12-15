# Snapshot Testing Guide

This directory contains snapshot tests for WeeklyPlan UI components using Swift Testing and SnapshotTesting.

## Overview

Snapshot tests capture the visual state of UI components and compare against reference images to detect unintended visual regressions.

## Dependencies

- **Swift Testing**: Modern testing framework (`import Testing`)
- **SnapshotTesting**: Point-Free snapshot library (SPM: `pointfreeco/swift-snapshot-testing`)

## Running Snapshot Tests

### Initial Setup

1. **Add SnapshotTesting Package** (if not already added):
   ```
   Xcode → File → Add Package Dependencies
   → https://github.com/pointfreeco/swift-snapshot-testing
   ```

2. **Record Baseline Snapshots**:
   - Open `WeeklyPlanReaderViewSnapshotTests.swift`
   - Set `record: true` in `assertSnapshotHosting` helper
   - Run tests once (Cmd+U)
   - Reference images saved to `__Snapshots__/` directory
   - Set `record: false` back

3. **Verify Snapshots**:
   - Run tests normally with `record: false`
   - Tests pass if rendered UI matches reference images
   - Test fails if visual differences detected

### Test Structure

```swift
@Suite("WeeklyPlanReaderView Snapshots")
struct WeeklyPlanReaderViewSnapshotTests {
    @Test("Loaded state renders correctly")
    func loadedStateSnapshot() async throws {
        let vm = WeeklyPlanReaderViewModel(
            service: MockWeeklyPlanService.previewLoaded()
        )
        let view = WeeklyPlanReaderView(vm: vm)

        vm.load()
        try await Task.sleep(for: .milliseconds(500))

        try assertSnapshotHosting(view, named: "loaded")
    }
}
```

## Mock Services

Located in `Mocks/MockWeeklyPlanService.swift`:

```swift
// Successful load with data
MockWeeklyPlanService.previewLoaded()

// Empty response (no meal plans)
MockWeeklyPlanService.previewEmpty()

// Error state
MockWeeklyPlanService.previewError(message: "Network timeout")

// Custom delay for loading state capture
MockWeeklyPlanService(mode: .loaded, delay: .seconds(2))
```

## Covered States

| Test | State | Description |
|------|-------|-------------|
| `loadedStateSnapshot` | `.loaded` | Full meal plan with 2 days |
| `emptyStateSnapshot` | `.empty` | No meal plans available |
| `errorStateSnapshot` | `.failed` | Network/server error |
| `loadingStateSnapshot` | `.loading` | Skeleton loading state |
| `dayNavigationSnapshot` | `.loaded` | Day 2 selected |
| `coverageExpandedSnapshot` | `.loaded` | Coverage section expanded |

## Snapshot Configuration

**Device**: iPhone 13 Pro (390x844)
**Format**: PNG images
**Location**: `__Snapshots__/WeeklyPlanReaderViewSnapshotTests/`

## CI Integration

Snapshots are **deterministic** across machines when using:
- Same iOS simulator version
- Same device size (iPhone 13 Pro)
- Fixed view frames (390x844)

To use in CI:
1. Commit `__Snapshots__/` directory to git
2. Run tests with `record: false` (default)
3. CI fails if snapshots don't match

## Updating Snapshots

When UI changes are intentional:
1. Set `record: true`
2. Run tests to regenerate references
3. Review new snapshots in `__Snapshots__/`
4. Commit updated images
5. Set `record: false`

## Troubleshooting

### Tests fail with "Snapshot mismatch"
- Check if UI changes were intentional
- If yes: re-record snapshots
- If no: investigate unexpected UI changes

### Different results on different machines
- Ensure same iOS simulator version
- Check device size matches (390x844)
- Verify system appearance (light/dark mode)

### Snapshots not saving
- Check write permissions in test directory
- Ensure `record: true` is set
- Look for snapshot files in `__Snapshots__/`

## Best Practices

1. **Keep snapshots small**: Test specific components, not entire screens
2. **Use meaningful names**: `"loaded"`, `"error"`, `"day_2"`
3. **Test critical paths**: Loading, empty, error states
4. **Deterministic data**: Use fixed mock responses
5. **Wait for async**: Use `Task.sleep` after `vm.load()`

## Related Documentation

- [Architecture Reference](../../docs/architecture/weekly-plan-reference.md)
- [WeeklyPlan MVVM Guide](../../docs/architecture/weekly-plan-reference.md#layers-and-responsibilities)
- [Swift Testing Documentation](https://developer.apple.com/documentation/testing)
- [SnapshotTesting Library](https://github.com/pointfreeco/swift-snapshot-testing)
