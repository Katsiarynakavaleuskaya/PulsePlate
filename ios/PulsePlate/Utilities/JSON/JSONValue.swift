import Foundation

/// Type-safe wrapper for dynamic JSON values from backend
/// Prevents crashes when API contract changes or returns unexpected data
public enum JSONValue: Codable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if container.decodeNil() {
            self = .null
            return
        }

        if let value = try? container.decode(Bool.self) {
            self = .bool(value)
            return
        }

        if let value = try? container.decode(Double.self) {
            self = .number(value)
            return
        }

        if let value = try? container.decode(String.self) {
            self = .string(value)
            return
        }

        if let value = try? container.decode([String: JSONValue].self) {
            self = .object(value)
            return
        }

        if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
            return
        }

        self = .null
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch self {
        case .null:
            try container.encodeNil()
        case .bool(let value):
            try container.encode(value)
        case .number(let value):
            try container.encode(value)
        case .string(let value):
            try container.encode(value)
        case .object(let value):
            try container.encode(value)
        case .array(let value):
            try container.encode(value)
        }
    }
}

// MARK: - Convenience Accessors
extension JSONValue {
    var objectValue: [String: JSONValue]? {
        if case .object(let dict) = self { return dict }
        return nil
    }

    var arrayValue: [JSONValue]? {
        if case .array(let arr) = self { return arr }
        return nil
    }

    var stringValue: String? {
        if case .string(let str) = self { return str }
        return nil
    }

    var doubleValue: Double? {
        switch self {
        case .number(let num):
            return num
        case .string(let str):
            // Support both dot and comma as decimal separator (EU locales)
            let normalized = str.replacingOccurrences(of: ",", with: ".")
            return Double(normalized)
        default:
            return nil
        }
    }

    var intRounded: Int? {
        guard let d = doubleValue else { return nil }
        return Int(d.rounded())
    }

    var boolValue: Bool? {
        if case .bool(let value) = self { return value }
        return nil
    }
}
