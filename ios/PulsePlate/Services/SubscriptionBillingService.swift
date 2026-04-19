import Foundation

protocol SubscriptionBillingServicing {
    func verifyReceipt(
        receiptData: String,
        apiKey: String
    ) async throws -> AppleReceiptVerificationResponseDTO

    func activateSubscription(
        request: ActivateSubscriptionRequestDTO,
        apiKey: String
    ) async throws -> SubscriptionActivationResponseDTO

    func fetchActivationStatus(
        activationID: String,
        apiKey: String
    ) async throws -> SubscriptionActivationResponseDTO
}

final class SubscriptionBillingService: SubscriptionBillingServicing, Sendable {
    private let apiClient: APIClientProtocol

    init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    func verifyReceipt(
        receiptData: String,
        apiKey: String
    ) async throws -> AppleReceiptVerificationResponseDTO {
        try await apiClient.post(
            path: "/api/v1/billing/apple/verify-receipt",
            body: AppleReceiptVerificationRequestDTO(receiptData: receiptData),
            headers: ["X-API-Key": apiKey]
        )
    }

    func activateSubscription(
        request: ActivateSubscriptionRequestDTO,
        apiKey: String
    ) async throws -> SubscriptionActivationResponseDTO {
        try await apiClient.post(
            path: "/api/v1/pro/payments/activate",
            body: request,
            headers: ["X-API-Key": apiKey]
        )
    }

    func fetchActivationStatus(
        activationID: String,
        apiKey: String
    ) async throws -> SubscriptionActivationResponseDTO {
        try await apiClient.get(
            path: "/api/v1/pro/payments/activations/\(activationID)",
            headers: ["X-API-Key": apiKey]
        )
    }
}
