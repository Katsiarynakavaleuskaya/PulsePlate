import Foundation

enum ProKeyProvider {
    private static let account = "pro_api_key"
    private static let store = KeychainStore(service: "com.pulseplate.pro-key")

    static func value() -> String? {
        // For SPM projects: use ProcessInfo environment variables
        // Set via Xcode Scheme → Run → Environment Variables
        // Example: PRO_API_KEY = <your_pro_key>

        #if DEBUG
        // Development: check environment variable first
        if let envKey = ProcessInfo.processInfo.environment["PRO_API_KEY"],
           !envKey.isEmpty {
            return envKey
        }
        #endif

        // Production-safe: retrieve from Keychain.
        // RU: В релизе никаких fallback ключей быть не должно.
        return (try? store.getString(account: account)) ?? nil
    }

    static func set(value: String) throws {
        try store.setString(value, account: account)
    }

    static func clear() throws {
        try store.delete(account: account)
    }
}
