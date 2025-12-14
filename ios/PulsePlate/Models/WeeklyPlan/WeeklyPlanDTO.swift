import Foundation

/// Raw API response from POST /api/v1/pro/meal/weekly
/// Uses JSONValue for flexible parsing to prevent crashes on contract changes
public struct WeeklyPlanDTO: Decodable, Sendable {
    public let root: JSONValue

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        self.root = try container.decode(JSONValue.self)
    }

    // For testing: allow direct initialization with JSONValue
    public init(root: JSONValue) {
        self.root = root
    }
}
