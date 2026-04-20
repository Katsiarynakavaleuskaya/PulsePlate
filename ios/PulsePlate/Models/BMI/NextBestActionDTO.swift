import Foundation

/// Server-authored advisory next-step hint.
///
/// Thin-client rule:
/// - iOS only decodes and forwards this payload
/// - no local tier inference or business logic beyond route-safe mapping
public struct NextBestActionDTO: Decodable, Equatable, Sendable {
    public let type: String
    public let recommendedSurface: String
    public let recommendedTier: String
    public let triggerReason: String
    public let whyNow: String

    enum CodingKeys: String, CodingKey {
        case type
        case recommendedSurface = "recommended_surface"
        case recommendedTier = "recommended_tier"
        case triggerReason = "trigger_reason"
        case whyNow = "why_now"
    }
}
