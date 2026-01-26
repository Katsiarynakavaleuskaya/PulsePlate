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
    public let marker: BMIMarkerDTO?
    public let ranges: [BMIRangeDTO]
}

public struct BMIMarkerDTO: Decodable, Sendable {
    public let value: Double?

    private enum CodingKeys: String, CodingKey {
        case value
    }

    public init(value: Double?) {
        self.value = value
    }

    public init(from decoder: Decoder) throws {
        // New format: { "value": 12.3 }
        if let container = try? decoder.container(keyedBy: CodingKeys.self) {
            value = try container.decodeIfPresent(Double.self, forKey: .value)
            return
        }

        // Legacy format: 12.3
        let single = try decoder.singleValueContainer()
        if single.decodeNil() {
            value = nil
            return
        }

        do {
            value = try single.decode(Double.self)
        } catch {
            throw DecodingError.dataCorruptedError(
                in: single,
                debugDescription: "BMIMarkerDTO legacy marker must be Double or null."
            )
        }
    }
}

public struct BMIRangeDTO: Decodable, Sendable {

    /// i18n key, e.g. "bmi.normal"
    public let key: String
    public let from: Double?
    public let to: Double?
}
