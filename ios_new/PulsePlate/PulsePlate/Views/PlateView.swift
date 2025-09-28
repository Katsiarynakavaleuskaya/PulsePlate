import SwiftUI

struct PlateViewPP: View {
  @StateObject private var nutritionService = NutritionService()
  @State private var selectedSegment: Int? = nil

  private var segments: [NutritionSegment] {
    guard let nutritionData = nutritionService.nutritionData else {
      return []
    }

    return nutritionData.segments.enumerated().map { index, segmentData in
      NutritionSegment(
        name: segmentData.name,
        color: colorFromString(segmentData.color),
        startAngle: Double(index * 90),
        endAngle: Double((index + 1) * 90),
        percentage: segmentData.percentage,
        icon: segmentData.icon,
        currentValue: segmentData.currentValue,
        targetValue: segmentData.targetValue
      )
    }
  }

  private var progress: Double {
    nutritionService.nutritionData?.totalProgress ?? 0.0
  }

  var body: some View {
    ScrollView {
      VStack(spacing: 24) {
        // Header
        VStack(alignment: .leading, spacing: 8) {
          Text("My Plate")
            .font(.largeTitle)
            .bold()
            .foregroundStyle(.white)
          Text("Tap segments to customize your nutrition")
            .foregroundStyle(.white.opacity(0.8))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal)

        // Loading state
        if nutritionService.isLoading {
          ProgressView("Loading nutrition data...")
            .foregroundStyle(.white)
            .padding()
        } else if let error = nutritionService.error {
          VStack(spacing: 12) {
            Text("Error loading data")
              .foregroundStyle(.red)
            Text(error)
              .font(.caption)
              .foregroundStyle(.red.opacity(0.8))
            Button("Retry") {
              Task {
                await nutritionService.fetchNutritionData()
              }
            }
            .buttonStyle(.bordered)
            .foregroundStyle(.white)
          }
          .padding()
        } else {
        // Interactive Plate Segments with animations
        VStack(spacing: 16) {
          PlateSegments(segments: segments) { index in
            withAnimation(.spring(response: 0.6, dampingFraction: 0.8)) {
              selectedSegment = selectedSegment == index ? nil : index
            }
          }
          .slideIn(isActive: !nutritionService.isLoading, delay: 0.2)

          // Overall progress ring with shimmer effect
          PlateRing(progress: progress)
            .scaleOnAppear(isActive: !nutritionService.isLoading, scale: 1.05)
            .shimmer()
        }
        .padding()

          // Selected segment details with animation
          if let selected = selectedSegment, selected < segments.count {
            SegmentDetailView(segment: segments[selected])
              .padding(.horizontal)
              .slideIn(isActive: selectedSegment != nil, delay: 0.1)
              .fadeIn(isActive: selectedSegment != nil, delay: 0.1)
          }
        }

        // Mascot hint with pulsing animation
        MascotBubble(textKey: "mascot.plate.hint")
          .padding(.horizontal)
          .pulsing(isActive: selectedSegment == nil, scale: 1.02)
          .fadeIn(isActive: !nutritionService.isLoading, delay: 0.5)

        // Quick actions with staggered animation
        HStack(spacing: 16) {
          Button("Add Meal") {
            // TODO: Navigate to meal entry
          }
          .buttonStyle(.bordered)
          .foregroundStyle(.white)
          .slideIn(isActive: !nutritionService.isLoading, delay: 0.6)

          Button("View Details") {
            // TODO: Show detailed nutrition breakdown
          }
          .buttonStyle(.borderedProminent)
          .slideIn(isActive: !nutritionService.isLoading, delay: 0.7)
        }
        .padding()
      }
    }
    .background(Color("Navy"))
    .accessibilityLabel("Plate Screen")
    .onAppear {
      // Load mock data for development
      nutritionService.loadMockData()
    }
  }

  func colorFromString(_ colorString: String) -> Color {
    switch colorString.lowercased() {
    case "green":
      return .green
    case "red":
      return .red
    case "orange":
      return .orange
    case "yellow":
      return .yellow
    case "blue":
      return .blue
    case "purple":
      return .purple
    default:
      return .gray
    }
  }
}

struct SegmentDetailView: View {
  let segment: NutritionSegment

  var body: some View {
    VStack(alignment: .leading, spacing: 12) {
      HStack {
        Image(systemName: segment.icon)
          .foregroundColor(segment.color)
          .font(.title2)

        VStack(alignment: .leading, spacing: 4) {
          Text(segment.name)
            .font(.title2)
            .bold()
            .foregroundStyle(.white)

          Text("\(Int(segment.percentage))% of your plate")
            .font(.caption)
            .foregroundStyle(.white.opacity(0.8))
        }

        Spacer()
      }

      // Progress bar
      VStack(alignment: .leading, spacing: 8) {
        HStack {
          Text("Progress")
            .font(.caption)
            .foregroundStyle(.white.opacity(0.8))
          Spacer()
          Text("\(Int((segment.currentValue / segment.targetValue) * 100))%")
            .font(.caption)
            .bold()
            .foregroundStyle(.white)
        }

        ProgressView(value: segment.currentValue, total: segment.targetValue)
          .progressViewStyle(LinearProgressViewStyle(tint: segment.color))
          .scaleEffect(y: 2)
      }

      // Values
      HStack {
        VStack(alignment: .leading) {
          Text("Current")
            .font(.caption2)
            .foregroundStyle(.white.opacity(0.6))
          Text("\(segment.currentValue, specifier: "%.1f") servings")
            .font(.caption)
            .bold()
            .foregroundStyle(.white)
        }

        Spacer()

        VStack(alignment: .trailing) {
          Text("Target")
            .font(.caption2)
            .foregroundStyle(.white.opacity(0.6))
          Text("\(segment.targetValue, specifier: "%.1f") servings")
            .font(.caption)
            .bold()
            .foregroundStyle(.white)
        }
      }
    }
    .padding()
    .background(Color.white.opacity(0.1))
    .cornerRadius(12)
    .overlay(
      RoundedRectangle(cornerRadius: 12)
        .stroke(segment.color.opacity(0.3), lineWidth: 1)
    )
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
