import Foundation

enum AppConfig {
    static func baseURL() -> URL {
        // SPM projects: use ProcessInfo for environment-based config
        // For dev: set via Xcode scheme environment variables
        // For prod: hardcode or use config file

        #if DEBUG
        // Development: local backend
        // Set BASE_URL in Xcode Scheme → Run → Environment Variables
        // Example: BASE_URL = http://127.0.0.1:8000
        if let envURL = ProcessInfo.processInfo.environment["BASE_URL"],
           let url = URL(string: envURL) {
            return url
        }
        // Fallback: use 127.0.0.1 instead of localhost to avoid IPv6 issues
        return URL(string: "http://127.0.0.1:8000")!
        #else
        // Production: hardcode or load from config
        guard let url = URL(string: "https://api.pulseplate.com") else {
            fatalError("Invalid production BASE_URL")
        }
        return url
        #endif
    }
}
