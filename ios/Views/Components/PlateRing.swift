import SwiftUI

/// RU: Простое кольцо тарелки с "пульсом".
/// EN: Simple plate ring with a subtle "pulse" animation.
struct PlateRing: View {
  @State private var pulse: Bool = false
  var progress: CGFloat = 0.68 // 0...1 — later bind to calories

  var body: some View {
    ZStack {
      // Base ring
      Circle()
        .stroke(Color.white.opacity(0.15), lineWidth: 16)

      // Progress (brand: Gold)
      Circle()
        .trim(from: 0, to: progress)
        .stroke(Color("Gold"), style: StrokeStyle(lineWidth: 16, lineCap: .round))
        .rotationEffect(.degrees(-90))
        .animation(.easeInOut(duration: 0.8), value: progress)

      // Pulsating rim
      Circle()
        .stroke(Color("Gold").opacity(pulse ? 0.25 : 0.05), lineWidth: pulse ? 28 : 20)
        .animation(.easeInOut(duration: 1.4).repeatForever(autoreverses: true), value: pulse)
        .onAppear { pulse = true }

      Text("\(Int(progress * 100))%")
        .font(.title2).bold()
        .foregroundStyle(.white)
        .accessibilityLabel("Daily plate progress \(Int(progress * 100)) percent")
    }
    .frame(height: 220)
  }
}
