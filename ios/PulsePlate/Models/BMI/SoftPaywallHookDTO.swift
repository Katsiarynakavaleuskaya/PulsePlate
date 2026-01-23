import Foundation

/// Soft paywall hook DTO.
///
/// Contract: `null` when disabled, full object when enabled (never `{enabled: false}`).
public struct SoftPaywallHookDTO: Decodable, Sendable {

    public let id: String
    public let kind: String
    public let position: String
    public let priority: Int
    public let message: SoftPaywallMessageDTO
    public let availability: SoftPaywallAvailabilityDTO
    public let target: String

    enum CodingKeys: String, CodingKey {
        case id
        case kind
        case position
        case priority
        case message
        case availability
        case target
    }
}

public struct SoftPaywallMessageDTO: Decodable, Sendable {

    /// i18n keys
    public let titleKey: String?
    public let bodyKey: String?
    public let ctaKey: String?

    /// localized fallback text
    public let defaultTitle: String?
    public let defaultBody: String?
    public let defaultCta: String?

    enum CodingKeys: String, CodingKey {
        case titleKey = "title_key"
        case bodyKey = "body_key"
        case ctaKey = "cta_key"
        case defaultTitle = "default_title"
        case defaultBody = "default_body"
        case defaultCta = "default_cta"
    }
}

public struct SoftPaywallAvailabilityDTO: Decodable, Sendable {

    public let proAvailable: Bool
    public let reasonKey: String?

    enum CodingKeys: String, CodingKey {
        case proAvailable = "pro_available"
        case reasonKey = "reason_key"
    }
}
