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
    ///   The method creates a copy to avoid mutating the provided encoder.
    ///   Always ensures `.sortedKeys` formatting is applied.
    /// - Returns: Encoded JSON data with sorted keys
    public func encodeSorted(using encoder: JSONEncoder? = nil) throws -> Data {
        let enc: JSONEncoder
        if let provided = encoder {
            enc = Self.makeEncoderCopy(provided)
            enc.outputFormatting.insert(.sortedKeys)
        } else {
            enc = JSONEncoder()
            enc.outputFormatting = [.sortedKeys]
        }
        return try enc.encode(self)
    }

    /// Encodes JSONValue to Data with pretty printing
    /// Useful for debugging and logging
    ///
    /// - Parameter encoder: Optional custom encoder for date/data strategies.
    ///   The method creates a copy to avoid mutating the provided encoder.
    ///   Always ensures `.prettyPrinted` formatting is applied.
    /// - Returns: Pretty-printed JSON data
    public func encodePretty(using encoder: JSONEncoder? = nil) throws -> Data {
        let enc: JSONEncoder
        if let provided = encoder {
            enc = Self.makeEncoderCopy(provided)
            enc.outputFormatting.insert(.prettyPrinted)
        } else {
            enc = JSONEncoder()
            enc.outputFormatting = [.prettyPrinted]
        }
        return try enc.encode(self)
    }

    /// Creates a copy of the encoder with all strategies preserved
    private static func makeEncoderCopy(_ existing: JSONEncoder) -> JSONEncoder {
        let copy = JSONEncoder()
        copy.outputFormatting = existing.outputFormatting
        copy.dateEncodingStrategy = existing.dateEncodingStrategy
        copy.dataEncodingStrategy = existing.dataEncodingStrategy
        copy.keyEncodingStrategy = existing.keyEncodingStrategy
        copy.userInfo = existing.userInfo
        return copy
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
