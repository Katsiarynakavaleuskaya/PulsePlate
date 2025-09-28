import SwiftUI

struct PlateViewPP: View {
  var body: some View {
    VStack(spacing: 16) {
      Text("Plate").font(.title).bold().foregroundStyle(.white)
      PlateRing(progress: 0.68)
      MascotBubble(textKey: "mascot.plate.hint")
    }
    .padding()
    .background(Color("Navy"))
  }
}
