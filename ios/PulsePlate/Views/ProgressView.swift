import SwiftUI

struct ProgressViewPP: View {
  var body: some View {
    ScrollView {
      VStack(alignment: .leading, spacing: 16) {
        Text("Progress").font(.title).bold()
        Text("Charts coming…").foregroundStyle(.secondary)
      }.padding()
    }
    .accessibilityElement(children: .combine)
  }
}
