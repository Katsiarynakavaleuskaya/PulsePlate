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
  @ObservedObject private var localization = LocalizationManager.shared
  @Environment(\.horizontalSizeClass) private var horizontalSizeClass
  @Environment(\.dynamicTypeSize) private var dynamicTypeSize

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
    localization.localized(key)
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
    // PlateSegments uses a fixed 280-point drawing canvas. Constrain its
    // proposal here so a wide iPad does not separate the paths from the circles.
    .frame(width: PlateVisualLayout.segmentCanvasSide, height: PlateVisualLayout.segmentCanvasSide)

    if isAppStoreScreenshotMode {
      return AnyView(content)
    }

    return AnyView(content.slideIn(isActive: !nutritionService.isLoading, delay: 0.2))
  }

  private var plateRingView: some View {
    let content = PlateRing(progress: progress)
      .environment(\.locale, Locale(identifier: localization.currentLanguage))

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
        VStack(spacing: PPDesignTokens.Spacing.xLarge) {
          // Header
          VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
            Text(localized("plate.preview.title"))
              .font(PPDesignTokens.Typography.largeTitle)
              .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
            Text(localized("plate.preview.subtitle"))
              .font(PPDesignTokens.Typography.body)
              .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
          }
          .frame(maxWidth: .infinity, alignment: .leading)
          .padding(.horizontal)

          plateHeroImage

          // Loading state
          if nutritionService.isLoading {
            ProgressView("Loading nutrition data...")
              .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
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
          VStack(spacing: PPDesignTokens.Spacing.large) {
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
        .padding(.bottom, PPDesignTokens.Spacing.medium)
      }
      .background(PPDesignTokens.Brand.navy.ignoresSafeArea())
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
        VStack(spacing: PPDesignTokens.Spacing.medium) {
          HStack(spacing: PPDesignTokens.Spacing.large) {
            PPButton(localized("plate.preview.add_meal"), variant: .secondary, fullWidth: true) {
              handlePrimaryCTA(.addMeal)
            }
            .accessibilityIdentifier("appstore.plate.add_meal")

            PPButton(localized("plate.preview.view_details"), variant: .primary, fullWidth: true) {
              handlePrimaryCTA(.viewDetails)
            }
            .accessibilityIdentifier("appstore.plate.view_details")
          }
          .padding(.horizontal)
        }
        .padding(PPDesignTokens.Spacing.large)
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: PPDesignTokens.Radius.xLarge, style: .continuous))
        .padding(.horizontal)
        .padding(.bottom, PPDesignTokens.Spacing.small)
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

  private var plateHeroImage: some View {
    ZStack(alignment: .bottomTrailing) {
      Image(ppRequiredBundleAsset: "photo-daily-plate-salmon-v1.jpg")
        .resizable()
        .scaledToFill()
        .scaleEffect(
          PlateVisualLayout.heroZoom,
          anchor: UnitPoint(x: PlateVisualLayout.heroFocalX, y: PlateVisualLayout.heroFocalY)
        )
        .frame(width: plateHeroSide, height: plateHeroSide)
        .clipped()
        .clipShape(
          RoundedRectangle(
            cornerRadius: PPDesignTokens.Radius.xLarge,
            style: .continuous
          )
        )
        .accessibilityHidden(true)

      Image("FitChefActionNutritionPlate")
        .renderingMode(.original)
        .resizable()
        .scaledToFill()
        .scaleEffect(
          PlateVisualLayout.medallionZoom,
          anchor: UnitPoint(
            x: PlateVisualLayout.medallionFocalX,
            y: PlateVisualLayout.medallionFocalY
          )
        )
        .frame(
          width: PlateVisualLayout.medallionSide,
          height: PlateVisualLayout.medallionSide
        )
        .clipped()
        .clipShape(Circle())
        .overlay(
          Circle()
            .stroke(PPDesignTokens.ColorToken.strokeSubtle, lineWidth: 1)
        )
        .padding(PPDesignTokens.Spacing.small)
        .accessibilityHidden(true)
    }
  }

  private var plateHeroSide: CGFloat {
    horizontalSizeClass == .regular && !dynamicTypeSize.isAccessibilitySize
      ? PlateVisualLayout.regularHeroSide
      : PlateVisualLayout.compactHeroSide
  }
}

private enum PlateVisualLayout {
  static let segmentCanvasSide: CGFloat = 280
  static let compactHeroSide: CGFloat = 178
  static let regularHeroSide: CGFloat = 270
  static let heroFocalX: CGFloat = 0.42
  static let heroFocalY: CGFloat = 0.5
  static let heroZoom: CGFloat = 1.02
  static let medallionSide: CGFloat = 52
  static let medallionFocalX: CGFloat = 0.5
  static let medallionFocalY: CGFloat = 0.38
  static let medallionZoom: CGFloat = 1.08
}

private struct PlateIssueView: View {
  let issue: PlateLoadIssue
  let onAction: (PlateIssuePrimaryAction) -> Void
  private let localization = LocalizationManager.shared

  var body: some View {
    let action = issue.primaryAction
    VStack(spacing: PPDesignTokens.Spacing.medium) {
      Text(issue.title)
        .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
        .font(PPDesignTokens.Typography.title)

      Text(issue.message)
        .font(PPDesignTokens.Typography.caption)
        .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
        .multilineTextAlignment(.center)

      if action != .none {
        PPButton(buttonTitle(for: action), variant: .secondary) {
          onAction(action)
        }
      }
    }
    .padding(PPDesignTokens.Spacing.large)
    .background(PPDesignTokens.ColorToken.surfaceElevated)
    .clipShape(RoundedRectangle(cornerRadius: PPDesignTokens.Radius.large, style: .continuous))
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
    VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
      HStack {
        Image(systemName: segment.icon)
          .foregroundColor(segment.color)
          .font(.title2)

        VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xSmall) {
          Text(segment.name)
            .font(PPDesignTokens.Typography.heading)
            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)

          Text("\(Int(segment.percentage))% of your plate")
            .font(PPDesignTokens.Typography.caption)
            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
        }

        Spacer()
      }

      // Progress bar
      VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
        HStack {
          Text("Progress")
            .font(PPDesignTokens.Typography.caption)
            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
          Spacer()
          Text("\(segment.targetValue > 0 ? Int((segment.currentValue / segment.targetValue) * 100) : 0)%")
            .font(PPDesignTokens.Typography.captionStrong)
            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
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
            .foregroundStyle(PPDesignTokens.ColorToken.textTertiary)
          Text("\(segment.currentValue, specifier: "%.1f") servings")
            .font(PPDesignTokens.Typography.captionStrong)
            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
        }

        Spacer()

        VStack(alignment: .trailing) {
          Text("Target")
            .font(.caption2)
            .foregroundStyle(PPDesignTokens.ColorToken.textTertiary)
          Text("\(segment.targetValue, specifier: "%.1f") servings")
            .font(PPDesignTokens.Typography.captionStrong)
            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
        }
      }
    }
    .padding(PPDesignTokens.Spacing.large)
    .background(PPDesignTokens.ColorToken.surfaceElevated)
    .cornerRadius(PPDesignTokens.Radius.large)
    .overlay(
      RoundedRectangle(cornerRadius: PPDesignTokens.Radius.large)
        .stroke(segment.color.opacity(0.3), lineWidth: 1)
    )
  }
}

struct ProgressItem: View {
  let title: String
  let value: Double
  let color: Color

  var body: some View {
    VStack(spacing: PPDesignTokens.Spacing.xSmall) {
      Text(title)
        .font(PPDesignTokens.Typography.caption)
        .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)

      ZStack {
        Circle()
          .stroke(PPDesignTokens.ColorToken.strokeSubtle, lineWidth: PPDesignTokens.Spacing.xSmall)
          .frame(width: PPDesignTokens.Spacing.touchTarget, height: PPDesignTokens.Spacing.touchTarget)

        Circle()
          .trim(from: 0, to: value)
          .stroke(color, style: StrokeStyle(lineWidth: PPDesignTokens.Spacing.xSmall, lineCap: .round))
          .frame(width: PPDesignTokens.Spacing.touchTarget, height: PPDesignTokens.Spacing.touchTarget)
          .rotationEffect(.degrees(-90))

        Text("\(Int(value * 100))%")
          .font(PPDesignTokens.Typography.captionStrong)
          .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
      }
    }
  }
}

#Preview {
  PlateViewPP()
}
