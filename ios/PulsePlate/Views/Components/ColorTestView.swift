import SwiftUI

struct ColorTestView: View {
    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                Text("Color Assets Test")
                    .font(.largeTitle)
                    .bold()
                    .foregroundColor(.white)

                // Brand Colors
                VStack(alignment: .leading, spacing: 12) {
                    Text("Brand Colors")
                        .font(.headline)
                        .foregroundColor(.white)

                    HStack(spacing: 12) {
                        ColorCard(name: "Navy", color: .navy)
                        ColorCard(name: "AppPrimary", color: .appPrimary)
                        ColorCard(name: "Accent", color: .accent)
                    }

                    HStack(spacing: 12) {
                        ColorCard(name: "Heart", color: .heart)
                        ColorCard(name: "Gold", color: .gold)
                        ColorCard(name: "Success", color: .success)
                    }
                }

                // Surface Colors
                VStack(alignment: .leading, spacing: 12) {
                    Text("Surface Colors")
                        .font(.headline)
                        .foregroundColor(.white)

                    HStack(spacing: 12) {
                        ColorCard(name: "Surface", color: Color.surface)
                        ColorCard(name: "Elevated", color: Color.surfaceElevated)
                        ColorCard(name: "Highlight", color: Color.surfaceHighlight)
                    }
                }

                // Text Colors
                VStack(alignment: .leading, spacing: 12) {
                    Text("Text Colors")
                        .font(.headline)
                        .foregroundColor(.white)

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Primary Text")
                        Text("Primary Text")
                            .foregroundColor(.textPrimary)
                        Text("Secondary Text")
                            .foregroundColor(.gray)
                        Text("Tertiary Text")
                            .foregroundColor(.textTertiary)
                    }
                    .padding()
                    .background(Color.surface)
                    .cornerRadius(12)
                }
            }
            .padding()
        }
        .navyBackground()
    }
}

struct ColorCard: View {
    let name: String
    let color: Color

    var body: some View {
        VStack(spacing: 8) {
            RoundedRectangle(cornerRadius: 8)
                .fill(color)
                .frame(width: 60, height: 60)

            Text(name)
                .font(.caption)
                .foregroundColor(.white)
        }
    }
}

#Preview {
    ColorTestView()
}
