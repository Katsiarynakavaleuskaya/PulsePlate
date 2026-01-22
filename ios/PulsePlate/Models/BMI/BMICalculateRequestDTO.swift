import Foundation

/// Request DTO for canonical BMI calculation endpoint.
///
/// Backend: POST /api/v1/bmi/calculate
///
/// Contract notes:
/// - All numeric values must be positive where applicable
/// - `category` is NOT part of request (response-only)
/// - `lang` defaults to "en" on backend if omitted
///
/// Forbidden:
/// - No computed properties
/// - No validation logic
/// - No default value inference
public struct BMICalculateRequestDTO: Encodable, Equatable, Sendable {

    /// Weight in kilograms (gt=0)
    public let weightKg: Double

    /// Height in centimeters (gt=0)
    public let heightCm: Double

    /// Age in years (1...120)
    public let age: Int

    /// Gender (normalized on backend)
    /// Allowed values: "male", "female" (case-insensitive)
    /// Optional by contract.
    public let gender: String?

    /// Pregnancy flag (normalized on backend)
    /// Accepts bool or string on backend; client sends Bool.
    public let pregnant: Bool?

    /// Athlete flag (normalized on backend)
    /// Accepts bool or string on backend; client sends Bool.
    public let athlete: Bool?

    /// Waist circumference in centimeters (gt=0 if provided)
    public let waistCm: Double?

    /// Language code for localization (default handled by backend)
    /// Examples: "en", "ru", "es"
    public let lang: String?

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

    private enum CodingKeys: String, CodingKey {
        case weightKg = "weight_kg"
        case heightCm = "height_cm"
        case age
        case gender
        case pregnant
        case athlete
        case waistCm = "waist_cm"
        case lang
    }
}
