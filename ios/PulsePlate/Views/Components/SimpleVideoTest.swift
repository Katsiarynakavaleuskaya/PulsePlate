import SwiftUI
import AVKit

/// RU: Простой тест для проверки MP4 файлов в Bundle
/// EN: Simple test for MP4 files in Bundle
struct SimpleVideoTest: View {
    @State private var currentVideo = 0
    @State private var player: AVPlayer?

    private let videos = [
        "20250913_1212_FitChef Cat Animation_simple_compose_01k515hmynfk7amcg36rv5eqba",
        "20250913_1212_FitChef Cat Animation_simple_compose_01k515hnxhea6tx4wrkxxt4kd5"
    ]

    var body: some View {
        VStack(spacing: 20) {
            Text("Simple Video Test")
                .font(.title)
                .bold()
                .foregroundStyle(.white)

            // Video Player
            if let player = player {
                VideoPlayer(player: player)
                    .frame(width: 200, height: 200)
                    .clipShape(RoundedRectangle(cornerRadius: 20))
            } else {
                VStack {
                    Image(systemName: "video.slash")
                        .font(.system(size: 50))
                        .foregroundStyle(.red)
                    Text("Video not found")
                        .foregroundStyle(.red)
                    Text("File: \(videos[currentVideo])")
                        .font(.caption)
                        .foregroundStyle(.gray)
                        .multilineTextAlignment(.center)
                }
                .frame(width: 200, height: 200)
                .background(Color.gray.opacity(0.2))
                .clipShape(RoundedRectangle(cornerRadius: 20))
            }

            // Controls
            HStack(spacing: 20) {
                Button("Previous") {
                    currentVideo = (currentVideo - 1 + videos.count) % videos.count
                    loadVideo()
                }
                .buttonStyle(.bordered)
                .foregroundStyle(.white)

                Button("Next") {
                    currentVideo = (currentVideo + 1) % videos.count
                    loadVideo()
                }
                .buttonStyle(.bordered)
                .foregroundStyle(.white)
            }

            // Video Info
            VStack(alignment: .leading, spacing: 8) {
                Text("Current Video: \(currentVideo + 1)/\(videos.count)")
                    .font(.headline)
                    .foregroundStyle(.white)

                Text("File: \(videos[currentVideo])")
                    .font(.caption)
                    .foregroundStyle(.gray)
                    .lineLimit(2)
                    .multilineTextAlignment(.center)
            }
            .padding()
            .background(Color.white.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 12))

            // Debug Info
            VStack(alignment: .leading, spacing: 4) {
                Text("Debug Info:")
                    .font(.caption)
                    .bold()
                    .foregroundStyle(.white)

                Text("Bundle path: \(Bundle.main.bundlePath)")
                    .font(.caption2)
                    .foregroundStyle(.gray)

                Text("Resources path: \(Bundle.main.resourcePath ?? "nil")")
                    .font(.caption2)
                    .foregroundStyle(.gray)
            }
            .padding()
            .background(Color.black.opacity(0.3))
            .clipShape(RoundedRectangle(cornerRadius: 8))

            Spacer()
        }
        .padding()
        .navyBackground()
        .onAppear {
            loadVideo()
        }
    }

    private func loadVideo() {
        let videoName = videos[currentVideo]

        // Try different ways to find the video
        var videoURL: URL?

        // Method 1: Direct file name
        if let url = Bundle.main.url(forResource: videoName, withExtension: "mp4") {
            videoURL = url
        }
        // Method 2: Without extension
        else if let url = Bundle.main.url(forResource: videoName, withExtension: nil) {
            videoURL = url
        }
        // Method 3: Search in Resources folder
        else if let resourcesPath = Bundle.main.resourcePath {
            let fullPath = "\(resourcesPath)/\(videoName).mp4"
            if FileManager.default.fileExists(atPath: fullPath) {
                videoURL = URL(fileURLWithPath: fullPath)
            }
        }

        if let url = videoURL {
            player = AVPlayer(url: url)
            print("✅ Video loaded: \(url)")
        } else {
            player = nil
            print("❌ Video not found: \(videoName)")
        }
    }
}

#Preview {
    SimpleVideoTest()
}
