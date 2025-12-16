import Foundation

enum ProKeyProvider {
    static func value() -> String? {
        // For SPM projects: use ProcessInfo environment variables
        // Set via Xcode Scheme → Run → Environment Variables
        // Example: PRO_API_KEY = test_pro_key

        #if DEBUG
        // Development: check environment variable first
        if let envKey = ProcessInfo.processInfo.environment["PRO_API_KEY"],
           !envKey.isEmpty {
            return envKey
        }
        // Fallback for local testing
        return "test_pro_key"
        #else
        // Production: retrieve from Keychain or secure storage
        // TODO: Implement Keychain retrieval
        return nil
        #endif
    }
}
