import Foundation

/// FastAPI validation error response (422).
///
/// Format: `{"detail": [{"type": "...", "loc": [...], "msg": "...", "input": ...}]}`
/// Note: `msg` is plain English (not i18n keys) per audit contract.
public struct ValidationErrorResponse: Decodable, Equatable, Sendable {
    public let detail: [ValidationErrorItem]
}

public struct ValidationErrorItem: Decodable, Equatable, Sendable {
    public let loc: [String]
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
