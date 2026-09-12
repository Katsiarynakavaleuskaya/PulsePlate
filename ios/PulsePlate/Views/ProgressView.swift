import SwiftUI
import Charts

struct ProgressViewPP: View {
    @StateObject private var nutritionService = NutritionService()
    @StateObject private var weeklyHealthKit = HealthKitManager()
    @ObservedObject private var localization = LocalizationManager.shared
    @State private var showProfile = false
    @State private var showProSetup = false
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                    ProgressGlassCard {
                        introductoryContent
                    }

                    NavigationLink {
                        WeeklyProgressView(hk: weeklyHealthKit)
                    } label: {
                        WeeklyProgressNavigationLabel(
                            title: localization.localized("navigation.progress.weekly")
                        )
                    }
                    .buttonStyle(.plain)

                    if nutritionService.isLoading {
                        ProgressGlassCard {
                            HStack(spacing: PPDesignTokens.Spacing.medium) {
                                ProgressView()
                                    .tint(PPDesignTokens.ColorToken.primary)
                                Text(localization.localized("progress.loading"))
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
                        ProgressGlassCard {
                            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
                                Text(localization.localized("progress.empty.title"))
                                    .font(PPDesignTokens.Typography.title)
                                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                                Text(localization.localized("progress.empty.detail"))
                                    .font(PPDesignTokens.Typography.caption)
                                    .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                                PPButton(localization.localized("progress.action.refresh"), variant: .primary) {
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
            .toolbarBackground(.visible, for: .navigationBar)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .navigationDestination(isPresented: $showProfile) {
                ProfileView()
            }
            .navigationDestination(isPresented: $showProSetup) {
                ProfileView()
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
            Image(ppRequiredBundleAsset: "FitChefActionProgressTracking")
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

        return ProgressGlassCard {
            HStack {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xSmall) {
                    Text(localization.localized("progress.label"))
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

        return ProgressGlassCard {
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
                .chartXAxis {
                    AxisMarks { _ in
                        AxisGridLine()
                            .foregroundStyle(PPDesignTokens.ColorToken.strokeSubtle)
                        AxisTick()
                            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                        AxisValueLabel()
                            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                    }
                }
                .chartYAxis {
                    AxisMarks { _ in
                        AxisGridLine()
                            .foregroundStyle(PPDesignTokens.ColorToken.strokeSubtle)
                        AxisTick()
                            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                        AxisValueLabel()
                            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                    }
                }
                .chartYScale(domain: 0 ... 1)
                .frame(height: 220)
            }
        }
    }

    private func segmentListCard(nutritionData: NutritionData) -> some View {
        let segments = indexedSegments(nutritionData.segments)

        return ProgressGlassCard {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
                Text(localization.localized("navigation.tab.today"))
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
        ProgressGlassCard {
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
                    PPButton(localization.localized("plate.action.retry"), variant: .primary) {
                        Task { await nutritionService.fetchNutritionData(for: Date()) }
                    }
                case .openProfile:
                    PPButton(localization.localized("plate.action.open_profile"), variant: .secondary) {
                        showProfile = true
                    }
                case .openProSetup:
                    PPButton(localization.localized("plate.action.pro_settings"), variant: .secondary) {
                        showProSetup = true
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

struct WeeklyProgressNavigationLabel: View {
    let title: String
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    @ScaledMetric(relativeTo: .headline) private var titleSize =
        PPDesignTokens.Typography.sizeLG

    init(title: String) {
        self.title = title
    }

    var body: some View {
        ProgressGlassCard {
            Group {
                if dynamicTypeSize.isAccessibilitySize {
                    VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
                        HStack {
                            calendar
                            Spacer(minLength: PPDesignTokens.Spacing.small)
                            chevron
                        }
                        titleLabel
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                } else {
                    HStack(spacing: PPDesignTokens.Spacing.medium) {
                        calendar
                        titleLabel
                        Spacer(minLength: PPDesignTokens.Spacing.small)
                        chevron
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(title)
    }

    private var calendar: some View {
        Image(systemName: "calendar")
            .font(.system(size: titleSize, weight: .semibold))
            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
            .accessibilityHidden(true)
    }

    private var titleLabel: some View {
        Text(title)
            .font(.system(size: titleSize, weight: .semibold))
            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
            .lineLimit(nil)
            .multilineTextAlignment(.leading)
            .fixedSize(horizontal: false, vertical: true)
            .layoutPriority(1)
    }

    private var chevron: some View {
        Image(systemName: "chevron.forward")
            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
            .accessibilityHidden(true)
    }
}

private struct ProgressGlassCard<Content: View>: View {
    @Environment(\.colorScheme) private var contentColorScheme
    private let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        GlassCard {
            content.environment(\.colorScheme, contentColorScheme)
        }
        .environment(\.colorScheme, .dark)
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
