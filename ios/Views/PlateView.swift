import SwiftUI

struct PlateViewPP: View {
  @State private var progress: Double = 0.68
  @State private var isAnimating = false

  var body: some View {
    ScrollView {
      VStack(spacing: 24) {
        // Header
        VStack(alignment: .leading, spacing: 8) {
          Text("My Plate")
            .font(.largeTitle)
            .bold()
            .foregroundStyle(.white)
          Text("Track your daily nutrition goals")
            .foregroundStyle(.white.opacity(0.8))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal)

        // Interactive Plate Ring
        VStack(spacing: 16) {
          PlateRing(progress: progress)
            .onTapGesture {
              withAnimation(.spring(response: 0.6, dampingFraction: 0.8)) {
                progress = min(1.0, progress + 0.1)
                isAnimating = true
              }
            }

          // Progress details
          VStack(spacing: 8) {
            Text("Daily Progress")
              .font(.headline)
              .foregroundStyle(.white)

            HStack(spacing: 20) {
              ProgressItem(title: "Protein", value: 0.8, color: .red)
              ProgressItem(title: "Carbs", value: 0.6, color: .orange)
              ProgressItem(title: "Fats", value: 0.4, color: .yellow)
            }
          }
          .padding()
          .background(Color.white.opacity(0.1))
          .cornerRadius(12)
        }
        .padding()

        // Mascot hint
        MascotBubble(textKey: "mascot.plate.hint")
          .padding(.horizontal)

        // Quick actions
        HStack(spacing: 16) {
          Button("Add Meal") {
            // TODO: Navigate to meal entry
          }
          .buttonStyle(.bordered)
          .foregroundStyle(.white)

          Button("View Details") {
            // TODO: Show detailed nutrition breakdown
          }
          .buttonStyle(.borderedProminent)
        }
        .padding()
      }
    }
    .background(Color("Navy"))
    .accessibilityLabel("Plate Screen")
  }
}

struct ProgressItem: View {
  let title: String
  let value: Double
  let color: Color

  var body: some View {
    VStack(spacing: 4) {
      Text(title)
        .font(.caption)
        .foregroundStyle(.white.opacity(0.8))

      ZStack {
        Circle()
          .stroke(Color.white.opacity(0.2), lineWidth: 4)
          .frame(width: 40, height: 40)

        Circle()
          .trim(from: 0, to: value)
          .stroke(color, style: StrokeStyle(lineWidth: 4, lineCap: .round))
          .frame(width: 40, height: 40)
          .rotationEffect(.degrees(-90))

        Text("\(Int(value * 100))%")
          .font(.caption2)
          .bold()
          .foregroundStyle(.white)
      }
    }
  }
}

#Preview {
  PlateViewPP()
}
