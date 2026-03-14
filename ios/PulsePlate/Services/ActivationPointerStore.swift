import Foundation

protocol ActivationPointerStoring {
    func loadActivationID() -> String?
    func saveActivationID(_ id: String)
    func clearActivationID()
}

final class UserDefaultsActivationPointerStore: ActivationPointerStoring {
    private let userDefaults: UserDefaults
    private let activationIDKey: String

    init(
        userDefaults: UserDefaults = .standard,
        activationIDKey: String = "subscription.last_activation_id"
    ) {
        self.userDefaults = userDefaults
        self.activationIDKey = activationIDKey
    }

    func loadActivationID() -> String? {
        userDefaults.string(forKey: activationIDKey)
    }

    func saveActivationID(_ id: String) {
        userDefaults.set(id, forKey: activationIDKey)
    }

    func clearActivationID() {
        userDefaults.removeObject(forKey: activationIDKey)
    }
}
