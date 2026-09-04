import SwiftUI
import Charts

struct ProgressViewPP: View {
    @StateObject private var nutritionService = NutritionService()
    @ObservedObject private var localization = LocalizationManager.shared
    @State private var showProfile = false
    @State private var showProSetup = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                    GlassCard {
                        VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
                            Text("Progress")
                                .font(PPDesignTokens.Typography.heading)
                                .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                            Text("Track daily nutrition completion and segment balance.")
                                .font(PPDesignTokens.Typography.body)
                                .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    NavigationLink {
                        WeeklyProgressView()
                    } label: {
                        WeeklyProgressNavigationLabel(
                            title: localization.localized("navigation.progress.weekly")
                        )
                    }
                    .buttonStyle(.plain)

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
            .navigationTitle("Progress")
            .navigationBarTitleDisplayMode(.inline)
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
                Text("Segment progress")
                    .font(PPDesignTokens.Typography.title)
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)

                Chart(segments, id: \.index) { item in
                    BarMark(
                        x: .value("Segment", item.segment.name),
                        y: .value(
                            "Completion",
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

struct WeeklyProgressNavigationLabel: View {
    let title: String

    @ScaledMetric(relativeTo: .headline) private var titleSize =
        PPDesignTokens.Typography.sizeLG

    init(title: String) {
        self.title = title
    }

    var body: some View {
        GlassCard {
            HStack(spacing: PPDesignTokens.Spacing.medium) {
                Image(systemName: "calendar")
                    .font(.system(size: titleSize, weight: .semibold))
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                    .accessibilityHidden(true)

                Text(title)
                    .font(.system(size: titleSize, weight: .semibold))
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                    .lineLimit(nil)
                    .multilineTextAlignment(.leading)
                    .fixedSize(horizontal: false, vertical: true)
                    .layoutPriority(1)

                Spacer(minLength: PPDesignTokens.Spacing.small)

                Image(systemName: "chevron.forward")
                    .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                    .accessibilityHidden(true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(title)
    }
}
