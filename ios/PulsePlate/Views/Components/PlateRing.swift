import SwiftUI

struct PlateRing: View {
  let progress: Double
  @State private var animatedProgress: Double = 0

  // Clamp progress to valid range
  private var clampedProgress: Double {
    min(max(progress, 0), 1)
  }

  var body: some View {
    ZStack {
      // Background circle
      Circle()
        .stroke(Color.white.opacity(0.2), lineWidth: 8)
        .frame(width: 200, height: 200)

      // Progress ring
      Circle()
        .trim(from: 0, to: animatedProgress)
        .stroke(
          LinearGradient(
            colors: [.green, .blue, .purple],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
          ),
          style: StrokeStyle(lineWidth: 8, lineCap: .round)
        )
        .frame(width: 200, height: 200)
        .rotationEffect(.degrees(-90))

      // Center content
      VStack(spacing: 4) {
        Text(animatedProgress, format: .percent)
          .font(.title)
          .bold()
          .foregroundStyle(.white)
        Text(LocalizedStringKey("progress.complete"))
          .font(.caption)
          .foregroundStyle(.white.opacity(0.8))
      }
    }
    .onAppear {
      animatedProgress = clampedProgress
    }
    .onChange(of: clampedProgress) { _, newValue in
      withAnimation(.easeInOut(duration: 0.8)) {
        animatedProgress = newValue
      }
    }
    .accessibilityLabel(LocalizedStringKey("progress.label"))
    .accessibilityValue(Text(animatedProgress, format: .percent))
  }
}

#Preview {
  PlateRing(progress: 0.68)
    .background(Color.navy)
}
