import SwiftUI

struct PlateSegments: View {
  @State private var selectedSegment: Int? = nil
  private let segments: [NutritionSegment]
  let onSegmentTap: (Int) -> Void

  init(segments: [NutritionSegment], onSegmentTap: @escaping (Int) -> Void) {
    self.segments = segments
    self.onSegmentTap = onSegmentTap
  }

  var body: some View {
    ZStack {
      // Background circle
      Circle()
        .fill(Color.white.opacity(0.1))
        .frame(width: 280, height: 280)

      // Segments
      ForEach(Array(segments.enumerated()), id: \.offset) { index, segment in
        SegmentView(
          segment: segment,
          isSelected: selectedSegment == index,
          onTap: {
            selectedSegment = selectedSegment == index ? nil : index
            onSegmentTap(index)
          }
        )
      }

      // Center circle with logo
      Circle()
        .fill(Color.white.opacity(0.9))
        .frame(width: 60, height: 60)
        .overlay(
          Image(systemName: "heart.fill")
            .foregroundColor(.red)
            .font(.title2)
        )
    }
  }
}

struct SegmentView: View {
  let segment: NutritionSegment
  let isSelected: Bool
  let onTap: () -> Void

  var body: some View {
    Path { path in
      let center = CGPoint(x: 140, y: 140)
      let radius: CGFloat = 100
      let startAngle = Angle.degrees(segment.startAngle)
      let endAngle = Angle.degrees(segment.endAngle)

      path.move(to: center)
      path.addArc(
        center: center,
        radius: radius,
        startAngle: startAngle,
        endAngle: endAngle,
        clockwise: false
      )
      path.closeSubpath()
    }
    .fill(segment.color)
    .overlay(
      Path { path in
        let center = CGPoint(x: 140, y: 140)
        let radius: CGFloat = 100
        let startAngle = Angle.degrees(segment.startAngle)
        let endAngle = Angle.degrees(segment.endAngle)

        path.move(to: center)
        path.addArc(
          center: center,
          radius: radius,
          startAngle: startAngle,
          endAngle: endAngle,
          clockwise: false
        )
        path.closeSubpath()
      }
      .stroke(Color.white, lineWidth: 2)
    )
    .scaleEffect(isSelected ? 1.1 : 1.0)
    .animation(.spring(response: 0.4, dampingFraction: 0.8), value: isSelected)
    .overlay {
      if isSelected {
        Rectangle()
          .fill(
            LinearGradient(
              colors: [
                Color.white.opacity(0),
                Color.white.opacity(0.3),
                Color.white.opacity(0)
              ],
              startPoint: .leading,
              endPoint: .trailing
            )
          )
          .mask(
            Path { path in
              let center = CGPoint(x: 140, y: 140)
              let radius: CGFloat = 100
              let startAngle = Angle.degrees(segment.startAngle)
              let endAngle = Angle.degrees(segment.endAngle)

              path.move(to: center)
              path.addArc(
                center: center,
                radius: radius,
                startAngle: startAngle,
                endAngle: endAngle,
                clockwise: false
              )
              path.closeSubpath()
            }
          )
          .animation(.linear(duration: 1.5).repeatForever(autoreverses: false), value: isSelected)
      }
    }
    .onTapGesture {
      withAnimation(.spring(response: 0.3, dampingFraction: 0.6)) {
        onTap()
      }
    }
    .accessibilityLabel(segment.name)
    .accessibilityHint("Tap to select \(segment.name)")
  }
}

struct NutritionSegment {
  let name: String
  let color: Color
  let startAngle: Double
  let endAngle: Double
  let percentage: Double
  let icon: String
  let currentValue: Double
  let targetValue: Double
}

#Preview {
  PlateSegments(
    segments: [
      NutritionSegment(
        name: "Vegetables",
        color: .green,
        startAngle: 0,
        endAngle: 90,
        percentage: 40,
        icon: "leaf.fill",
        currentValue: 3.2,
        targetValue: 4.0
      ),
      NutritionSegment(
        name: "Protein",
        color: .red,
        startAngle: 90,
        endAngle: 180,
        percentage: 25,
        icon: "fish.fill",
        currentValue: 1.8,
        targetValue: 2.0
      ),
      NutritionSegment(
        name: "Carbs",
        color: .orange,
        startAngle: 180,
        endAngle: 270,
        percentage: 25,
        icon: "grain.fill",
        currentValue: 1.2,
        targetValue: 1.5
      ),
      NutritionSegment(
        name: "Fats",
        color: .yellow,
        startAngle: 270,
        endAngle: 360,
        percentage: 10,
        icon: "drop.fill",
        currentValue: 0.6,
        targetValue: 0.8
      )
    ],
    onSegmentTap: { _ in }
  )
  .background(.navy)
}
