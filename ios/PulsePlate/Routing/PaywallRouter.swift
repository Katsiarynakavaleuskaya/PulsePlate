import Foundation
import Observation

/// Paywall router (navigation handler) for soft-paywall CTAs.
///
/// Thin-client rule:
/// - This router only manages presentation state.
/// - It must not contain subscription business logic (pricing/eligibility/tiers).
@MainActor
@Observable
final class PaywallRouter {
    private(set) var isPaywallPresented: Bool = false
    private(set) var lastSource: String? = nil
    private(set) var lastTarget: String? = nil

    func presentPaywall(source: String, target: String) {
        lastSource = source
        lastTarget = target
        isPaywallPresented = true
    }

    func dismissPaywall() {
        isPaywallPresented = false
    }
}
