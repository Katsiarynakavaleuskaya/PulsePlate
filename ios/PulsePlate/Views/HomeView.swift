import SwiftUI

struct HomeView: View {
  var body: some View {
    ScrollView {
      VStack(alignment: .leading, spacing: 16) {
        Text("My Plate").font(.title).bold()
        Text("Coming soon…").foregroundStyle(.secondary)
      }.padding()
    }
    .safeAreaInset(edge: .bottom) {
      Color.clear.frame(height: 80)
    }
    .accessibilityElement(children: .combine)
    .accessibilityLabel("Home Screen")
  }
}
