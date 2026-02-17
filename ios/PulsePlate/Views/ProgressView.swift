import SwiftUI
import Charts

struct ProgressViewPP: View {
    @StateObject private var nutritionService = NutritionService()
    @State private var showProfile = false
    @State private var showProSetup = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    GlassCard {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Progress")
                                .font(.title.bold())
                                .foregroundStyle(Color.textPrimary)
                            Text("Track daily nutrition completion and segment balance.")
                                .font(.subheadline)
                                .foregroundStyle(Color.textSecondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    if nutritionService.isLoading {
                        GlassCard {
                            HStack(spacing: 10) {
                                ProgressView()
                                    .tint(Color.appPrimary)
                                Text("Loading progress data...")
                                    .foregroundStyle(Color.textSecondary)
                                    .font(.subheadline)
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
                            VStack(alignment: .leading, spacing: 10) {
                                Text("No progress data")
                                    .font(.headline)
                                    .foregroundStyle(Color.textPrimary)
                                Text("Configure profile + key, then refresh to load your current day.")
                                    .font(.caption)
                                    .foregroundStyle(Color.textSecondary)
                                Button("Refresh") {
                                    Task { await nutritionService.fetchNutritionData(for: Date()) }
                                }
                                .buttonStyle(.borderedProminent)
                            }
                        }
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 12)
                .padding(.bottom, 20)
            }
            .background(Color.navy.ignoresSafeArea())
            .navigationTitle("Progress")
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

    private func summaryCard(nutritionData: NutritionData) -> some View {
        GlassCard {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Overall completion")
                        .font(.caption)
                        .foregroundStyle(Color.textSecondary)
                    Text("\(Int((nutritionData.totalProgress * 100).rounded()))%")
                        .font(.title2.bold())
                        .foregroundStyle(Color.textPrimary)
                }

                Spacer()

                ProgressView(value: nutritionData.totalProgress, total: 1.0)
                    .progressViewStyle(.linear)
                    .tint(Color.success)
                    .frame(width: 140)
            }
        }
    }

    private func segmentChartCard(nutritionData: NutritionData) -> some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text("Segment progress")
                    .font(.headline)
                    .foregroundStyle(Color.textPrimary)

                Chart(nutritionData.segments, id: \.name) { segment in
                    BarMark(
                        x: .value("Segment", segment.name),
                        y: .value(
                            "Completion",
                            segment.targetValue > 0 ? min(segment.currentValue / segment.targetValue, 1.0) : 0
                        )
                    )
                    .foregroundStyle(colorFromString(segment.color))
                }
                .chartYScale(domain: 0 ... 1)
                .frame(height: 220)
            }
        }
    }

    private func segmentListCard(nutritionData: NutritionData) -> some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 10) {
                Text("Today")
                    .font(.headline)
                    .foregroundStyle(Color.textPrimary)

                ForEach(nutritionData.segments, id: \.name) { segment in
                    HStack(spacing: 10) {
                        Circle()
                            .fill(colorFromString(segment.color))
                            .frame(width: 8, height: 8)
                        Text(segment.name)
                            .font(.subheadline)
                            .foregroundStyle(Color.textPrimary)
                        Spacer()
                        Text(String(format: "%.1f / %.1f", segment.currentValue, segment.targetValue))
                        .font(.caption)
                        .foregroundStyle(Color.textSecondary)
                    }
                }
            }
        }
    }

    private func issueCard(issue: PlateLoadIssue) -> some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 10) {
                Text(issue.title)
                    .font(.headline)
                    .foregroundStyle(Color.textPrimary)
                Text(issue.message)
                    .font(.caption)
                    .foregroundStyle(Color.textSecondary)

                switch issue.primaryAction {
                case .none:
                    EmptyView()
                case .retry:
                    Button("Retry") {
                        Task { await nutritionService.fetchNutritionData(for: Date()) }
                    }
                    .buttonStyle(.borderedProminent)
                case .openProfile:
                    Button("Open profile") {
                        showProfile = true
                    }
                    .buttonStyle(.bordered)
                case .openProSetup:
                    Button("Open PRO setup") {
                        showProSetup = true
                    }
                    .buttonStyle(.bordered)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func colorFromString(_ colorString: String) -> Color {
        switch colorString.lowercased() {
        case "green":
            return .success
        case "red":
            return .heart
        case "orange":
            return .warning
        case "yellow":
            return .warning
        case "blue":
            return .appPrimary
        case "purple":
            return .appPrimary
        default:
            return .textTertiary
        }
    }
}
