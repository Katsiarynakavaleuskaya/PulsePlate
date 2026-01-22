import Foundation

/// Response DTO for canonical BMI calculation.
///
/// Backend: POST /api/v1/bmi/calculate
///
/// Contract:
/// - `category` may be nil (child / teen / pregnant / too_young)
/// - `groupDisplay` and `interpretation` are localized TEXT
/// - i18n KEYS appear only in visualization / interpretation_v1 / soft_paywall
/// - No client-side logic allowed
public struct BMICalculateResponseDTO: Decodable, Sendable {

    public let bmi: Double
    public let category: String?
    public let group: String
    public let groupDisplay: String
    public let interpretation: String

    public let whtRatio: Double?
    public let waistRisk: WaistRiskDTO?
    public let notes: [String]
    public let ageBand: String

    public let visualization: BMIScaleV1DTO?
    public let interpretationV1: BMIInterpretationV1DTO?
    public let softPaywall: SoftPaywallHookDTO?

    enum CodingKeys: String, CodingKey {
        case bmi
        case category
        case group
        case groupDisplay = "group_display"
        case interpretation
        case whtRatio = "wht_ratio"
        case waistRisk = "waist_risk"
        case notes
        case ageBand = "age_band"
        case visualization
        case interpretationV1 = "interpretation_v1"
        case softPaywall = "soft_paywall"
    }
}
