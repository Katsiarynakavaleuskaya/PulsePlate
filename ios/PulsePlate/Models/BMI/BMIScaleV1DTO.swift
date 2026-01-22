import Foundation

/// BMI scale visualization (v1).
/// Client relies ONLY on ranges[].key for i18n lookup.
public struct BMIScaleV1DTO: Decodable, Sendable {

    public let ranges: [BMIRangeDTO]

    enum CodingKeys: String, CodingKey {
        case ranges
    }
}

public struct BMIRangeDTO: Decodable, Sendable {

    /// i18n key, e.g. "bmi.normal"
    public let key: String
    public let from: Double?
    public let to: Double?

    enum CodingKeys: String, CodingKey {
        case key
        case from
        case to
    }
}
