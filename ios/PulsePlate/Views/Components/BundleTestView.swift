import SwiftUI

/// RU: Тест для проверки файлов в Bundle
/// EN: Test for checking files in Bundle
struct BundleTestView: View {
    var body: some View {
        VStack(spacing: 20) {
            Text("Bundle Test")
                .font(.title)
                .bold()
                .foregroundStyle(.white)

            // Проверяем MP4 файлы
            VStack(alignment: .leading, spacing: 8) {
                Text("MP4 Files in Bundle:")
                    .font(.headline)
                    .foregroundStyle(.white)

                let mp4Files = [
                    "20250913_1212_FitChef Cat Animation_simple_compose_01k515hmynfk7amcg36rv5eqba",
                    "20250913_1212_FitChef Cat Animation_simple_compose_01k515hnxhea6tx4wrkxxt4kd5"
                ]

                ForEach(mp4Files, id: \.self) { file in
                    HStack {
                        if Bundle.main.url(forResource: file, withExtension: "mp4") != nil {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                            Text("✅ \(file)")
                                .font(.caption)
                                .foregroundStyle(.green)
                        } else {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(.red)
                            Text("❌ \(file)")
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                    }
                }
            }
            .padding()
            .background(Color.white.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 12))

            // Информация о Bundle
            VStack(alignment: .leading, spacing: 4) {
                Text("Bundle Info:")
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
        .background(.navy)
        .navigationTitle("Bundle Test")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    BundleTestView()
}
