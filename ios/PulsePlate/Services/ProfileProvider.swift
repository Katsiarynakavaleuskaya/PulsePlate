import Foundation

enum AppStorageKeys {
    static let appLanguage = "AppLanguage"
}

// MARK: - PRO Nutrition Profile (Plate /daily)
//
// RU: Единый источник query-параметров профиля для PRO endpoints (Plate).
// EN: Single source of truth for profile query params used by PRO endpoints (Plate).

public enum ProProfileSex: String, CaseIterable, Identifiable, Sendable {
    case female
    case male

    public var id: String { rawValue }
}

public enum ProProfileActivity: String, CaseIterable, Identifiable, Sendable {
    case sedentary
    case light
    case moderate
    case active
    case veryActive = "very_active"

    public var id: String { rawValue }
}

public enum ProProfileGoal: String, CaseIterable, Identifiable, Sendable {
    case loss
    case maintain
    case gain

    public var id: String { rawValue }
}

public struct ProNutritionProfile: Sendable, Equatable {
    public let sex: ProProfileSex
    public let age: Int
    public let heightCm: Int
    public let weightKg: Int
    public let activity: ProProfileActivity
    public let goal: ProProfileGoal
}

public protocol ProfileProviding: Sendable {
    /// RU: Возвращает профиль только если заполнены обязательные поля.
    /// EN: Returns a profile only if required fields are present/valid.
    func proNutritionProfile() -> ProNutritionProfile?

    /// RU: Язык UI для query `lang` (совпадает с выбором языка в приложении).
    /// EN: UI language code for query `lang` (matches app language selection).
    func languageCode() -> String
}

public struct DefaultProfileProvider: ProfileProviding, Sendable {
    private enum Keys {
        static let sex = "pro_profile_sex"
        static let age = "pro_profile_age"
        static let heightCm = "pro_profile_height_cm"
        static let weightKg = "pro_profile_weight_kg"
        static let activity = "pro_profile_activity"
        static let goal = "pro_profile_goal"

    }

    private let userDefaults: UserDefaults

    public init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
    }

    public func languageCode() -> String {
        let raw = (userDefaults.string(forKey: AppStorageKeys.appLanguage) ?? "en").lowercased()
        // Backend currently supports these language codes.
        switch raw {
        case "en", "ru", "es":
            return raw
        default:
            return "en"
        }
    }

    public func proNutritionProfile() -> ProNutritionProfile? {
        guard
            let sex = ProProfileSex(rawValue: _string(Keys.sex)),
            let age = _int(Keys.age),
            let height = _int(Keys.heightCm),
            let weight = _int(Keys.weightKg)
        else {
            return nil
        }

        // Optional fields have backend defaults; we still send them deterministically.
        let activity = ProProfileActivity(rawValue: _string(Keys.activity)) ?? .moderate
        let goal = ProProfileGoal(rawValue: _string(Keys.goal)) ?? .maintain

        return ProNutritionProfile(
            sex: sex,
            age: age,
            heightCm: height,
            weightKg: weight,
            activity: activity,
            goal: goal
        )
    }

    private func _string(_ key: String) -> String {
        (userDefaults.string(forKey: key) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func _int(_ key: String) -> Int? {
        let s = _string(key)
        guard !s.isEmpty, let i = Int(s), i > 0 else { return nil }
        return i
    }
}
