import SwiftUI

struct PlateRing: View {
  let progress: Double
  @State private var animatedProgress: Double = 0

  private var clampedProgress: Double {
    max(0, min(progress, 1))
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
        .animation(.easeInOut(duration: 1.5), value: animatedProgress)

      // Center content
      VStack(spacing: 4) {
        Text("\(Int(clampedProgress * 100))%")
          .font(.title)
          .bold()
          .foregroundStyle(.white)
        Text("Complete")
          .font(.caption)
          .foregroundStyle(.white.opacity(0.8))
      }
    }
    .onAppear {
      animatedProgress = clampedProgress
    }
    .onChange(of: progress) { newValue in
      withAnimation(.easeInOut(duration: 0.8)) {
        animatedProgress = clampedProgress
      }
    }
    .accessibilityLabel("Nutrition progress: \(Int(clampedProgress * 100)) percent complete")
  }
}

#Preview {
  PlateRing(progress: 0.68)
    .background(Color("Navy"))
}
