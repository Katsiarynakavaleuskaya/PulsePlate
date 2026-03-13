import SwiftUI

enum PlatePrimaryCTA {
  case addMeal
  case viewDetails
}

enum PlatePrimaryDestination: Equatable {
  case mealEntry
  case nutritionDetails
}

func destination(for action: PlatePrimaryCTA) -> PlatePrimaryDestination {
  switch action {
  case .addMeal:
    return .mealEntry
  case .viewDetails:
    return .nutritionDetails
  }
}

struct MealEntryView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var mealName = ""
    @State private var servings = "1.0"
    @State private var mealSaved = false

    private var isFormValid: Bool {
        !mealName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    var body: some View {
        Form {
            Section("Meal") {
                TextField("Meal name", text: $mealName)
                TextField("Servings", text: $servings)
                    .keyboardType(.decimalPad)
            }

            Section {
                Button("Save meal") {
                    mealSaved = true
                }
                .disabled(!isFormValid)
            }

            if mealSaved {
                Section("Saved") {
                    Text("\(mealName) added to today's log.")
                        .foregroundStyle(.green)
                }
            }
        }
        .navigationTitle("Add Meal")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button("Done") {
                    dismiss()
                }
            }
        }
    }
}

struct NutritionDetailsView: View {
    let segments: [NutritionSegment]
    let progress: Double

    private var clampedProgress: Double {
        min(max(progress, 0.0), 1.0)
    }

    var body: some View {
        List {
            Section("Overall") {
                Text("Completion: \(Int((clampedProgress * 100).rounded()))%")
            }

            Section("Segments") {
                ForEach(segments.indices, id: \.self) { index in
                    let segment = segments[index]
                    VStack(alignment: .leading, spacing: 6) {
                        Text(segment.name)
                            .font(.headline)
                        Text(
                            String(
                                format: "%.1f / %.1f servings",
                                segment.currentValue,
                                segment.targetValue
                            )
                        )
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .navigationTitle("Nutrition Details")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct PlateViewPP: View {
  @StateObject private var nutritionService = NutritionService()
  @State private var selectedSegment: Int? = nil
  @State private var showMealEntry = false
  @State private var showNutritionDetails = false
  @State private var showProfile = false
  @State private var showProSetup = false

  private var isAppStoreScreenshotMode: Bool {
    AppStoreScreenshotContext.isEnabled
  }

  private var segments: [NutritionSegment] {
    guard let nutritionData = nutritionService.nutritionData else {
      return []
    }

    var runningAngle: Double = 0

    return nutritionData.segments.map { segmentData in
      let sweep = (segmentData.percentage / 100.0) * 360.0
      let startAngle = runningAngle
      let endAngle = startAngle + sweep
      runningAngle = endAngle

      return NutritionSegment(
        name: segmentData.name,
        color: Color.segmentSemanticColor(from: segmentData.color),
        startAngle: startAngle,
        endAngle: endAngle,
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

  private func localized(_ key: String) -> String {
    NSLocalizedString(key, comment: "")
  }

  private func handlePrimaryCTA(_ action: PlatePrimaryCTA) {
    switch destination(for: action) {
    case .mealEntry:
      showMealEntry = true
    case .nutritionDetails:
      showNutritionDetails = true
    }
  }

  private var plateSegmentsView: some View {
    let content = PlateSegments(segments: segments) { index in
      withAnimation(.spring(response: 0.6, dampingFraction: 0.8)) {
        selectedSegment = selectedSegment == index ? nil : index
      }
    }

    if isAppStoreScreenshotMode {
      return AnyView(content)
    }

    return AnyView(content.slideIn(isActive: !nutritionService.isLoading, delay: 0.2))
  }

  private var plateRingView: some View {
    let content = PlateRing(progress: progress)

    if isAppStoreScreenshotMode {
      return AnyView(content)
    }

    return AnyView(
      content
        .scaleOnAppear(isActive: !nutritionService.isLoading, scale: 1.05)
        .shimmer()
    )
  }

  private func segmentDetailView(_ segment: NutritionSegment) -> some View {
    let content = SegmentDetailView(segment: segment)
      .padding(.horizontal)

    if isAppStoreScreenshotMode {
      return AnyView(content)
    }

    return AnyView(
      content
        .slideIn(isActive: selectedSegment != nil, delay: 0.1)
        .fadeIn(isActive: selectedSegment != nil, delay: 0.1)
    )
  }

  var body: some View {
    NavigationStack {
      ScrollView {
        VStack(spacing: 24) {
          // Header
          VStack(alignment: .leading, spacing: 8) {
            Text(localized("plate.preview.title"))
              .font(.largeTitle)
              .bold()
              .foregroundStyle(.white)
            Text(localized("plate.preview.subtitle"))
              .foregroundStyle(.white.opacity(0.8))
          }
          .frame(maxWidth: .infinity, alignment: .leading)
          .padding(.horizontal)

          // Loading state
          if nutritionService.isLoading {
            ProgressView("Loading nutrition data...")
              .foregroundStyle(.white)
              .padding()
          } else if let issue = nutritionService.issue {
            PlateIssueView(issue: issue) { action in
              switch action {
              case .none:
                break
              case .retry:
                Task {
                  await nutritionService.fetchNutritionData()
                }
              case .openProfile:
                showProfile = true
              case .openProSetup:
                showProSetup = true
              }
            }
          } else {
          // Interactive Plate Segments with animations
          VStack(spacing: 16) {
            plateSegmentsView

            // Overall progress ring with shimmer effect
            plateRingView
          }
          .padding()

            // Selected segment details with animation
            if let selected = selectedSegment, selected < segments.count {
              segmentDetailView(segments[selected])
            }
          }
        }
        .padding(.bottom, 12)
      }
      .background(Color.navy.ignoresSafeArea())
      .navigationDestination(isPresented: $showMealEntry) {
        MealEntryView()
      }
      .navigationDestination(isPresented: $showNutritionDetails) {
        NutritionDetailsView(segments: segments, progress: progress)
      }
      .navigationDestination(isPresented: $showProfile) {
        ProfileView()
      }
      .navigationDestination(isPresented: $showProSetup) {
        #if DEBUG
        DebugToolsScreen()
        #else
        ProfileView()
        #endif
      }
      .safeAreaInset(edge: .bottom) {
        VStack(spacing: 12) {
          // Mascot hint always visible above action buttons
          MascotBubble(textKey: "mascot.plate.hint")
            .padding(.horizontal)

          HStack(spacing: 16) {
            Button(localized("plate.preview.add_meal")) {
              handlePrimaryCTA(.addMeal)
            }
            .accessibilityIdentifier("appstore.plate.add_meal")
            .buttonStyle(.bordered)

            Button(localized("plate.preview.view_details")) {
              handlePrimaryCTA(.viewDetails)
            }
            .accessibilityIdentifier("appstore.plate.view_details")
            .buttonStyle(.borderedProminent)
          }
          .padding(.horizontal)
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .padding(.horizontal)
        .padding(.bottom, 8)
      }
      .accessibilityLabel("Plate Screen")
      .onAppear {
        if isAppStoreScreenshotMode {
          nutritionService.loadMockData()
          return
        }

        // RU: В обычном runtime загружаем реальные данные; в screenshot-mode запрещаем async jitter.
        // EN: Normal runtime loads live data; screenshot mode stays static to avoid async jitter.
        Task {
          await nutritionService.fetchNutritionData(for: Date())
        }
      }
    }
  }
}

private struct PlateIssueView: View {
  let issue: PlateLoadIssue
  let onAction: (PlateIssuePrimaryAction) -> Void
  private let localization = LocalizationManager.shared

  var body: some View {
    let action = issue.primaryAction
    VStack(spacing: 12) {
      Text(issue.title)
        .foregroundStyle(.white)
        .font(.headline)

      Text(issue.message)
        .font(.caption)
        .foregroundStyle(.white.opacity(0.85))
        .multilineTextAlignment(.center)

      if action != .none {
        Button(buttonTitle(for: action)) {
          onAction(action)
        }
        .buttonStyle(.bordered)
        .foregroundStyle(.white)
      }
    }
    .padding()
    .background(Color.surfaceElevated)
    .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    .padding(.horizontal)
  }

  private func buttonTitle(for action: PlateIssuePrimaryAction) -> String {
    switch action {
    case .none:
      return ""
    case .retry:
      return localization.localized("plate.action.retry")
    case .openProfile:
      return localization.localized("plate.action.open_profile")
    case .openProSetup:
      return localization.localized("plate.action.pro_settings")
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
          Text("\(segment.targetValue > 0 ? Int((segment.currentValue / segment.targetValue) * 100) : 0)%")
            .font(.caption)
            .bold()
            .foregroundStyle(.white)
        }

        ProgressView(value: max(0, min(segment.currentValue, segment.targetValue)), total: segment.targetValue > 0 ? segment.targetValue : 1)
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
    .background(Color.surfaceElevated)
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
