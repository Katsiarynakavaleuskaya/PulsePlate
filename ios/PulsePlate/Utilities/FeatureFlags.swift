import Foundation

/// Centralized feature toggles for PulsePlate
///
/// Feature flags control visibility and behavior of new/experimental features.
/// Use flags to ship code to production without exposing incomplete functionality.
///
/// ## Pattern:
/// - `true` in DEBUG: Enable for local development/testing
/// - `false` in RELEASE: Hide from production until ready
/// - Future: Replace with remote config (Firebase, LaunchDarkly, etc.)
public enum FeatureFlags {

    // MARK: - Weekly Plan Reader

    /// Controls visibility of Weekly Plan Reader feature
    ///
    /// **Status**: MVP complete, pending integration testing
    /// **Enable when**:
    /// - Backend API stable and deployed
    /// - Paywall/VIP gates implemented
    /// - Smoke checklist passed (see WeeklyPlanReaderSmokeChecklist.md)
    ///
    /// **Current behavior**:
    /// - DEBUG: Enabled (mock service available)
    /// - RELEASE: Disabled (awaiting TestFlight validation)
    public static var weeklyPlanReaderEnabled: Bool {
        #if DEBUG
        return true
        #else
        return false
        #endif
    }

    // MARK: - Future Features

    /// iPad/Mac NavigationSplitView for Weekly Plan Reader
    ///
    /// **Status**: Planned for next iteration
    /// **Dependencies**: weeklyPlanReaderEnabled must be true
    public static var weeklyPlanSplitViewEnabled: Bool {
        #if DEBUG
        return false // Enable when implemented
        #else
        return false
        #endif
    }

    /// VIP/Premium paywall gates
    ///
    /// **Status**: Architecture ready, UI pending
    /// **Note**: When enabled, Weekly Plan Reader requires active subscription
    public static var vipGatesEnabled: Bool {
        #if DEBUG
        return false
        #else
        return false
        #endif
    }
}

// MARK: - Usage Example
/*
 In your view:

 ```swift
 var body: some View {
     if FeatureFlags.weeklyPlanReaderEnabled {
         WeeklyPlanReaderView(...)
     } else {
         PlaceholderView()
     }
 }
 ```
 */
