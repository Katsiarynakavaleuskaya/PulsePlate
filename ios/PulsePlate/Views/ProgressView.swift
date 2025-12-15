import SwiftUI

struct ProgressViewPP: View {
  var body: some View {
    ScrollView {
      VStack(alignment: .leading, spacing: 16) {
        Text("Progress").font(.title).bold()
        Text("Charts coming…").foregroundStyle(.secondary)
      }.padding()
    }
    .safeAreaInset(edge: .bottom) {
      Color.clear.frame(height: 80)
    }
    .accessibilityElement(children: .combine)
  }
}
