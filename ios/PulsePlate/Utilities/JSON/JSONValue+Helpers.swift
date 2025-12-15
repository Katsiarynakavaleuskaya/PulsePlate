import Foundation

// MARK: - JSONValue Factory Methods
extension JSONValue {
    /// Creates an empty JSON object
    public static func emptyObject() -> JSONValue {
        .object([:])
    }

    /// Creates an empty JSON array
    public static func emptyArray() -> JSONValue {
        .array([])
    }
}

// MARK: - JSONValue Encoding Helpers
extension JSONValue {
    /// Encodes JSONValue to Data with sorted keys
    /// Useful for stable request body encoding
    public func encodeSorted() throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(self)
    }

    /// Encodes JSONValue to Data with pretty printing
    /// Useful for debugging and logging
    public func encodePretty() throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(self)
    }
}

// MARK: - JSONValue Subscripts
extension JSONValue {
    /// Safe subscript for object access (returns nil for missing keys)
    public subscript(key: String) -> JSONValue? {
        objectValue?[key]
    }

    /// Safe subscript for array access (returns nil for out-of-bounds)
    public subscript(index: Int) -> JSONValue? {
        guard let arr = arrayValue, arr.indices.contains(index) else {
            return nil
        }
        return arr[index]
    }
}
