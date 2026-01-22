import Foundation

/// Interpretation v1 (i18n-key based).
///
/// Backend schema: `app/schemas/bmi.py::BMIInterpretationV1Schema` (lines 365-404)
/// All fields are i18n keys (client must perform lookup).
public struct BMIInterpretationV1DTO: Decodable, Sendable {

    public let goalDirection: String
    public let targetRange: TargetRangeDTO?
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

/// Target range: numeric or literal string.
///
/// Backend: `NumericRangeSchema | Literal["age_appropriate_growth", "prenatal_guidelines"] | None`
public enum TargetRangeDTO: Decodable, Sendable {
    case numeric(NumericRangeDTO)
    case literal(String)

    public struct NumericRangeDTO: Decodable, Sendable {
        public let min: Double
        public let max: Double
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let numeric = try? container.decode(NumericRangeDTO.self) {
            self = .numeric(numeric)
            return
        }
        if let literal = try? container.decode(String.self) {
            self = .literal(literal)
            return
        }
        throw DecodingError.dataCorruptedError(
            in: container,
            debugDescription: "TargetRangeDTO must be NumericRangeDTO or String"
        )
    }
}
