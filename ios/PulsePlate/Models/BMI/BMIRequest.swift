import Foundation

/// POST /api/v1/bmi/calculate
/// Contract: FREE tier endpoint (no API key required)
public struct BMIRequest: Encodable, Sendable {
    public let weightKg: Double
    public let heightCm: Double
    public let age: Int
    public let gender: String?
    public let pregnant: Bool?
    public let athlete: Bool?
    public let waistCm: Double?
    public let lang: String?

    enum CodingKeys: String, CodingKey {
        case weightKg = "weight_kg"
        case heightCm = "height_cm"
        case age
        case gender
        case pregnant
        case athlete
        case waistCm = "waist_cm"
        case lang
    }

    public init(
        weightKg: Double,
        heightCm: Double,
        age: Int,
        gender: String? = nil,
        pregnant: Bool? = nil,
        athlete: Bool? = nil,
        waistCm: Double? = nil,
        lang: String? = nil
    ) {
        self.weightKg = weightKg
        self.heightCm = heightCm
        self.age = age
        self.gender = gender
        self.pregnant = pregnant
        self.athlete = athlete
        self.waistCm = waistCm
        self.lang = lang
    }
}
