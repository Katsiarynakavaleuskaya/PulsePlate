import SwiftUI

struct HomeView: View {
  var body: some View {
    ScrollView {
      VStack(alignment: .leading, spacing: 16) {
        Text("My Plate").font(.title).bold()
        Text("Coming soon…").foregroundStyle(.secondary)
      }.padding()
    }
    .accessibilityElement(children: .contain)
    .accessibilityLabel(Text("Home Screen"))
  }
}
