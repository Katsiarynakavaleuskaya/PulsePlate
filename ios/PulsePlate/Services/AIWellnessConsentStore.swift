import Foundation

// MARK: - AI Wellness Consent Protocol

/// Provides consent state for AI wellness insight features.
///
/// The app must obtain explicit user consent before sending any free-text
/// query to the AI/CBT insight backend. Consent stores only a boolean
/// acceptance flag and an optional version string — no user free text,
/// no query content, and no medical data.
protocol AIWellnessConsentProviding: Sendable {
    func hasAccepted() -> Bool
    func markAccepted()
}

// MARK: - UserDefaults-backed Implementation

/// Stores AI wellness consent acceptance as a local boolean in UserDefaults.
///
/// - Key: `ai_wellness_consent_accepted_v1` (versioned for future re-prompt).
/// - Value: `Bool` (`false` by default — consent is not pre-accepted).
/// - No user free text, query content, or medical data is stored.
final class AIWellnessConsentStore: AIWellnessConsentProviding, @unchecked Sendable {
    // Single-threaded by design; UserDefaults is thread-safe per Apple docs.

    static let key = AppStorageKeys.aiWellnessConsentAccepted

    private let userDefaults: UserDefaults

    init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
    }

    func hasAccepted() -> Bool {
        userDefaults.bool(forKey: Self.key)
    }

    func markAccepted() {
        userDefaults.set(true, forKey: Self.key)
    }
}
