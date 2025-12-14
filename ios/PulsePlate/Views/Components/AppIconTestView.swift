import SwiftUI

struct AppIconTestView: View {
    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                Text("App Icon Test")
                    .font(.largeTitle)
                    .bold()
                    .foregroundColor(.white)

                // Показываем иконку в разных размерах
                VStack(spacing: 16) {
                    Text("App Icon Preview")
                        .font(.headline)
                        .foregroundColor(.white)

                    HStack(spacing: 20) {
                        // Маленькая иконка
                        Image("AppIcon")
                            .resizable()
                            .frame(width: 60, height: 60)
                            .cornerRadius(12)

                        // Средняя иконка
                        Image("AppIcon")
                            .resizable()
                            .frame(width: 120, height: 120)
                            .cornerRadius(20)

                        // Большая иконка
                        Image("AppIcon")
                            .resizable()
                            .frame(width: 180, height: 180)
                            .cornerRadius(30)
                    }
                }
                .padding()
                .background(Color.surface)
                .cornerRadius(16)

                // Информация о иконке
                VStack(alignment: .leading, spacing: 12) {
                    Text("Icon Information")
                        .font(.headline)
                        .foregroundColor(.white)

                    VStack(alignment: .leading, spacing: 8) {
                        InfoRow(title: "Design", value: "PulsePlate Brand")
                        InfoRow(title: "Colors", value: "Navy + Blue + Green + Red")
                        InfoRow(title: "Style", value: "Minimalist with Heart")
                        InfoRow(title: "Format", value: "PNG with Alpha")
                    }
                }
                .padding()
                .background(Color.surface)
                .cornerRadius(16)

                // Размеры иконок
                VStack(alignment: .leading, spacing: 12) {
                    Text("Generated Sizes")
                        .font(.headline)
                        .foregroundColor(.white)

                    LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 3), spacing: 12) {
                        SizeCard(size: "20x20", count: "3 variants")
                        SizeCard(size: "29x29", count: "3 variants")
                        SizeCard(size: "40x40", count: "3 variants")
                        SizeCard(size: "60x60", count: "2 variants")
                        SizeCard(size: "76x76", count: "2 variants")
                        SizeCard(size: "83.5x83.5", count: "1 variant")
                        SizeCard(size: "1024x1024", count: "App Store")
                    }
                }
                .padding()
                .background(Color.surface)
                .cornerRadius(16)
            }
            .padding()
        }
                .navyBackground()
    }
}

struct InfoRow: View {
    let title: String
    let value: String

    var body: some View {
        HStack {
            Text(title)
                .foregroundColor(.textSecondary)
            Spacer()
            Text(value)
                .foregroundColor(.white)
                .fontWeight(.medium)
        }
    }
}

struct SizeCard: View {
    let size: String
    let count: String

    var body: some View {
        VStack(spacing: 4) {
            Text(size)
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundColor(.white)

            Text(count)
                .font(.caption2)
                .foregroundColor(.textTertiary)
        }
        .padding(8)
        .background(Color.surfaceElevated)
        .cornerRadius(8)
    }
}

#Preview {
    AppIconTestView()
}
