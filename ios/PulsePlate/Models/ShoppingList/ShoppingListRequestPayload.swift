import Foundation

/// Encodable request payload for Shopping List API
/// Represents the typed structure sent to POST /api/v1/pro/meal/shopping-list
public struct ShoppingListRequestPayload: Encodable {
    public let planData: ShoppingPlan
    public let preferences: [String: Any]?

    public init(planData: ShoppingPlan, preferences: [String: Any]? = nil) {
        self.planData = planData
        self.preferences = preferences
    }

    enum CodingKeys: String, CodingKey {
        case planData = "plan_data"
        case preferences
    }

    // Manual encoding to support [String: Any] for preferences
    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(planData, forKey: .planData)

        if let preferences {
            // Encode as untyped JSON dictionary
            let prefsData = try JSONSerialization.data(withJSONObject: preferences)
            let prefsDecoded = try JSONDecoder().decode(ShoppingListAnyCodable.self, from: prefsData)
            try container.encode(prefsDecoded, forKey: .preferences)
        }
    }
}

// Helper for encoding untyped dictionaries
// NOTE: Intentionally local to ShoppingList to avoid name clashes.
private struct ShoppingListAnyCodable: Codable {
    let value: Any

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let dict = try? container.decode([String: ShoppingListAnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else if let array = try? container.decode([ShoppingListAnyCodable].self) {
            value = array.map { $0.value }
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let dict = value as? [String: Any] {
            try container.encode(dict.mapValues { ShoppingListAnyCodable(value: $0) } as [String: ShoppingListAnyCodable])
        } else if let array = value as? [Any] {
            try container.encode(array.map { ShoppingListAnyCodable(value: $0) } as [ShoppingListAnyCodable])
        } else if let string = value as? String {
            try container.encode(string)
        } else if let bool = value as? Bool {
            try container.encode(bool)
        } else if let int = value as? Int {
            try container.encode(int)
        } else if let double = value as? Double {
            try container.encode(double)
        } else {
            try container.encodeNil()
        }
    }

    private init(value: Any) {
        self.value = value
    }
}
