import XCTest
@testable import PulsePlate

final class SoftPaywallCTARoutingTests: XCTestCase {
    @MainActor
    func test_presentPaywall_setsPresented_andStoresContext() async {
        let router = PaywallRouter()

        router.presentPaywall(source: .bmiSoftPaywallCTA, target: .pro)

        XCTAssertTrue(router.isPaywallPresented)
        XCTAssertEqual(router.lastSource, .bmiSoftPaywallCTA)
        XCTAssertEqual(router.lastTarget, .pro)
    }

    @MainActor
    func test_dismissPaywall_clearsPresentedFlag() async {
        let router = PaywallRouter()
        router.presentPaywall(source: .bmiSoftPaywallCTA, target: .pro)

        router.dismissPaywall()

        XCTAssertFalse(router.isPaywallPresented)
        XCTAssertNil(router.lastSource)
        XCTAssertNil(router.lastTarget)
    }

    func test_softPaywallTargetMapping_mapsVipPaywall() {
        XCTAssertEqual(PaywallTarget.fromSoftPaywallHookTarget("vip_paywall"), .vip)
        XCTAssertEqual(PaywallTarget.fromSoftPaywallHookTarget("vip"), .vip)
    }

    func test_softPaywallTargetMapping_fallsBackToNilForUnknown() {
        XCTAssertNil(PaywallTarget.fromSoftPaywallHookTarget("unknown"))
        XCTAssertNil(PaywallTarget.fromSoftPaywallHookTarget(""))
    }
}
