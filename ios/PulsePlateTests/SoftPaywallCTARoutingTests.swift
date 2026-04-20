import XCTest
@testable import PulsePlate

final class SoftPaywallCTARoutingTests: XCTestCase {
    @MainActor
    func test_presentPaywall_setsPresented_andStoresContext() async {
        let router = PaywallRouter()
        let nextBestAction = NextBestActionDTO(
            type: "unlock_targets",
            recommendedSurface: "pro_targets",
            recommendedTier: "PRO",
            triggerReason: "post_bmi",
            whyNow: "post_bmi_baseline_body_metrics"
        )

        router.presentPaywall(
            source: .bmiSoftPaywallCTA,
            target: .pro,
            nextBestAction: nextBestAction
        )

        XCTAssertTrue(router.isPaywallPresented)
        XCTAssertEqual(router.lastSource, .bmiSoftPaywallCTA)
        XCTAssertEqual(router.lastTarget, .pro)
        XCTAssertEqual(router.lastNextBestAction, nextBestAction)
    }

    @MainActor
    func test_dismissPaywall_clearsPresentedFlag() async {
        let router = PaywallRouter()
        router.presentPaywall(source: .bmiSoftPaywallCTA, target: .pro)

        router.dismissPaywall()

        XCTAssertFalse(router.isPaywallPresented)
        XCTAssertNil(router.lastSource)
        XCTAssertNil(router.lastTarget)
        XCTAssertNil(router.lastNextBestAction)
    }

    func test_softPaywallTargetMapping_mapsVipPaywall() {
        XCTAssertEqual(PaywallTarget.fromSoftPaywallHookTarget("vip_paywall"), .vip)
        XCTAssertEqual(PaywallTarget.fromSoftPaywallHookTarget("vip"), .vip)
    }

    func test_nextBestActionSurfaceMapping_mapsProSurfaces() {
        XCTAssertEqual(PaywallTarget.fromNextBestActionSurface("pro_targets"), .pro)
        XCTAssertEqual(PaywallTarget.fromNextBestActionSurface("pro_daily_plate"), .pro)
    }

    func test_nextBestActionSurfaceMapping_mapsVipSurface() {
        XCTAssertEqual(PaywallTarget.fromNextBestActionSurface("vip_export"), .vip)
    }

    func test_resolve_prefersNextBestActionSurface() {
        let nextBestAction = NextBestActionDTO(
            type: "upgrade_for_export",
            recommendedSurface: "vip_export",
            recommendedTier: "VIP",
            triggerReason: "weekly_plan_ready",
            whyNow: "weekly_plan_ready_export_and_share"
        )

        XCTAssertEqual(
            PaywallTarget.resolve(
                softPaywallTarget: "pro_paywall",
                nextBestAction: nextBestAction
            ),
            .vip
        )
    }

    func test_softPaywallTargetMapping_fallsBackToNilForUnknown() {
        XCTAssertNil(PaywallTarget.fromSoftPaywallHookTarget("unknown"))
        XCTAssertNil(PaywallTarget.fromSoftPaywallHookTarget(""))
    }

    func test_nextBestActionSurfaceMapping_fallsBackToNilForUnknown() {
        XCTAssertNil(PaywallTarget.fromNextBestActionSurface("unknown"))
        XCTAssertNil(PaywallTarget.fromNextBestActionSurface(""))
    }
}
