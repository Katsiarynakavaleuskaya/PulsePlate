import SwiftUI

struct ProfileView: View {
  var body: some View {
    Form {
      Section("Language") { Text("EN / RU / ES (later)") }
      Section("Legal") {
        Link("Privacy Policy", destination: URL(string:"https://example.com/privacy")!)
        Link("Terms of Use", destination: URL(string:"https://example.com/terms")!)
      }
    }
    .accessibilityLabel("Profile Screen")
  }
}
