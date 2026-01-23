import Foundation

/// BMI scale visualization (v1).
/// Client relies ONLY on ranges[].key for i18n lookup.
/// Other fields (kind, bmi, min, max, marker) are kept to match backend contract and avoid silent drift.
public struct BMIScaleV1DTO: Decodable, Sendable {
    // Keep full contract to avoid silent drift.
    public let kind: String?
    public let bmi: Double?
    public let min: Double?
    public let max: Double?
    public let marker: Double?
    public let ranges: [BMIRangeDTO]
}

public struct BMIRangeDTO: Decodable, Sendable {

    /// i18n key, e.g. "bmi.normal"
    public let key: String
    public let from: Double?
    public let to: Double?
}
