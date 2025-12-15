import Testing
import SwiftUI
import UIKit
import SnapshotTesting
@testable import PulsePlate

/// Snapshot tests for WeeklyPlanReaderView using Swift Testing framework
@Suite("WeeklyPlanReaderView Snapshots")
struct WeeklyPlanReaderViewSnapshotTests {

    @Test("Loaded state renders correctly")
    func loadedStateSnapshot() async throws {
        let vm = WeeklyPlanReaderViewModel(
            service: MockWeeklyPlanService.previewLoaded()
        )
        let view = WeeklyPlanReaderView(vm: vm)

        // Trigger load and wait for completion
        vm.load()
        try await Task.sleep(for: .milliseconds(500))

        try assertSnapshotHosting(view, named: "loaded")
    }

    @Test("Empty state renders correctly")
    func emptyStateSnapshot() async throws {
        let vm = WeeklyPlanReaderViewModel(
            service: MockWeeklyPlanService.previewEmpty()
        )
        let view = WeeklyPlanReaderView(vm: vm)

        // Trigger load and wait for completion
        vm.load()
        try await Task.sleep(for: .milliseconds(500))

        try assertSnapshotHosting(view, named: "empty")
    }

    @Test("Error state renders correctly")
    func errorStateSnapshot() async throws {
        let vm = WeeklyPlanReaderViewModel(
            service: MockWeeklyPlanService.previewError(message: "Network timeout")
        )
        let view = WeeklyPlanReaderView(vm: vm)

        // Trigger load and wait for error
        vm.load()
        try await Task.sleep(for: .milliseconds(500))

        try assertSnapshotHosting(view, named: "error")
    }

    @Test("Loading state renders correctly")
    func loadingStateSnapshot() async throws {
        // Use slow mock to catch loading state
        let slowService = MockWeeklyPlanService(mode: .loaded, delay: .seconds(2))
        let vm = WeeklyPlanReaderViewModel(service: slowService)
        let view = WeeklyPlanReaderView(vm: vm)

        // Trigger load but don't wait
        vm.load()
        try await Task.sleep(for: .milliseconds(100))

        try assertSnapshotHosting(view, named: "loading")
    }

    @Test("Day navigation - second day")
    func dayNavigationSnapshot() async throws {
        let vm = WeeklyPlanReaderViewModel(
            service: MockWeeklyPlanService.previewLoaded()
        )
        let view = WeeklyPlanReaderView(vm: vm)

        // Load and navigate to day 2
        vm.load()
        try await Task.sleep(for: .milliseconds(500))
        vm.nextDay(totalDays: 2)

        try assertSnapshotHosting(view, named: "day_2")
    }

    @Test("Coverage expanded state")
    func coverageExpandedSnapshot() async throws {
        let vm = WeeklyPlanReaderViewModel(
            service: MockWeeklyPlanService.previewLoaded()
        )
        let view = WeeklyPlanReaderView(vm: vm)

        // Load and expand coverage
        vm.load()
        try await Task.sleep(for: .milliseconds(500))
        vm.toggleCoverage()

        try assertSnapshotHosting(view, named: "coverage_expanded")
    }
}

// MARK: - Helper

/// Assert snapshot matches using SnapshotTesting with Swift Testing framework
private func assertSnapshotHosting<V: View>(
    _ view: V,
    named: String,
    fileID: StaticString = #fileID,
    filePath: StaticString = #filePath,
    line: UInt = #line
) throws {
    // Wrap view in UIHostingController with deterministic size
    let vc = UIHostingController(rootView: view)
    vc.view.frame = CGRect(x: 0, y: 0, width: 390, height: 844) // iPhone 14 size
    vc.view.backgroundColor = .systemBackground

    // Force layout pass
    vc.view.layoutIfNeeded()

    // Verify snapshot
    let failure = verifySnapshot(
        of: vc,
        as: .image(on: .iPhone13Pro),
        named: named,
        record: false,  // Change to true to record new baselines
        file: filePath,
        testName: "WeeklyPlanReaderViewSnapshotTests",
        line: line
    )

    // Swift Testing assertion
    #expect(failure == nil, "Snapshot mismatch for '\(named)': \(failure ?? "unknown diff")")
}
