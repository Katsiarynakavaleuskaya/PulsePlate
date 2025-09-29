import SwiftUI
import AVKit

/// RU: Тестовый экран для проверки анимаций FitChef
/// EN: Test screen for FitChef animations
struct AnimationTestView: View {
    @State private var currentVideo = 0
    @State private var isPlaying = false

    private let videos = [
        "20250913_1212_FitChef Cat Animation_simple_compose_01k515hmynfk7amcg36rv5eqba",
        "20250913_1212_FitChef Cat Animation_simple_compose_01k515hnxhea6tx4wrkxxt4kd5"
    ]

    var body: some View {
        VStack(spacing: 20) {
            Text("FitChef Animation Test")
                .font(.title)
                .bold()
                .foregroundStyle(.white)

            // Video Player
            if let url = Bundle.main.url(forResource: videos[currentVideo], withExtension: "mp4") {
                VideoPlayer(player: AVPlayer(url: url))
                    .frame(width: 200, height: 200)
                    .clipShape(RoundedRectangle(cornerRadius: 20))
                    .onAppear {
                        isPlaying = true
                    }
            } else {
                VStack {
                    Image(systemName: "video.slash")
                        .font(.system(size: 50))
                        .foregroundStyle(.red)
                    Text("Video not found")
                        .foregroundStyle(.red)
                    Text("File: \(videos[currentVideo]).mp4")
                        .font(.caption)
                        .foregroundStyle(.gray)
                }
                .frame(width: 200, height: 200)
                .background(Color.gray.opacity(0.2))
                .clipShape(RoundedRectangle(cornerRadius: 20))
            }

            // Controls
            HStack(spacing: 20) {
                Button("Previous") {
                    currentVideo = (currentVideo - 1 + videos.count) % videos.count
                }
                .buttonStyle(.bordered)
                .foregroundStyle(.white)

                Button(isPlaying ? "Pause" : "Play") {
                    isPlaying.toggle()
                }
                .buttonStyle(.borderedProminent)
                .foregroundStyle(.white)

                Button("Next") {
                    currentVideo = (currentVideo + 1) % videos.count
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
            }
            .padding()
            .background(Color.white.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 12))

            Spacer()
        }
        .padding()
        .background(.navy)
        .navigationTitle("Animation Test")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        AnimationTestView()
    }
}
