import SwiftUI
import AVKit
import OSLog

/// RU: Компонент для воспроизведения MP4 анимаций FitChef
/// EN: Component for playing FitChef MP4 animations
struct VideoPlayerView: View {
    let videoName: String
    @State private var player: AVPlayer?
    @State private var playerObserver: NSObjectProtocol?

    private static let logger = Logger(subsystem: "PulsePlate", category: "VideoPlayerView")

    var body: some View {
        Group {
            if let player = player {
                VideoPlayer(player: player)
            } else {
                // Fallback image if video fails to load
                Image("FitChef")
                    .resizable()
                    .scaledToFit()
            }
        }
        .onAppear {
            setupPlayer()
        }
        .onChange(of: videoName) { _ in
            setupPlayer()
        }
        .onDisappear {
            removeObserver()
            cleanupPlayer()
        }
    }

    private func setupPlayer() {
        removeObserver()
        cleanupPlayer()

        guard let url = resolveVideoURL(name: videoName) else {
            Self.logger.error("Video file not found: \(videoName, privacy: .public)")
            return
        }

        let newPlayer = AVPlayer(url: url)
        player = newPlayer
        setupPlayerLoop(for: newPlayer)
        newPlayer.play()
    }

    private func resolveVideoURL(name: String) -> URL? {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }

        if trimmed.lowercased().hasSuffix(".mp4") {
            let base = String(trimmed.dropLast(4))
            return Bundle.main.url(forResource: base, withExtension: "mp4")
        } else {
            return Bundle.main.url(forResource: trimmed, withExtension: "mp4")
        }
    }

    private func setupPlayerLoop(for player: AVPlayer) {
        player.actionAtItemEnd = .none

        playerObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: player.currentItem,
            queue: .main
        ) { _ in
            player.seek(to: .zero) { _ in
                player.play()
            }
        }
    }

    private func removeObserver() {
        if let token = playerObserver {
            NotificationCenter.default.removeObserver(token)
            playerObserver = nil
        }
    }

    private func cleanupPlayer() {
        player?.pause()
        player = nil
    }
}

/// RU: Анимированный FitChef с MP4 анимацией
/// EN: Animated FitChef with MP4 animation
struct AnimatedFitChefVideo: View {
    @State private var currentVideo = 0
    @State private var rotationTimer: Timer?

    private let videos = [
        "20250913_1212_FitChef Cat Animation_simple_compose_01k515hmynfk7amcg36rv5eqba",
        "20250913_1212_FitChef Cat Animation_simple_compose_01k515hnxhea6tx4wrkxxt4kd5"
    ]

    var body: some View {
        VideoPlayerView(videoName: videos[currentVideo])
            .onAppear {
                startRotation()
            }
            .onDisappear {
                stopRotation()
            }
    }

    private func startRotation() {
        // Stop any existing timer first
        stopRotation()

        rotationTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { _ in
            withAnimation(.easeInOut(duration: 0.5)) {
                currentVideo = (currentVideo + 1) % videos.count
            }
        }
    }

    private func stopRotation() {
        rotationTimer?.invalidate()
        rotationTimer = nil
    }
}

/// RU: Анимированное облачко с видео FitChef
/// EN: Animated speech bubble with FitChef video
struct AnimatedMascotBubbleVideo: View {
    var textKey: LocalizedStringKey
    @State private var showVideo = false

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            if showVideo {
                AnimatedFitChefVideo()
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
            // Show video after a short delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                withAnimation(.easeInOut(duration: 0.3)) {
                    showVideo = true
                }
            }
        }
    }
}

#Preview {
    VStack(spacing: 20) {
        AnimatedFitChefVideo()
            .frame(width: 100, height: 100)

        AnimatedMascotBubbleVideo(textKey: "Добро пожаловать в PulsePlate!")
            .padding()
    }
    .navyBackground()
}
