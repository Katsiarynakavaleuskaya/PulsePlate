import SwiftUI

struct LanguagePickerView: View {
    @ObservedObject var localization = LocalizationManager.shared
    var body: some View {
        Form {
            Picker(localization.localized("language_settings"), selection: $localization.currentLanguage) {
                Text("English").tag("en")
                Text("Русский").tag("ru")
                Text("Español").tag("es")
            }
            .pickerStyle(.segmented)
        }
        .navigationTitle(localization.localized("language_settings"))
    }
}
