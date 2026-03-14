import XCTest
@testable import PulsePlate

final class SubscriptionBillingServiceTests: XCTestCase {
    private let testAPIKey = ["pp", "placeholder"].joined(separator: "-")

    func test_verifyReceipt_sendsCanonicalPathHeaderAndBody() async throws {
        let apiClient = CapturingSubscriptionAPIClient(
            verifyResult: AppleReceiptVerificationResponseDTO(
                provider: "apple",
                verified: true,
                verificationState: .active,
                environment: "production",
                productID: "com.pulseplate.premium.monthly",
                expiresAt: "2026-04-01T00:00:00Z",
                activationPayload: AppleActivationHintDTO(tier: .pro, platform: "ios"),
                error: nil
            )
        )
        let service = SubscriptionBillingService(apiClient: apiClient)

        _ = try await service.verifyReceipt(
            receiptData: "receipt-123",
            apiKey: testAPIKey
        )

        XCTAssertEqual(apiClient.lastPostPath, "/api/v1/billing/apple/verify-receipt")
        XCTAssertEqual(apiClient.lastPostHeaders?["X-API-Key"], testAPIKey)
        XCTAssertEqual(apiClient.lastJSONBody?["receipt_data"] as? String, "receipt-123")
    }

    func test_activateSubscription_sendsCanonicalPathHeaderAndNestedBody() async throws {
        let apiClient = CapturingSubscriptionAPIClient(
            activateResult: SubscriptionActivationResponseDTO(
                activationID: "act-001",
                tier: "pro",
                status: "active",
                productID: "com.pulseplate.premium.monthly",
                expiresAt: "2026-04-01T00:00:00Z",
                activatedAt: "2026-03-10T00:00:00Z",
                subscriptionTier: "pro",
                source: "ios_app_store",
                paymentSource: "ios_app_store"
            )
        )
        let service = SubscriptionBillingService(apiClient: apiClient)

        let request = ActivateSubscriptionRequestDTO(
            source: .iosAppStore,
            payload: IOSAppStoreActivationPayloadDTO(
                verificationResult: IOSVerifiedActivationResultDTO(
                    transactionID: "txn-001",
                    originalTransactionID: "orig-001",
                    productID: "com.pulseplate.premium.monthly",
                    subscriptionTier: .pro,
                    status: .active,
                    expiresAt: "2026-04-01T00:00:00Z",
                    platform: .ios
                ),
                receiptData: "receipt-123"
            )
        )

        _ = try await service.activateSubscription(
            request: request,
            apiKey: testAPIKey
        )

        XCTAssertEqual(apiClient.lastPostPath, "/api/v1/pro/payments/activate")
        XCTAssertEqual(apiClient.lastPostHeaders?["X-API-Key"], testAPIKey)
        XCTAssertEqual(apiClient.lastJSONBody?["source"] as? String, "ios_app_store")
        let payload = try XCTUnwrap(apiClient.lastJSONBody?["payload"] as? [String: Any])
        let verificationResult = try XCTUnwrap(payload["verification_result"] as? [String: Any])
        XCTAssertEqual(verificationResult["transaction_id"] as? String, "txn-001")
        XCTAssertEqual(verificationResult["subscription_tier"] as? String, "pro")
        XCTAssertEqual(payload["receipt_data"] as? String, "receipt-123")
    }

    func test_fetchActivationStatus_sendsCanonicalPathAndHeader() async throws {
        let apiClient = CapturingSubscriptionAPIClient(
            fetchResult: SubscriptionActivationResponseDTO(
                activationID: "act-001",
                tier: "pro",
                status: "active",
                productID: "com.pulseplate.premium.monthly",
                expiresAt: "2026-04-01T00:00:00Z",
                activatedAt: nil,
                subscriptionTier: "pro",
                source: "ios_app_store",
                paymentSource: "ios_app_store"
            )
        )
        let service = SubscriptionBillingService(apiClient: apiClient)

        _ = try await service.fetchActivationStatus(
            activationID: "act-001",
            apiKey: testAPIKey
        )

        XCTAssertEqual(apiClient.lastGetPath, "/api/v1/pro/payments/activations/act-001")
        XCTAssertEqual(apiClient.lastGetHeaders?["X-API-Key"], testAPIKey)
    }

    func test_service_propagatesAPIErrorsWithoutReinterpretation() async {
        let apiClient = CapturingSubscriptionAPIClient(
            verifyError: APIError.api(statusCode: 502, message: "Apple upstream error")
        )
        let service = SubscriptionBillingService(apiClient: apiClient)

        do {
            _ = try await service.verifyReceipt(
                receiptData: "receipt-123",
                apiKey: testAPIKey
            )
            XCTFail("Expected verifyReceipt to throw")
        } catch let error as APIError {
            XCTAssertEqual(error, .api(statusCode: 502, message: "Apple upstream error"))
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }
}

// RU: XCTest helper не мутируется после настройки сценария, поэтому `@unchecked Sendable` безопасен.
// EN: This XCTest helper is only configured before use, so `@unchecked Sendable` is safe here.
private final class CapturingSubscriptionAPIClient: APIClientProtocol, @unchecked Sendable {
    var lastPostPath: String?
    var lastPostHeaders: [String: String]?
    var lastJSONBody: [String: Any]?
    var lastGetPath: String?
    var lastGetHeaders: [String: String]?

    private let verifyResult: AppleReceiptVerificationResponseDTO?
    private let activateResult: SubscriptionActivationResponseDTO?
    private let fetchResult: SubscriptionActivationResponseDTO?
    private let verifyError: Error?

    init(
        verifyResult: AppleReceiptVerificationResponseDTO? = nil,
        activateResult: SubscriptionActivationResponseDTO? = nil,
        fetchResult: SubscriptionActivationResponseDTO? = nil,
        verifyError: Error? = nil
    ) {
        self.verifyResult = verifyResult
        self.activateResult = activateResult
        self.fetchResult = fetchResult
        self.verifyError = verifyError
    }

    func postRaw<Response: Decodable>(
        path: String,
        body: Data,
        headers: [String: String]
    ) async throws -> Response {
        fatalError("Not used in this test")
    }

    func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String]
    ) async throws -> Response {
        lastPostPath = path
        lastPostHeaders = headers
        lastJSONBody = try Self.jsonDictionary(from: body)

        if path == "/api/v1/billing/apple/verify-receipt" {
            if let verifyError {
                throw verifyError
            }
            if Response.self == AppleReceiptVerificationResponseDTO.self {
                return verifyResult as! Response
            }
        }

        if path == "/api/v1/pro/payments/activate", Response.self == SubscriptionActivationResponseDTO.self {
            return activateResult as! Response
        }

        fatalError("Unexpected post request: \(path)")
    }

    func get<Response: Decodable>(
        path: String,
        headers: [String: String]
    ) async throws -> Response {
        lastGetPath = path
        lastGetHeaders = headers

        if Response.self == SubscriptionActivationResponseDTO.self {
            return fetchResult as! Response
        }

        fatalError("Unexpected get request: \(path)")
    }

    private static func jsonDictionary<Body: Encodable>(from body: Body) throws -> [String: Any] {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let data = try encoder.encode(body)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }
}
