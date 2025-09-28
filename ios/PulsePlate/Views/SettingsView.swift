import SwiftUI

struct SettingsView: View {
    @ObservedObject var localization = LocalizationManager.shared

    var body: some View {
        NavigationView {
            List {
                NavigationLink(destination: LanguagePickerView()) {
                    Text(localization.localized("language_settings"))
                }
            }
            .navigationTitle(localization.localized("settings_title"))
        }
    }
}
