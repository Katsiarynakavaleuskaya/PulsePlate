import SwiftUI
import Lottie

enum FitChefLottieAsset: String, CaseIterable {
    case blink = "fitchef_blink"
}

enum FitChefLottiePlaybackPolicy: Equatable {
    case animated
    case staticFallback(FitChefLottieFallbackReason)

    static func resolve(reduceMotion: Bool, animationLoaded: Bool) -> Self {
        if reduceMotion {
            return .staticFallback(.reduceMotion)
        }
        guard animationLoaded else {
            return .staticFallback(.assetUnavailable)
        }
        return .animated
    }

    var statusText: String {
        switch self {
        case .animated:
            return "Animated"
        case .staticFallback(.reduceMotion):
            return "Static image: Reduce Motion is enabled"
        case .staticFallback(.assetUnavailable):
            return "Static image: animation unavailable"
        }
    }
}

enum FitChefLottieFallbackReason: Equatable {
    case reduceMotion
    case assetUnavailable
}

/// RU: Компонент для Lottie анимаций FitChef
/// EN: Component for FitChef Lottie animations
struct LottieAnimationView: View {
    let asset: FitChefLottieAsset
    var showsPlaybackStatus = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    private let animation: LottieAnimation?

    init(asset: FitChefLottieAsset, showsPlaybackStatus: Bool = false) {
        self.asset = asset
        self.showsPlaybackStatus = showsPlaybackStatus
        animation = LottieAnimation.named(asset.rawValue, bundle: .main)
    }

    var body: some View {
        VStack(spacing: 8) {
            Group {
                if playbackPolicy == .animated, let animation {
                    LottieView(animation: animation)
                        .playing(loopMode: .loop)
                } else {
                    Image("FitChef")
                        .resizable()
                        .scaledToFit()
                }
            }
            .accessibilityLabel("FitChef blink animation")
            .accessibilityValue(playbackPolicy.statusText)

            if showsPlaybackStatus {
                Text(playbackPolicy.statusText)
                    .font(.caption)
                    .foregroundStyle(.gray)
            }
        }
    }

    private var playbackPolicy: FitChefLottiePlaybackPolicy {
        .resolve(reduceMotion: reduceMotion, animationLoaded: animation != nil)
    }
}

/// RU: Анимированный FitChef с Lottie анимацией
/// EN: Animated FitChef with Lottie animation
struct AnimatedFitChefLottie: View {
    var body: some View {
        LottieAnimationView(asset: .blink)
    }
}

/// RU: Анимированное облачко с Lottie FitChef
/// EN: Animated speech bubble with Lottie FitChef
struct AnimatedMascotBubbleLottie: View {
    var textKey: LocalizedStringKey

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            AnimatedFitChefLottie()
                .frame(width: 48, height: 48)
                .clipShape(Circle())
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

/// RU: Тестовый экран для Lottie анимаций
/// EN: Test screen for Lottie animations
struct LottieTestView: View {
    var body: some View {
        VStack(spacing: 20) {
            Text("Lottie Animation Test")
                .font(.title)
                .bold()
                .foregroundStyle(.white)

            LottieAnimationView(asset: .blink, showsPlaybackStatus: true)
                .frame(width: 200, height: 200)
                .clipShape(RoundedRectangle(cornerRadius: 20))

            Text("File: \(FitChefLottieAsset.blink.rawValue)")
                .font(.caption)
                .foregroundStyle(.gray)

            Spacer()
        }
        .padding()
        .navyBackground()
        .navigationTitle("Lottie Test")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    VStack(spacing: 20) {
        LottieAnimationView(asset: .blink)
            .frame(width: 100, height: 100)

        AnimatedMascotBubbleLottie(textKey: "Добро пожаловать в PulsePlate!")
            .padding()
    }
    .navyBackground()
}
