import Foundation

enum AppConfig {
    // MARK: - Release base URL validation

    /// Validates a raw string as a valid release base URL.
    ///
    /// Returns a valid `URL` only when all conditions are met:
    /// - The string is non-nil and non-empty.
    /// - The string can be parsed as a `URL`.
    /// - The scheme is `https`.
    /// - The host component is present and non-empty.
    ///
    /// Returns `nil` otherwise.
    static func validateReleaseBaseURL(_ raw: String?) -> URL? {
        guard let raw, !raw.isEmpty else { return nil }
        guard let url = URL(string: raw) else { return nil }
        guard url.scheme == "https" else { return nil }
        guard let host = url.host, !host.isEmpty else { return nil }
        return url
    }

    static func baseURL() -> URL {
        #if DEBUG
        // Development: Read from Info.plist first, then environment variables
        // Info-Debug.plist contains BASE_URL key
        if let infoPlistURL = Bundle.main.object(forInfoDictionaryKey: "BASE_URL") as? String,
           let url = URL(string: infoPlistURL) {
            return url
        }

        // Fallback: check environment variable (Xcode Scheme)
        if let envURL = ProcessInfo.processInfo.environment["BASE_URL"],
           let url = URL(string: envURL) {
            return url
        }

        // Final fallback: use 127.0.0.1 instead of localhost to avoid IPv6 issues
        return URL(string: "http://127.0.0.1:8000")!
        #else
        // Production: require explicit HTTPS BASE_URL from Info-Release.plist.
        // Silent fallback to a hardcoded host is forbidden (PR-7 fail-fast).
        // Operator decision: canonical_release_base_url = https://pulseplate.app
        let raw = Bundle.main.object(forInfoDictionaryKey: "BASE_URL") as? String
        guard let url = validateReleaseBaseURL(raw) else {
            fatalError(
                "Release BASE_URL is missing or invalid. "
                + "Info-Release.plist must contain a valid HTTPS BASE_URL. "
                + "Got: \(raw ?? "nil")"
            )
        }
        return url
        #endif
    }
}
