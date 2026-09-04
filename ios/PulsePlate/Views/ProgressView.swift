import SwiftUI
import Charts

struct ProgressViewPP: View {
    @StateObject private var nutritionService = NutritionService()
    @ObservedObject private var localization = LocalizationManager.shared
    @State private var showProfile = false
    @State private var showProSetup = false
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                    GlassCard {
                        introductoryContent
                    }

                    if nutritionService.isLoading {
                        GlassCard {
                            HStack(spacing: PPDesignTokens.Spacing.medium) {
                                ProgressView()
                                    .tint(PPDesignTokens.ColorToken.primary)
                                Text("Loading progress data...")
                                    .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                                    .font(PPDesignTokens.Typography.body)
                            }
                        }
                    } else if let issue = nutritionService.issue {
                        issueCard(issue: issue)
                    } else if let nutritionData = nutritionService.nutritionData {
                        summaryCard(nutritionData: nutritionData)
                        segmentChartCard(nutritionData: nutritionData)
                        segmentListCard(nutritionData: nutritionData)
                    } else {
                        GlassCard {
                            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
                                Text("No progress data")
                                    .font(PPDesignTokens.Typography.title)
                                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                                Text("Configure profile + key, then refresh to load your current day.")
                                    .font(PPDesignTokens.Typography.caption)
                                    .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                                PPButton("Refresh", variant: .primary) {
                                    Task { await nutritionService.fetchNutritionData(for: Date()) }
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, PPDesignTokens.Spacing.large)
                .padding(.top, PPDesignTokens.Spacing.medium)
                .padding(.bottom, PPDesignTokens.Spacing.xLarge)
            }
            .background(PPDesignTokens.Brand.navy.ignoresSafeArea())
            .navigationTitle(localization.localized("home.action.progress.title"))
            .navigationBarTitleDisplayMode(.inline)
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
            .task {
                await nutritionService.fetchNutritionData(for: Date())
            }
        }
        .accessibilityElement(children: .contain)
    }

    private var introductoryContent: some View {
        HStack(alignment: .center, spacing: PPDesignTokens.Spacing.large) {
            introductoryCopy
            Spacer(minLength: PPDesignTokens.Spacing.small)
            introductoryVisual
        }
    }

    private var introductoryCopy: some View {
        VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
            Text(localization.localized("home.action.progress.title"))
                .font(PPDesignTokens.Typography.heading)
                .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
            Text(localization.localized("progress.summary.subtitle"))
                .font(PPDesignTokens.Typography.body)
                .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private var introductoryVisual: some View {
        if usesEndurancePhoto {
            Image(ppRequiredBundleAsset: "photo-activity-endurance-v1.jpg")
                .resizable()
                .scaledToFill()
                .scaleEffect(
                    ProgressVisualLayout.photoZoom,
                    anchor: UnitPoint(
                        x: ProgressVisualLayout.focalX,
                        y: ProgressVisualLayout.photoFocalY
                    )
                )
                .frame(
                    width: ProgressVisualLayout.photoWidth,
                    height: ProgressVisualLayout.photoHeight
                )
                .clipped()
                .clipShape(
                    RoundedRectangle(
                        cornerRadius: PPDesignTokens.Radius.large,
                        style: .continuous
                    )
                )
                .accessibilityHidden(true)
        } else {
            Image("FitChefActionProgressTracking")
                .renderingMode(.original)
                .resizable()
                .scaledToFill()
                .scaleEffect(
                    ProgressVisualLayout.mascotZoom,
                    anchor: UnitPoint(
                        x: ProgressVisualLayout.focalX,
                        y: ProgressVisualLayout.mascotFocalY
                    )
                )
                .frame(width: mascotSide, height: mascotSide)
                .clipped()
                .clipShape(Circle())
                .overlay(
                    Circle()
                        .stroke(PPDesignTokens.ColorToken.strokeSubtle, lineWidth: 1)
                )
                .accessibilityHidden(true)
        }
    }

    private var usesEndurancePhoto: Bool {
        horizontalSizeClass == .regular && !dynamicTypeSize.isAccessibilitySize
    }

    private var mascotSide: CGFloat {
        dynamicTypeSize.isAccessibilitySize
            ? ProgressVisualLayout.accessibilityMascotSide
            : ProgressVisualLayout.mascotSide
    }

    private func summaryCard(nutritionData: NutritionData) -> some View {
        let clampedProgress = min(max(nutritionData.totalProgress, 0), 1)

        return GlassCard {
            HStack {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xSmall) {
                    Text("Overall completion")
                        .font(PPDesignTokens.Typography.caption)
                        .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                    Text("\(Int((clampedProgress * 100).rounded()))%")
                        .font(PPDesignTokens.Typography.heading)
                        .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                }

                Spacer()

                ProgressView(value: clampedProgress, total: 1.0)
                    .progressViewStyle(.linear)
                    .tint(PPDesignTokens.ColorToken.success)
                    .frame(width: 140)
            }
        }
    }

    private func segmentChartCard(nutritionData: NutritionData) -> some View {
        let segments = indexedSegments(nutritionData.segments)

        return GlassCard {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
                Text(localization.localized("progress.nutrient_progress.title"))
                    .font(PPDesignTokens.Typography.title)
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)

                Chart(segments, id: \.index) { item in
                    BarMark(
                        x: .value(
                            localization.localized("progress.chart.nutrient_category"),
                            item.segment.name
                        ),
                        y: .value(
                            localization.localized("progress.chart.completion"),
                            item.segment.targetValue > 0
                                ? min(item.segment.currentValue / item.segment.targetValue, 1.0)
                                : 0
                        )
                    )
                    .foregroundStyle(Color.segmentSemanticColor(from: item.segment.color))
                }
                .chartYScale(domain: 0 ... 1)
                .frame(height: 220)
            }
        }
    }

    private func segmentListCard(nutritionData: NutritionData) -> some View {
        let segments = indexedSegments(nutritionData.segments)

        return GlassCard {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
                Text("Today")
                    .font(PPDesignTokens.Typography.title)
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)

                ForEach(segments, id: \.index) { item in
                    HStack(spacing: PPDesignTokens.Spacing.medium) {
                        Circle()
                            .fill(Color.segmentSemanticColor(from: item.segment.color))
                            .frame(width: PPDesignTokens.Spacing.small, height: PPDesignTokens.Spacing.small)
                        Text(item.segment.name)
                            .font(PPDesignTokens.Typography.body)
                            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                        Spacer()
                        Text(
                            String(
                                format: "%.1f / %.1f",
                                item.segment.currentValue,
                                item.segment.targetValue
                            )
                        )
                        .font(PPDesignTokens.Typography.caption)
                        .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                    }
                }
            }
        }
    }

    private func indexedSegments(
        _ segments: [NutritionSegmentData]
    ) -> [(index: Int, segment: NutritionSegmentData)] {
        Array(segments.enumerated()).map { (index: $0.offset, segment: $0.element) }
    }

    private func issueCard(issue: PlateLoadIssue) -> some View {
        GlassCard {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
                Text(issue.title)
                    .font(PPDesignTokens.Typography.title)
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                Text(issue.message)
                    .font(PPDesignTokens.Typography.caption)
                    .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)

                switch issue.primaryAction {
                case .none:
                    EmptyView()
                case .retry:
                    PPButton("Retry", variant: .primary) {
                        Task { await nutritionService.fetchNutritionData(for: Date()) }
                    }
                case .openProfile:
                    PPButton("Open profile", variant: .secondary) {
                        showProfile = true
                    }
                case .openProSetup:
                    PPButton("Open PRO setup", variant: .secondary) {
                        showProSetup = true
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private enum ProgressVisualLayout {
    static let photoWidth: CGFloat = 168
    static let photoHeight: CGFloat = 122
    static let photoZoom: CGFloat = 1.02
    static let mascotSide: CGFloat = 52
    static let accessibilityMascotSide: CGFloat = 56
    static let focalX: CGFloat = 0.5
    static let photoFocalY: CGFloat = 0.36
    static let mascotFocalY: CGFloat = 0.38
    static let mascotZoom: CGFloat = 1.08
}
