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
    let activationPayload: IOSVerifiedActivationResultDTO?
    let error: AppleProviderErrorDTO?

    private enum CodingKeys: String, CodingKey {
        case provider
        case verified
        case verificationState
        case environment
        case productID = "productId"
        case expiresAt
        case activationPayload
        case error
    }
}

struct IOSVerifiedActivationResultDTO: Codable, Equatable, Sendable {
    let transactionID: String
    let originalTransactionID: String?
    let productID: String
    let subscriptionTier: BillingSubscriptionTier
    let status: BillingVerificationStatus
    let expiresAt: String?
    let platform: BillingPlatform

    // RU: Декодирование идёт через HTTPClient с `.convertFromSnakeCase`, поэтому ключи
    // здесь должны совпадать с уже преобразованными именами (`transactionId`).
    // Кодирование для activate-request остаётся канонически snake_case, поэтому для
    // encode используется отдельный набор ключей ниже.
    // EN: Decoding goes through HTTPClient with `.convertFromSnakeCase`, so these keys
    // must match the already-transformed names (`transactionId`).
    // Encoding for the activate request must stay canonical snake_case, so encode uses
    // a separate key set below.
    private enum DecodingKeys: String, CodingKey {
        case transactionID = "transactionId"
        case originalTransactionID = "originalTransactionId"
        case productID = "productId"
        case subscriptionTier
        case status
        case expiresAt
        case platform
    }

    private enum EncodingKeys: String, CodingKey {
        case transactionID = "transaction_id"
        case originalTransactionID = "original_transaction_id"
        case productID = "product_id"
        case subscriptionTier = "subscription_tier"
        case status
        case expiresAt = "expires_at"
        case platform
    }

    init(
        transactionID: String,
        originalTransactionID: String?,
        productID: String,
        subscriptionTier: BillingSubscriptionTier,
        status: BillingVerificationStatus,
        expiresAt: String?,
        platform: BillingPlatform
    ) {
        self.transactionID = transactionID
        self.originalTransactionID = originalTransactionID
        self.productID = productID
        self.subscriptionTier = subscriptionTier
        self.status = status
        self.expiresAt = expiresAt
        self.platform = platform
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: DecodingKeys.self)
        self.transactionID = try container.decode(String.self, forKey: .transactionID)
        self.originalTransactionID = try container.decodeIfPresent(String.self, forKey: .originalTransactionID)
        self.productID = try container.decode(String.self, forKey: .productID)
        self.subscriptionTier = try container.decode(BillingSubscriptionTier.self, forKey: .subscriptionTier)
        self.status = try container.decode(BillingVerificationStatus.self, forKey: .status)
        self.expiresAt = try container.decodeIfPresent(String.self, forKey: .expiresAt)
        self.platform = try container.decode(BillingPlatform.self, forKey: .platform)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: EncodingKeys.self)
        try container.encode(transactionID, forKey: .transactionID)
        try container.encodeIfPresent(originalTransactionID, forKey: .originalTransactionID)
        try container.encode(productID, forKey: .productID)
        try container.encode(subscriptionTier, forKey: .subscriptionTier)
        try container.encode(status, forKey: .status)
        try container.encodeIfPresent(expiresAt, forKey: .expiresAt)
        try container.encode(platform, forKey: .platform)
    }
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
        case activationID = "activationId"
        case tier
        case status
        case productID = "productId"
        case expiresAt
        case activatedAt
        case subscriptionTier
        case source
        case paymentSource
    }
}
