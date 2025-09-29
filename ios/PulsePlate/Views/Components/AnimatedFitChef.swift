import SwiftUI

/// RU: Анимированный маскот FitChef с 4 кадрами.
/// EN: Animated FitChef mascot with 4 frames.
struct AnimatedFitChef: View {
    @State private var currentFrame = 0
    @State private var animationTimer: Timer?

    let frames = [
        "fitchef_frame1",
        "fitchef_frame2",
        "fitchef_frame3",
        "fitchef_frame4"
    ]

    let frameDuration: Double = 0.5 // 0.5 секунды на кадр

    var body: some View {
        Image(frames[currentFrame])
            .resizable()
            .scaledToFit()
            .onAppear {
                startAnimation()
            }
            .onDisappear {
                stopAnimation()
            }
    }

    private func startAnimation() {
        animationTimer = Timer.scheduledTimer(withTimeInterval: frameDuration, repeats: true) { _ in
            withAnimation(.easeInOut(duration: 0.2)) {
                currentFrame = (currentFrame + 1) % frames.count
            }
        }
    }

    private func stopAnimation() {
        animationTimer?.invalidate()
        animationTimer = nil
    }
}

/// RU: Анимированное облачко маскота с локализуемой репликой.
/// EN: Animated mascot speech bubble with localized line.
struct AnimatedMascotBubble: View {
    var textKey: LocalizedStringKey

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            AnimatedFitChef()
                .frame(width: 48, height: 48)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: 6) {
                Text(textKey)
                    .foregroundStyle(.white)
                    .font(.body)

                Text("FitChef")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.7))
            }
            .padding(12)
            .background(Color.white.opacity(0.08))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(Color.white.opacity(0.12), lineWidth: 1)
            )
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(Text("FitChef, ") + Text(textKey))
    }
}

#Preview {
    VStack(spacing: 20) {
        AnimatedFitChef()
            .frame(width: 100, height: 100)

        AnimatedMascotBubble(textKey: "Добро пожаловать в PulsePlate!")
            .padding()
    }
    .background(.navy)
}
