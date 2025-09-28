import SwiftUI

struct LanguagePickerView: View {
    @ObservedObject var localization = LocalizationManager.shared
    let supportedLanguages = ["en", "ru", "es"]
    var body: some View {
        Form {
            Picker(localization.localized("language_settings"), selection: $localization.currentLanguage) {
                ForEach(supportedLanguages, id: \.self) { code in
                    Text(localization.localized("language_name_\(code)"))
                        .tag(code)
                }
            }
            .pickerStyle(.segmented)
        }
        .navigationTitle(localization.localized("language_settings"))
    }
}
