import Foundation

/// Component of FastAPI/Pydantic `loc` path.
/// Can be a string ("body", "field") or an int (array index).
public enum LocationComponent: Codable, Equatable, Sendable {
    case string(String)
    case int(Int)

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let i = try? container.decode(Int.self) {
            self = .int(i)
            return
        }
        if let s = try? container.decode(String.self) {
            self = .string(s)
            return
        }
        throw DecodingError.typeMismatch(
            LocationComponent.self,
            DecodingError.Context(codingPath: decoder.codingPath, debugDescription: "Expected String or Int for loc component")
        )
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .string(let s):
            try container.encode(s)
        case .int(let i):
            try container.encode(i)
        }
    }
}

/// FastAPI validation error response (422).
///
/// Format: `{"detail": [{"type": "...", "loc": [...], "msg": "...", "input": ...}]}`
/// Note: `msg` is plain English (not i18n keys) per audit contract.
public struct ValidationErrorResponse: Decodable, Equatable, Sendable {
    public let detail: [ValidationErrorItem]
}

public struct ValidationErrorItem: Decodable, Equatable, Sendable {
    public let loc: [LocationComponent]
    public let msg: String
    public let type: String
    // Note: `input` field may be present but we don't decode it (not needed for client)
}

/// Simple error response (400/500/501).
///
/// Format: `{"detail": "localized error message"}`
/// Note: `detail` is localized text via backend `t(lang, key)` per audit contract.
public struct SimpleErrorResponse: Decodable, Equatable, Sendable {
    public let detail: String
}
