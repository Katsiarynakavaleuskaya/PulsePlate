import XCTest
@testable import PulsePlate

final class SoftPaywallCTARoutingTests: XCTestCase {
    @MainActor
    func test_presentPaywall_setsPresented_andStoresContext() async {
        let router = PaywallRouter()

        router.presentPaywall(source: "bmi_soft_paywall", target: "pro_paywall")

        let isPaywallPresented = router.isPaywallPresented
        let lastSource = router.lastSource
        let lastTarget = router.lastTarget

        XCTAssertTrue(isPaywallPresented)
        XCTAssertEqual(lastSource, "bmi_soft_paywall")
        XCTAssertEqual(lastTarget, "pro_paywall")
    }

    @MainActor
    func test_dismissPaywall_clearsPresentedFlag() async {
        let router = PaywallRouter()
        router.presentPaywall(source: "bmi_soft_paywall", target: "pro_paywall")

        router.dismissPaywall()

        let isPaywallPresented = router.isPaywallPresented
        XCTAssertFalse(isPaywallPresented)
    }
}
