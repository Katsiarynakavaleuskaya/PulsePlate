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
    ///
    /// - Parameter encoder: Optional custom encoder for date/data strategies.
    ///   The method always ensures `.sortedKeys` formatting is applied.
    /// - Returns: Encoded JSON data with sorted keys
    public func encodeSorted(using encoder: JSONEncoder? = nil) throws -> Data {
        let enc = encoder ?? JSONEncoder()
        enc.outputFormatting.insert(.sortedKeys)
        return try enc.encode(self)
    }

    /// Encodes JSONValue to Data with pretty printing
    /// Useful for debugging and logging
    ///
    /// - Parameter encoder: Optional custom encoder for date/data strategies.
    ///   The method always ensures `.prettyPrinted` formatting is applied.
    /// - Returns: Pretty-printed JSON data
    public func encodePretty(using encoder: JSONEncoder? = nil) throws -> Data {
        let enc = encoder ?? JSONEncoder()
        enc.outputFormatting.insert(.prettyPrinted)
        return try enc.encode(self)
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
