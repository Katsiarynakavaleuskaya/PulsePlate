import SwiftUI

struct ProfileView: View {
  var body: some View {
    Form {
      Section("Language") { Text("EN / RU / ES (later)") }
      Section("Legal") {
        if let privacyURL = URL(string: "https://pulseplate.app/privacy") {
          Link("Privacy Policy", destination: privacyURL)
        }
        if let termsURL = URL(string: "https://pulseplate.app/terms") {
          Link("Terms of Use", destination: termsURL)
        }
      }
    }
    .accessibilityLabel("Profile Screen")
  }
}
