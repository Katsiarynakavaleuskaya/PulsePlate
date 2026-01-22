import Foundation

/// Waist-to-height risk result.
///
/// Backend schema: `app/schemas/bmi.py::WaistRiskResultSchema` (lines 87-107)
/// Source of truth: audit-док section 1.1 Response Schema
public struct WaistRiskDTO: Decodable, Sendable {

    public let whtRatio: Double?
    public let riskLevel: String
    public let notes: [String]

    enum CodingKeys: String, CodingKey {
        case whtRatio = "wht_ratio"
        case riskLevel = "risk_level"
        case notes
    }
}
