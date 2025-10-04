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
                        ColorCard(name: "Navy", color: Color.navy)
                        ColorCard(name: "AppPrimary", color: Color.appPrimary)
                        ColorCard(name: "Accent", color: Color.accent)
                    }

                    HStack(spacing: 12) {
                        ColorCard(name: "Heart", color: Color.heart)
                        ColorCard(name: "Gold", color: Color.gold)
                        ColorCard(name: "Success", color: Color.green)
                    }
                }

                // Surface Colors
                VStack(alignment: .leading, spacing: 12) {
                    Text("Surface Colors")
                        .font(.headline)
                        .foregroundColor(.white)

                    HStack(spacing: 12) {
                        ColorCard(name: "Surface", color: Color.gray.opacity(0.1))
                        ColorCard(name: "Elevated", color: Color.white.opacity(0.1))
                        ColorCard(name: "Highlight", color: Color.blue.opacity(0.1))
                    }
                }

                // Text Colors
                VStack(alignment: .leading, spacing: 12) {
                    Text("Text Colors")
                        .font(.headline)
                        .foregroundColor(.white)

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Primary Text")
                            .foregroundColor(.white)
                        Text("Secondary Text")
                            .foregroundColor(.gray)
                        Text("Tertiary Text")
                            .foregroundColor(.gray.opacity(0.6))
                    }
                    .padding()
                    .background(Color.gray.opacity(0.1))
                    .cornerRadius(12)
                }
            }
            .padding()
        }
        .background(Color.navy)
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
                .foregroundColor(.textSecondary)
        }
    }
}

#Preview {
    ColorTestView()
}
