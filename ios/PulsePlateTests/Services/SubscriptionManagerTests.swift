import XCTest
@testable import PulsePlate

@MainActor
final class SubscriptionManagerTests: XCTestCase {
    func test_purchaseHappyPathUnlocksOnlyAfterRefresh() async {
        let storeKit = MockStoreKitManager()
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore()
        let manager = makeManager(
            storeKit: storeKit,
            billing: billing,
            pointerStore: pointerStore
        )

        storeKit.purchaseResult = .success(.fixture())
        storeKit.receiptData = "receipt-123"
        billing.verifyResult = .activeVerify()
        billing.activateResult = .activeActivation(id: "act-123")
        billing.fetchResult = .activeActivation(id: "act-123")

        await manager.purchase(productID: "com.pulseplate.premium.monthly")

        XCTAssertEqual(manager.flowState, .unlocked)
        XCTAssertEqual(manager.entitlement?.activationID, "act-123")
        XCTAssertEqual(pointerStore.activationID, "act-123")
        XCTAssertEqual(billing.verifyCallCount, 1)
        XCTAssertEqual(billing.activateCallCount, 1)
        XCTAssertEqual(billing.fetchCallCount, 1)
    }

    func test_purchasePendingSetsPendingState() async {
        let storeKit = MockStoreKitManager()
        storeKit.purchaseResult = .pending
        let manager = makeManager(storeKit: storeKit)

        await manager.purchase(productID: "com.pulseplate.premium.monthly")

        XCTAssertEqual(manager.flowState, .pendingApproval)
    }

    func test_purchaseCancelledReturnsToIdle() async {
        let storeKit = MockStoreKitManager()
        storeKit.purchaseResult = .cancelled
        let manager = makeManager(storeKit: storeKit)

        await manager.purchase(productID: "com.pulseplate.premium.monthly")

        XCTAssertEqual(manager.flowState, .idle)
    }

    func test_purchaseStoreKitSuccessBackendVerifyFails() async {
        let storeKit = MockStoreKitManager()
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore()
        let manager = makeManager(
            storeKit: storeKit,
            billing: billing,
            pointerStore: pointerStore
        )

        storeKit.purchaseResult = .success(.fixture())
        storeKit.receiptData = "receipt-123"
        billing.verifyError = APIError.api(statusCode: 502, message: "Apple upstream error")

        await manager.purchase(productID: "com.pulseplate.premium.monthly")

        XCTAssertNil(pointerStore.activationID)
        XCTAssertNil(manager.entitlement)
        XCTAssertEqual(billing.activateCallCount, 0)
        if case .failed(let message) = manager.flowState {
            XCTAssertTrue(message.contains("Apple upstream error"))
        } else {
            XCTFail("Expected failed state")
        }
    }

    func test_purchaseVerifySuccessActivateFails() async {
        let storeKit = MockStoreKitManager()
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore()
        let manager = makeManager(
            storeKit: storeKit,
            billing: billing,
            pointerStore: pointerStore
        )

        storeKit.purchaseResult = .success(.fixture())
        storeKit.receiptData = "receipt-123"
        billing.verifyResult = .activeVerify()
        billing.activateError = APIError.api(statusCode: 409, message: "conflict")

        await manager.purchase(productID: "com.pulseplate.premium.monthly")

        XCTAssertNil(pointerStore.activationID)
        XCTAssertNil(manager.entitlement)
        XCTAssertEqual(billing.fetchCallCount, 0)
        if case .failed(let message) = manager.flowState {
            XCTAssertTrue(message.contains("conflict"))
        } else {
            XCTFail("Expected failed state")
        }
    }

    func test_restoreHappyPathUnlocksAfterRefresh() async {
        let storeKit = MockStoreKitManager()
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore()
        let manager = makeManager(
            storeKit: storeKit,
            billing: billing,
            pointerStore: pointerStore
        )

        storeKit.latestVerifiedTransaction = .fixture()
        storeKit.receiptData = "receipt-restore"
        billing.verifyResult = .restoredVerify()
        billing.activateResult = .activeActivation(id: "act-restore")
        billing.fetchResult = .activeActivation(id: "act-restore")

        await manager.restore()

        XCTAssertEqual(storeKit.syncCallCount, 1)
        XCTAssertEqual(manager.flowState, .unlocked)
        XCTAssertEqual(pointerStore.activationID, "act-restore")
    }

    func test_appRelaunchWithActivationIDRefreshesEntitlement() async {
        let storeKit = MockStoreKitManager()
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore(activationID: "act-boot")
        let manager = makeManager(
            storeKit: storeKit,
            billing: billing,
            pointerStore: pointerStore
        )

        storeKit.loadProductsError = StubError("catalog unavailable")
        billing.fetchResult = .activeActivation(id: "act-boot")

        await manager.bootstrap()

        XCTAssertEqual(manager.flowState, .unlocked)
        XCTAssertEqual(manager.entitlement?.activationID, "act-boot")
        if case .failed(let message) = manager.catalogState {
            XCTAssertTrue(message.contains("catalog unavailable"))
        } else {
            XCTFail("Expected catalog load failure")
        }
    }

    func test_offlineRefreshKeepsPointerButDoesNotUnlock() async {
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore(activationID: "act-offline")
        let manager = makeManager(
            billing: billing,
            pointerStore: pointerStore
        )

        billing.fetchError = APIError.transport("offline")

        await manager.refreshEntitlement(trigger: .manualRetry)

        XCTAssertEqual(pointerStore.activationID, "act-offline")
        XCTAssertNil(manager.entitlement)
        if case .failed(let message) = manager.flowState {
            XCTAssertTrue(message.contains("offline"))
        } else {
            XCTFail("Expected failed state")
        }
    }

    func test_bootstrapWithProductLoadFailureButSuccessfulEntitlementRefresh() async {
        let storeKit = MockStoreKitManager()
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore(activationID: "act-bootstrap")
        let manager = makeManager(
            storeKit: storeKit,
            billing: billing,
            pointerStore: pointerStore
        )

        storeKit.loadProductsError = StubError("storekit down")
        billing.fetchResult = .activeActivation(id: "act-bootstrap")

        await manager.bootstrap()

        XCTAssertEqual(manager.flowState, .unlocked)
        XCTAssertEqual(manager.entitlement?.activationID, "act-bootstrap")
        if case .failed(let message) = manager.catalogState {
            XCTAssertTrue(message.contains("storekit down"))
        } else {
            XCTFail("Expected product load failure")
        }
    }

    func test_storedActivationIDNotFoundClearsPointerAndDoesNotUnlock() async {
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore(activationID: "act-missing")
        let manager = makeManager(
            billing: billing,
            pointerStore: pointerStore
        )

        billing.fetchError = APIError.api(statusCode: 404, message: "act-missing")

        await manager.refreshEntitlement(trigger: .launch)

        XCTAssertNil(pointerStore.activationID)
        XCTAssertNil(manager.entitlement)
        XCTAssertEqual(manager.flowState, .idle)
        XCTAssertNil(manager.lastError)
    }

    func test_storedActivationIDForbiddenClearsPointerAndDoesNotUnlock() async {
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore(activationID: "act-forbidden")
        let manager = makeManager(
            billing: billing,
            pointerStore: pointerStore
        )

        billing.fetchError = APIError.api(statusCode: 403, message: "forbidden")

        await manager.refreshEntitlement(trigger: .launch)

        XCTAssertNil(pointerStore.activationID)
        XCTAssertNil(manager.entitlement)
        XCTAssertEqual(manager.flowState, .idle)
        XCTAssertNil(manager.lastError)
    }

    func test_foregroundRefreshWhilePurchaseInFlightDoesNotStartSecondFlow() async {
        let storeKit = MockStoreKitManager()
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore(activationID: "act-foreground")
        let manager = makeManager(
            storeKit: storeKit,
            billing: billing,
            pointerStore: pointerStore
        )

        storeKit.purchaseDelayNanoseconds = 100_000_000
        storeKit.purchaseError = StubError("purchase interrupted")

        let purchaseTask = Task {
            await manager.purchase(productID: "com.pulseplate.premium.monthly")
        }
        await Task.yield()
        await manager.refreshEntitlement(trigger: .foreground)
        await purchaseTask.value

        XCTAssertEqual(billing.fetchCallCount, 0)
    }

    func test_restoreSyncSuccessButNoVerifiedTransactionFailsClosed() async {
        let storeKit = MockStoreKitManager()
        let billing = MockSubscriptionBillingService()
        let pointerStore = InMemoryActivationPointerStore()
        let manager = makeManager(
            storeKit: storeKit,
            billing: billing,
            pointerStore: pointerStore
        )

        storeKit.latestVerifiedTransaction = nil

        await manager.restore()

        XCTAssertNil(pointerStore.activationID)
        XCTAssertNil(manager.entitlement)
        XCTAssertEqual(billing.fetchCallCount, 0)
        if case .failed(let message) = manager.flowState {
            XCTAssertTrue(message.contains("verified entitlement transaction"))
        } else {
            XCTFail("Expected failed state")
        }
    }

    private func makeManager(
        storeKit: MockStoreKitManager = MockStoreKitManager(),
        billing: MockSubscriptionBillingService = MockSubscriptionBillingService(),
        pointerStore: InMemoryActivationPointerStore = InMemoryActivationPointerStore(),
        apiKey: String? = ["pp", "placeholder"].joined(separator: "-")
    ) -> SubscriptionManager {
        SubscriptionManager(
            storeKitManager: storeKit,
            billingService: billing,
            activationPointerStore: pointerStore,
            apiKeyProvider: { apiKey }
        )
    }
}

private final class MockStoreKitManager: StoreKitManaging {
    var products: [SubscriptionProduct] = [
        SubscriptionProduct(
            id: "com.pulseplate.premium.monthly",
            displayName: "Premium Monthly",
            displayPrice: "$9.99"
        )
    ]
    var loadProductsError: Error?
    var purchaseResult: StorePurchaseResult = .cancelled
    var purchaseError: Error?
    var purchaseDelayNanoseconds: UInt64 = 0
    var latestVerifiedTransaction: StoreEntitlementTransaction?
    var receiptData: String = "receipt-default"
    var receiptError: Error?
    private(set) var syncCallCount = 0

    func loadProducts() async throws -> [SubscriptionProduct] {
        if let loadProductsError {
            throw loadProductsError
        }
        return products
    }

    func purchase(productID: String) async throws -> StorePurchaseResult {
        if purchaseDelayNanoseconds > 0 {
            try? await Task.sleep(nanoseconds: purchaseDelayNanoseconds)
        }
        if let purchaseError {
            throw purchaseError
        }
        return purchaseResult
    }

    func sync() async throws {
        syncCallCount += 1
    }

    func latestVerifiedEntitlementTransaction() async -> StoreEntitlementTransaction? {
        latestVerifiedTransaction
    }

    func currentReceiptData() async throws -> String {
        if let receiptError {
            throw receiptError
        }
        return receiptData
    }
}

private final class MockSubscriptionBillingService: SubscriptionBillingServicing {
    var verifyResult: AppleReceiptVerificationResponseDTO = .activeVerify()
    var verifyError: Error?
    var activateResult: SubscriptionActivationResponseDTO = .activeActivation(id: "act-default")
    var activateError: Error?
    var fetchResult: SubscriptionActivationResponseDTO = .activeActivation(id: "act-default")
    var fetchError: Error?
    private(set) var verifyCallCount = 0
    private(set) var activateCallCount = 0
    private(set) var fetchCallCount = 0

    func verifyReceipt(
        receiptData: String,
        apiKey: String
    ) async throws -> AppleReceiptVerificationResponseDTO {
        verifyCallCount += 1
        if let verifyError {
            throw verifyError
        }
        return verifyResult
    }

    func activateSubscription(
        request: ActivateSubscriptionRequestDTO,
        apiKey: String
    ) async throws -> SubscriptionActivationResponseDTO {
        activateCallCount += 1
        if let activateError {
            throw activateError
        }
        return activateResult
    }

    func fetchActivationStatus(
        activationID: String,
        apiKey: String
    ) async throws -> SubscriptionActivationResponseDTO {
        fetchCallCount += 1
        if let fetchError {
            throw fetchError
        }
        return fetchResult
    }
}

private final class InMemoryActivationPointerStore: ActivationPointerStoring {
    var activationID: String?

    init(activationID: String? = nil) {
        self.activationID = activationID
    }

    func loadActivationID() -> String? {
        activationID
    }

    func saveActivationID(_ id: String) {
        activationID = id
    }

    func clearActivationID() {
        activationID = nil
    }
}

private struct StubError: Error, LocalizedError {
    let message: String

    init(_ message: String) {
        self.message = message
    }

    var errorDescription: String? {
        message
    }
}

private extension StoreEntitlementTransaction {
    static func fixture() -> StoreEntitlementTransaction {
        StoreEntitlementTransaction(
            transactionID: "txn-001",
            originalTransactionID: "orig-001",
            productID: "com.pulseplate.premium.monthly"
        )
    }
}

private extension AppleReceiptVerificationResponseDTO {
    static func activeVerify() -> AppleReceiptVerificationResponseDTO {
        AppleReceiptVerificationResponseDTO(
            provider: "apple",
            verified: true,
            verificationState: .active,
            environment: "production",
            productID: "com.pulseplate.premium.monthly",
            expiresAt: "2026-04-01T00:00:00Z",
            activationPayload: AppleActivationHintDTO(tier: .pro, platform: "ios"),
            error: nil
        )
    }

    static func restoredVerify() -> AppleReceiptVerificationResponseDTO {
        AppleReceiptVerificationResponseDTO(
            provider: "apple",
            verified: true,
            verificationState: .restored,
            environment: "production",
            productID: "com.pulseplate.premium.monthly",
            expiresAt: "2026-04-01T00:00:00Z",
            activationPayload: AppleActivationHintDTO(tier: .pro, platform: "ios"),
            error: nil
        )
    }
}

private extension SubscriptionActivationResponseDTO {
    static func activeActivation(id: String) -> SubscriptionActivationResponseDTO {
        SubscriptionActivationResponseDTO(
            activationID: id,
            tier: "pro",
            status: "active",
            productID: "com.pulseplate.premium.monthly",
            expiresAt: "2026-04-01T00:00:00Z",
            activatedAt: "2026-03-10T00:00:00Z",
            subscriptionTier: "pro",
            source: "ios_app_store",
            paymentSource: "ios_app_store"
        )
    }
}
