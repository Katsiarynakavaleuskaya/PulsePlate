import Foundation

enum AppConfig {
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
        // Production: Read from Info-Release.plist
        if let infoPlistURL = Bundle.main.object(forInfoDictionaryKey: "BASE_URL") as? String,
           let url = URL(string: infoPlistURL) {
            return url
        }

        // Fallback production URL if not configured
        guard let url = URL(string: "https://api.pulseplate.com") else {
            fatalError("Invalid production BASE_URL")
        }
        return url
        #endif
    }
}
