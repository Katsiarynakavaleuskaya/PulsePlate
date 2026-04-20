import Foundation

enum ProKeyProvider {
    private static let account = "pro_api_key"
    private static let store = KeychainStore(service: "com.pulseplate.pro-key")

    static func value() -> String? {
        // RU: Runtime-источник секрета только Keychain.
        // EN: Keychain is the only runtime secret source.
        do {
            return try store.getString(account: account)
        } catch {
            #if DEBUG
            assertionFailure("Keychain error while reading PRO key: \(error)")
            #endif
            return nil
        }
    }

    static func set(value: String) throws {
        try store.setString(value, account: account)
    }

    static func clear() throws {
        try store.delete(account: account)
    }
}
