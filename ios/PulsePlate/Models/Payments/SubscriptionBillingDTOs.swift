import Foundation

enum BillingSource: String, Codable, Sendable {
    case iosAppStore = "ios_app_store"
}

enum BillingSubscriptionTier: String, Codable, Sendable {
    case pro
    case vip
}

enum BillingVerificationState: String, Codable, Sendable {
    case active
    case expired
    case restored
    case invalid
}

enum BillingVerificationStatus: String, Codable, Sendable {
    case active
    case expired
    case rejected
}

enum BillingPlatform: String, Codable, Sendable {
    case ios
}

struct AppleActivationHintDTO: Decodable, Equatable, Sendable {
    let tier: BillingSubscriptionTier
    let platform: String
}

struct AppleProviderErrorDTO: Decodable, Equatable, Sendable {
    let code: String
    let message: String
}

struct AppleReceiptVerificationRequestDTO: Encodable, Equatable, Sendable {
    let receiptData: String
}

struct AppleReceiptVerificationResponseDTO: Decodable, Equatable, Sendable {
    let provider: String
    let verified: Bool
    let verificationState: BillingVerificationState
    let environment: String?
    let productID: String?
    let expiresAt: String?
    let activationPayload: AppleActivationHintDTO?
    let error: AppleProviderErrorDTO?

    private enum CodingKeys: String, CodingKey {
        case provider
        case verified
        case verificationState
        case environment
        case productID
        case expiresAt
        case activationPayload
        case error
    }
}

struct IOSVerifiedActivationResultDTO: Encodable, Equatable, Sendable {
    let transactionID: String
    let originalTransactionID: String?
    let productID: String
    let subscriptionTier: BillingSubscriptionTier
    let status: BillingVerificationStatus
    let expiresAt: String?
    let platform: BillingPlatform
}

struct IOSAppStoreActivationPayloadDTO: Encodable, Equatable, Sendable {
    let verificationResult: IOSVerifiedActivationResultDTO
    let receiptData: String
}

struct ActivateSubscriptionRequestDTO: Encodable, Equatable, Sendable {
    let source: BillingSource
    let payload: IOSAppStoreActivationPayloadDTO
}

struct SubscriptionActivationResponseDTO: Decodable, Equatable, Sendable {
    let activationID: String
    let tier: String?
    let status: String
    let productID: String?
    let expiresAt: String?
    let activatedAt: String?
    let subscriptionTier: String?
    let source: String?
    let paymentSource: String?

    private enum CodingKeys: String, CodingKey {
        case activationID
        case tier
        case status
        case productID
        case expiresAt
        case activatedAt
        case subscriptionTier
        case source
        case paymentSource
    }
}
