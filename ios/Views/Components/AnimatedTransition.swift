import SwiftUI

// MARK: - Custom Animations
struct SlideInTransition: ViewModifier {
  let isActive: Bool
  let delay: Double

  func body(content: Content) -> some View {
    content
      .offset(x: isActive ? 0 : 300)
      .opacity(isActive ? 1 : 0)
      .animation(.spring(response: 0.6, dampingFraction: 0.8).delay(delay), value: isActive)
  }
}

struct ScaleTransition: ViewModifier {
  let isActive: Bool
  let scale: Double

  func body(content: Content) -> some View {
    content
      .scaleEffect(isActive ? scale : 1.0)
      .animation(.spring(response: 0.4, dampingFraction: 0.7), value: isActive)
  }
}

struct FadeTransition: ViewModifier {
  let isActive: Bool
  let delay: Double

  func body(content: Content) -> some View {
    content
      .opacity(isActive ? 1 : 0)
      .animation(.easeInOut(duration: 0.3).delay(delay), value: isActive)
  }
}

// MARK: - View Extensions
extension View {
  func slideIn(isActive: Bool, delay: Double = 0) -> some View {
    modifier(SlideInTransition(isActive: isActive, delay: delay))
  }

  func scaleOnAppear(isActive: Bool, scale: Double = 1.1) -> some View {
    modifier(ScaleTransition(isActive: isActive, scale: scale))
  }

  func fadeIn(isActive: Bool, delay: Double = 0) -> some View {
    modifier(FadeTransition(isActive: isActive, delay: delay))
  }
}

// MARK: - Animated Progress Ring
struct AnimatedProgressRing: View {
  let progress: Double
  let color: Color
  let lineWidth: CGFloat
  let size: CGFloat

  @State private var animatedProgress: Double = 0

  init(progress: Double, color: Color, lineWidth: CGFloat = 8, size: CGFloat = 200) {
    self.progress = progress
    self.color = color
    self.lineWidth = lineWidth
    self.size = size
  }

  var body: some View {
    ZStack {
      // Background circle
      Circle()
        .stroke(Color.white.opacity(0.2), lineWidth: lineWidth)
        .frame(width: size, height: size)

      // Progress ring
      Circle()
        .trim(from: 0, to: animatedProgress)
        .stroke(
          LinearGradient(
            colors: [color, color.opacity(0.7)],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
          ),
          style: StrokeStyle(lineWidth: lineWidth, lineCap: .round)
        )
        .frame(width: size, height: size)
        .rotationEffect(.degrees(-90))
        .animation(.easeInOut(duration: 1.0), value: animatedProgress)
    }
    .onAppear {
      withAnimation(.easeInOut(duration: 1.5)) {
        animatedProgress = progress
      }
    }
    .onChange(of: progress) { newValue in
      withAnimation(.easeInOut(duration: 0.8)) {
        animatedProgress = newValue
      }
    }
  }
}

// MARK: - Pulsing Animation
struct PulsingView: ViewModifier {
  let isActive: Bool
  let scale: Double
  @State private var animate = false

  func body(content: Content) -> some View {
    content
      .scaleEffect(animate ? scale : 1.0)
      .animation(
        .easeInOut(duration: 0.6)
        .repeatForever(autoreverses: true),
        value: animate
      )
      .onAppear {
        if isActive {
          animate = true
        }
      }
      .onChange(of: isActive) { newValue in
        animate = newValue
      }
  }
}

extension View {
  func pulsing(isActive: Bool, scale: Double = 1.05) -> some View {
    modifier(PulsingView(isActive: isActive, scale: scale))
  }
}

// MARK: - Shimmer Effect
struct ShimmerEffect: ViewModifier {
  @State private var phase: CGFloat = 0

  func body(content: Content) -> some View {
    content
      .overlay(
        Rectangle()
          .fill(
            LinearGradient(
              colors: [
                Color.white.opacity(0),
                Color.white.opacity(0.3),
                Color.white.opacity(0)
              ],
              startPoint: .leading,
              endPoint: .trailing
            )
          )
          .offset(x: phase)
          .animation(
            .linear(duration: 1.5)
            .repeatForever(autoreverses: false),
            value: phase
          )
      )
      .onAppear {
        phase = 200
      }
  }
}

extension View {
  func shimmer() -> some View {
    modifier(ShimmerEffect())
  }
}
