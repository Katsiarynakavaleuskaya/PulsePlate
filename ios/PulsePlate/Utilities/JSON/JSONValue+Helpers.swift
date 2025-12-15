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
    /// - Parameter encoder: Optional custom encoder. If nil, creates one with `.sortedKeys`.
    ///   Pass your own encoder to control date/data strategies or custom formatting.
    /// - Returns: Encoded JSON data
    public func encodeSorted(using encoder: JSONEncoder? = nil) throws -> Data {
        if let encoder {
            return try encoder.encode(self)
        }
        let enc = JSONEncoder()
        enc.outputFormatting = [.sortedKeys]
        return try enc.encode(self)
    }

    /// Encodes JSONValue to Data with pretty printing
    /// Useful for debugging and logging
    ///
    /// - Parameter encoder: Optional custom encoder. If nil, creates one with `.prettyPrinted + .sortedKeys`.
    ///   Pass your own encoder to control date/data strategies or custom formatting.
    /// - Returns: Pretty-printed JSON data
    public func encodePretty(using encoder: JSONEncoder? = nil) throws -> Data {
        if let encoder {
            return try encoder.encode(self)
        }
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
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
