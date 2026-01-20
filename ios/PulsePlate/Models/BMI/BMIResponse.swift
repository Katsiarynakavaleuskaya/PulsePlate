import Foundation

/// Response from POST /api/v1/bmi/calculate
///
/// IMPORTANT CONTRACT NOTE:
/// - `category` is treated as a DISPLAY STRING (may be localized string or token).
/// - iOS MUST NOT infer thresholds, compute categories/groups, or implement BMI logic.
/// - iOS is a thin renderer of backend contract only.
/// - Soft paywall hook is rendered only if `softPaywall != nil`, no BMI-dependent logic.
public struct BMIResponse: Codable, Sendable {
    public let bmi: Double
    public let category: String?
    public let group: String
    public let groupDisplay: String
    public let interpretation: String

    public let whtRatio: Double?
    public let waistRisk: WaistRisk?
    public let notes: [String]
    public let ageBand: String

    public let visualization: BMIScaleV1Spec?
    public let interpretationV1: BMIInterpretationV1Schema?
    public let softPaywall: SoftPaywallHook?

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

// MARK: - Waist risk

public struct WaistRisk: Codable, Sendable {
    public let whtRatio: Double?
    public let riskLevel: String
    public let notes: [String]

    enum CodingKeys: String, CodingKey {
        case whtRatio = "wht_ratio"
        case riskLevel = "risk_level"
        case notes
    }
}

// MARK: - Visualization

public struct BMIScaleV1Spec: Codable, Sendable {
    public let kind: String
    public let bmi: Double
    public let min: Double
    public let max: Double
    public let ranges: [BMIRange]
    public let marker: BMIMarker
}

public struct BMIRange: Codable, Sendable {
    /// i18n key; iOS локализует key по своей таблице
    public let key: String
    public let from: Double
    public let to: Double

    enum CodingKeys: String, CodingKey {
        case key
        case from
        case to
    }
}

public struct BMIMarker: Codable, Sendable {
    public let value: Double
}

// MARK: - Soft paywall

public struct SoftPaywallHook: Codable, Sendable {
    public let id: String
    public let kind: String
    public let position: String
    public let priority: Int
    public let message: SoftPaywallMessage
    public let availability: SoftPaywallAvailability
    public let target: String
}

public struct SoftPaywallMessage: Codable, Sendable {
    public let lang: String
    public let titleKey: String
    public let bodyKey: String
    public let ctaKey: String
    public let defaultTitle: String
    public let defaultBody: String
    public let defaultCta: String

    enum CodingKeys: String, CodingKey {
        case lang
        case titleKey = "title_key"
        case bodyKey = "body_key"
        case ctaKey = "cta_key"
        case defaultTitle = "default_title"
        case defaultBody = "default_body"
        case defaultCta = "default_cta"
    }
}

public struct SoftPaywallAvailability: Codable, Sendable {
    public let proAvailable: Bool
    public let reasonKey: String?

    enum CodingKeys: String, CodingKey {
        case proAvailable = "pro_available"
        case reasonKey = "reason_key"
    }
}

// MARK: - Interpretation v1 (future-safe)

public struct BMIInterpretationV1Schema: Codable, Sendable {
    public let goalDirection: String
    public let targetRange: TargetRange?
    public let riskFlags: [String]
    public let priorityNotes: [String]
    public let disclaimers: [String]

    enum CodingKeys: String, CodingKey {
        case goalDirection = "goal_direction"
        case targetRange = "target_range"
        case riskFlags = "risk_flags"
        case priorityNotes = "priority_notes"
        case disclaimers
    }
}

public enum TargetRange: Codable, Sendable {
    case numeric(NumericRange)
    case literal(String)

    public struct NumericRange: Codable, Sendable {
        public let min: Double
        public let max: Double
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let numeric = try? container.decode(NumericRange.self) {
            self = .numeric(numeric)
            return
        }
        if let literal = try? container.decode(String.self) {
            self = .literal(literal)
            return
        }
        throw DecodingError.dataCorruptedError(
            in: container,
            debugDescription: "TargetRange must be NumericRange or String"
        )
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .numeric(let range):
            try container.encode(range)
        case .literal(let str):
            try container.encode(str)
        }
    }
}
