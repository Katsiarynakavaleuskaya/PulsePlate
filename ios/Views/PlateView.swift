import SwiftUI

struct PlateViewPP: View {
  var body: some View {
    VStack(alignment: .leading, spacing: 16) {
      Text("Plate").font(.title).bold()
      Text("SVG ring / Canvas later").foregroundStyle(.secondary)
    }.padding()
    .accessibilityLabel("Plate Screen")
  }
}
