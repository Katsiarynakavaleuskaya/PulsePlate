import SwiftUI

struct ProfileView: View {
    @ObservedObject var localization = LocalizationManager.shared
    var body: some View {
        Form {
            Section(header: Text(localization.localized("profile_language_section"))) {
                Text(localization.localized("profile_language_value"))
            }
            Section(header: Text(localization.localized("profile_legal_section"))) {
                if let privacyURL = URL(string: "https://pulseplate.app/privacy") {
                    Link(localization.localized("profile_privacy_policy"), destination: privacyURL)
                }
                if let termsURL = URL(string: "https://pulseplate.app/terms") {
                    Link(localization.localized("profile_terms_of_use"), destination: termsURL)
                }
            }
        }
        .accessibilityLabel(localization.localized("profile_screen_accessibility_label"))
    }
}
