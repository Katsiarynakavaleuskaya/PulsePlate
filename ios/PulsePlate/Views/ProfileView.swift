import SwiftUI

struct ProfileView: View {
    @ObservedObject var localization = LocalizationManager.shared
    @State private var showAnimationTest = false
    @State private var showBundleTest = false

    var body: some View {
        NavigationStack {
            Form {
                Section(header: Text(localization.localized("profile_language_section"))) {
                    Text(localization.localized("profile_language_value"))
                }
                Section(header: Text("Animation Test")) {
                    Button("Test MP4 Animation") {
                        showAnimationTest = true
                    }
                    Button("Test Bundle Files") {
                        showBundleTest = true
                    }
                    Button("Test Lottie Animation") {
                        // TODO: Add Lottie test
                    }
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
            .navigationTitle("Profile")
            .sheet(isPresented: $showAnimationTest) {
                SimpleVideoTest()
            }
            .sheet(isPresented: $showBundleTest) {
                BundleTestView()
            }
            .accessibilityLabel(localization.localized("profile_screen_accessibility_label"))
        }
    }
}
