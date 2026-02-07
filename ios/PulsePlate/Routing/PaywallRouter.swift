import Combine
import Foundation

/// Paywall router (navigation handler) for soft-paywall CTAs.
///
/// Thin-client rule:
/// - This router only manages presentation state.
/// - It must not contain subscription business logic (pricing/eligibility/tiers).
@MainActor
final class PaywallRouter: ObservableObject {
    @Published var isPaywallPresented: Bool = false
    @Published var lastSource: PaywallSource? = nil
    @Published var lastTarget: PaywallTarget? = nil

    func presentPaywall(source: PaywallSource, target: PaywallTarget) {
        lastSource = source
        lastTarget = target
        isPaywallPresented = true
    }

    func dismissPaywall() {
        isPaywallPresented = false
        lastSource = nil
        lastTarget = nil
    }
}

enum PaywallSource: String, Equatable {
    case bmiSoftPaywallCTA
}

enum PaywallTarget: String, Equatable {
    case pro
    case vip

    /// Map backend soft-paywall `hook.target` strings to typed enum.
    ///
    /// Backend currently emits `pro_paywall` (see app.schemas.bmi.SoftPaywallHook).
    /// This mapping keeps iOS routing forward-compatible if backend adds new targets.
    static func fromSoftPaywallHookTarget(_ target: String) -> PaywallTarget? {
        let normalized = target.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        switch normalized {
        case "pro_paywall", "pro":
            return .pro
        case "vip_paywall", "vip":
            return .vip
        default:
            return nil
        }
    }
}
