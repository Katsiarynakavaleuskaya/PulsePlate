import SwiftUI
import Lottie

/// RU: Компонент для Lottie анимаций FitChef
/// EN: Component for FitChef Lottie animations
struct LottieAnimationView: View {
    let animationName: String
    @State private var animation: LottieAnimation?
    @State private var isPlaying = false

    var body: some View {
        Group {
            if let animation = animation {
                LottieView(animation: animation)
                    .playing(loopMode: .loop)
                    .onAppear {
                        isPlaying = true
                    }
                    .onDisappear {
                        isPlaying = false
                    }
            } else {
                // Fallback image if animation fails to load
                Image("FitChef")
                    .resizable()
                    .scaledToFit()
            }
        }
        .onAppear {
            loadAnimation()
        }
        .onChange(of: animationName) { _ in
            loadAnimation()
        }
    }

    private func loadAnimation() {
        do {
            animation = try LottieAnimation.from(named: animationName)
            print("✅ Lottie animation loaded: \(animationName)")
        } catch {
            print("❌ Failed to load Lottie animation: \(animationName) - \(error)")
            animation = nil
        }
    }
}

/// RU: Анимированный FitChef с Lottie анимацией
/// EN: Animated FitChef with Lottie animation
struct AnimatedFitChefLottie: View {
    @State private var currentAnimation = 0
    @State private var animationTimer: Timer?

    private let animations = [
        "fitchef_blink",      // Моргание
        "fitchef_wave",       // Махание лапкой
        "fitchef_heartbeat",  // Слежение за пульсом
        "fitchef_idle"        // Простая анимация
    ]

    var body: some View {
        LottieAnimationView(animationName: animations[currentAnimation])
            .onAppear {
                startAnimation()
            }
            .onDisappear {
                stopAnimation()
            }
    }

    private func startAnimation() {
        // Stop any existing timer first
        stopAnimation()

        animationTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { _ in
            withAnimation(.easeInOut(duration: 0.3)) {
                currentAnimation = (currentAnimation + 1) % animations.count
            }
        }
    }

    private func stopAnimation() {
        animationTimer?.invalidate()
        animationTimer = nil
    }
}

/// RU: Анимированное облачко с Lottie FitChef
/// EN: Animated speech bubble with Lottie FitChef
struct AnimatedMascotBubbleLottie: View {
    var textKey: LocalizedStringKey
    @State private var showAnimation = false

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            if showAnimation {
                AnimatedFitChefLottie()
                    .frame(width: 48, height: 48)
                    .clipShape(Circle())
                    .accessibilityHidden(true)
            } else {
                Image("FitChef")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 48, height: 48)
                    .clipShape(Circle())
                    .accessibilityHidden(true)
            }

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
        .onAppear {
            // Show animation after a short delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                withAnimation(.easeInOut(duration: 0.3)) {
                    showAnimation = true
                }
            }
        }
    }
}

/// RU: Тестовый экран для Lottie анимаций
/// EN: Test screen for Lottie animations
struct LottieTestView: View {
    @State private var currentAnimation = 0

    private let animations = [
        "fitchef_blink",
        "fitchef_wave",
        "fitchef_heartbeat",
        "fitchef_idle"
    ]

    var body: some View {
        VStack(spacing: 20) {
            Text("Lottie Animation Test")
                .font(.title)
                .bold()
                .foregroundStyle(.white)

            // Animation Player
            LottieAnimationView(animationName: animations[currentAnimation])
                .frame(width: 200, height: 200)
                .clipShape(RoundedRectangle(cornerRadius: 20))

            // Controls
            HStack(spacing: 20) {
                Button("Previous") {
                    currentAnimation = (currentAnimation - 1 + animations.count) % animations.count
                }
                .buttonStyle(.bordered)
                .foregroundStyle(.white)

                Button("Next") {
                    currentAnimation = (currentAnimation + 1) % animations.count
                }
                .buttonStyle(.bordered)
                .foregroundStyle(.white)
            }

            // Animation Info
            VStack(alignment: .leading, spacing: 8) {
                Text("Current Animation: \(currentAnimation + 1)/\(animations.count)")
                    .font(.headline)
                    .foregroundStyle(.white)

                Text("File: \(animations[currentAnimation])")
                    .font(.caption)
                    .foregroundStyle(.gray)
            }
            .padding()
            .background(Color.white.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 12))

            Spacer()
        }
        .padding()
        .background(.navy)
        .navigationTitle("Lottie Test")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    VStack(spacing: 20) {
        LottieAnimationView(animationName: "fitchef_blink")
            .frame(width: 100, height: 100)

        AnimatedMascotBubbleLottie(textKey: "Добро пожаловать в PulsePlate!")
            .padding()
    }
    .background(.navy)
}
