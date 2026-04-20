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

    // MARK: - AI Insight

    /// Controls visibility of the PRO-only AI Insight surface from Home.
    ///
    /// **Status**: Wave-1 additive surface for reliability parity validation
    /// **Current behavior**:
    /// - `AI_INSIGHT_ENABLED`: Enabled explicitly for controlled rollout
    /// - `DEBUG`: Enabled for development and QA
    /// - `RELEASE`: Disabled until rollout approval
    public static var aiInsightEnabled: Bool {
        #if AI_INSIGHT_ENABLED
        return true
        #elseif DEBUG
        return true
        #else
        return false
        #endif
    }

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
    /// - WEEKLY_PLAN_READER_ENABLED: Enabled (for TestFlight QA)
    /// - DEBUG: Enabled (for development)
    /// - RELEASE: Disabled (awaiting production rollout)
    public static var weeklyPlanReaderEnabled: Bool {
        #if WEEKLY_PLAN_READER_ENABLED
        return true
        #elseif DEBUG
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
    public static let weeklyPlanSplitViewEnabled: Bool = false

    /// VIP/Premium paywall gates
    ///
    /// **Status**: Architecture ready, UI pending
    /// **Note**: When enabled, Weekly Plan Reader requires active subscription
    public static let vipGatesEnabled: Bool = false
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
