import Foundation
import SwiftUI
import Combine

class LocalizationManager: ObservableObject {
    static let shared = LocalizationManager()
    @Published var currentLanguage: String {
        didSet {
            UserDefaults.standard.set(currentLanguage, forKey: AppStorageKeys.appLanguage)
            // Force UI update
            objectWillChange.send()
        }
    }
    let supportedLanguages = ["en", "ru", "es"]

    private init() {
        let saved = UserDefaults.standard.string(forKey: AppStorageKeys.appLanguage)
        currentLanguage = saved ?? Locale.current.language.languageCode?.identifier ?? "en"
    }

    func localized(_ key: String) -> String {
        let lang = currentLanguage
        let path = Bundle.main.path(forResource: lang, ofType: "lproj") ?? Bundle.main.path(forResource: "en", ofType: "lproj")!
        let bundle = Bundle(path: path)!
        return NSLocalizedString(key, bundle: bundle, comment: "")
    }
}
