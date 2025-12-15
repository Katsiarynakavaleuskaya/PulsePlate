import Foundation

/// Convenient helpers for JSONValue to simplify common operations
public extension JSONValue {
    /// Extract object dictionary if this is an object case
    var objectValue: [String: JSONValue]? {
        if case .object(let o) = self { return o }
        return nil
    }

    /// Extract string if this is a string case
    var stringValue: String? {
        if case .string(let s) = self { return s }
        return nil
    }

    /// Extract number if this is a number case
    var numberValue: Double? {
        if case .number(let n) = self { return n }
        return nil
    }

    /// Extract array if this is an array case
    var arrayValue: [JSONValue]? {
        if case .array(let a) = self { return a }
        return nil
    }

    /// Extract boolean if this is a boolean case
    var boolValue: Bool? {
        if case .bool(let b) = self { return b }
        return nil
    }

    /// Check if this is a null case
    var isNull: Bool {
        if case .null = self { return true }
        return false
    }

    /// Create an empty object
    static func emptyObject() -> JSONValue {
        .object([:])
    }

    /// Create an empty array
    static func emptyArray() -> JSONValue {
        .array([])
    }

    /// Stable JSON encoding for request bodies (sorted keys)
    /// - Throws: EncodingError if encoding fails
    /// - Returns: Encoded JSON data
    func encodeSorted() throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(self)
    }

    /// Pretty-printed JSON encoding for debugging
    /// - Throws: EncodingError if encoding fails
    /// - Returns: Pretty-printed JSON data
    func encodePretty() throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(self)
    }

    /// Subscript access for object keys (returns nil if not an object or key doesn't exist)
    subscript(key: String) -> JSONValue? {
        objectValue?[key]
    }

    /// Subscript access for array indices (returns nil if not an array or index out of bounds)
    subscript(index: Int) -> JSONValue? {
        guard let array = arrayValue, array.indices.contains(index) else {
            return nil
        }
        return array[index]
    }
}
