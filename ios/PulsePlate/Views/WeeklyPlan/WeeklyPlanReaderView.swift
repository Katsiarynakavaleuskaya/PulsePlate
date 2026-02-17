import SwiftUI

/// Reference MVVM View implementation for backend-driven screens
/// Demonstrates: State-based rendering, ViewModel injection, proper lifecycle
///
/// Main Weekly Plan Reader screen
/// Read-only viewer for generated meal plans with day navigation
struct WeeklyPlanReaderView: View {
    @State private var vm: WeeklyPlanReaderViewModel

    init(vm: WeeklyPlanReaderViewModel) {
        _vm = State(initialValue: vm)
    }

    var body: some View {
        content
            .navigationTitle("Weekly Plan")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        // TODO: Share (future)
                    } label: {
                        Image(systemName: "square.and.arrow.up")
                    }
                    .disabled(!canShare)
                    .accessibilityLabel("Share weekly plan")
                }
            }
            .task { await ensureLoadedOnce() }
    }

    private var canShare: Bool {
        if case .loaded = vm.state { return true }
        return false
    }

    @MainActor
    private func ensureLoadedOnce() async {
        // Protection from duplicate .task calls on view recreation
        if case .idle = vm.state {
            vm.load()
        }
    }

    @ViewBuilder
    private var content: some View {
        switch vm.state {
        case .idle:
            EmptyPlanView { vm.load() }

        case .loading:
            WeeklyPlanSkeletonView()

        case .empty:
            EmptyPlanView { vm.load() }

        case .failed(let message):
            ErrorPlanView(message: message) { vm.retry() }

        case .loaded(let plan):
            LoadedPlanView(plan: plan, vm: vm)
        }
    }
}

// MARK: - Loaded Plan View
private struct LoadedPlanView: View {
    let plan: WeeklyPlanVM
    @Bindable var vm: WeeklyPlanReaderViewModel

    init(plan: WeeklyPlanVM, vm: WeeklyPlanReaderViewModel) {
        self.plan = plan
        self._vm = Bindable(wrappedValue: vm)
    }

    var currentDay: DayPlanVM? {
        guard vm.currentDayIndex < plan.days.count else { return nil }
        return plan.days[vm.currentDayIndex]
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                // Day Navigator
                DayNavigatorView(
                    dayTitle: currentDay?.title ?? "Day",
                    dayIndex: vm.currentDayIndex,
                    totalDays: plan.days.count,
                    onPrevious: { vm.prevDay(totalDays: plan.days.count) },
                    onNext: { vm.nextDay(totalDays: plan.days.count) }
                )
                .padding(.horizontal)

                if let day = currentDay {
                    // Meal Sections
                    ForEach(day.meals) { meal in
                        MealSectionView(section: meal)
                            .padding(.horizontal)
                    }

                    // Daily Summary
                    if let totals = day.totals {
                        DailySummaryView(macros: totals)
                            .padding(.horizontal)
                    }

                    // Weekly Coverage (Collapsible)
                    if !plan.weeklyCoverage.isEmpty {
                        WeeklyCoverageView(
                            coverage: plan.weeklyCoverage,
                            isExpanded: vm.isCoverageExpanded,
                            onToggle: { vm.toggleCoverage() }
                        )
                        .padding(.horizontal)
                    }

                    // Plan Metrics
                    if let metrics = plan.metrics {
                        PlanMetricsView(
                            cost: metrics.totalCost,
                            adherence: metrics.adherenceScore,
                            shoppingListCount: plan.shoppingList?.count ?? 0
                        )
                        .padding(.horizontal)
                    }

                    // VIP CTAs
                    VipCTASection()
                        .padding(.top, 6)
                } else {
                    Text("No day data")
                        .foregroundStyle(.secondary)
                        .padding()
                }
            }
            .padding(.bottom, 20)
        }
    }
}

// MARK: - VIP CTA Section
private struct VipCTASection: View {
    var body: some View {
        VStack(spacing: 10) {
            Button {
                // TODO: VIP gate → Shopping List
            } label: {
                HStack {
                    Text("🛒 Get Shopping List")
                    Spacer()
                    Text("VIP").foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal)
            .disabled(true)
            .accessibilityHint("VIP feature")

            Button {
                // TODO: VIP gate → Auto-Repair
            } label: {
                HStack {
                    Text("🔧 Auto-Repair Plan")
                    Spacer()
                    Text("VIP").foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
            }
            .buttonStyle(.bordered)
            .padding(.horizontal)
            .disabled(true)
            .accessibilityHint("VIP feature")
        }
    }
}

#Preview {
    NavigationStack {
        WeeklyPlanReaderView(
            vm: WeeklyPlanReaderViewModel(
                service: MockWeeklyPlanService(),
                apiKeyProvider: { "preview" } // pragma: allowlist secret
            )
        )
    }
}

// MARK: - Mock Service (for preview)
private final class MockWeeklyPlanService: WeeklyPlanServicing {
    func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO {
        // Simulate network delay
        try? await Task.sleep(for: .milliseconds(300))

        // Return realistic mock data via JSONValue
        return WeeklyPlanDTO(
            root: .object([
                "daily_menus": .array([
                    .object([
                        "day_number": .number(1),
                        "meals": .array([
                            .object([
                                "meal_type": .string("breakfast"),
                                "title": .string("Breakfast"),
                                "kcal": .number(450),
                                "items": .array([
                                    .object([
                                        "id": .string("i1"),
                                        "name": .string("Oatmeal with berries"),
                                        "portions": .number(1.5)
                                    ]),
                                    .object([
                                        "id": .string("i2"),
                                        "name": .string("Green tea"),
                                        "portions": .number(1.0)
                                    ])
                                ])
                            ]),
                            .object([
                                "meal_type": .string("lunch"),
                                "title": .string("Lunch"),
                                "kcal": .number(650),
                                "items": .array([
                                    .object([
                                        "id": .string("i3"),
                                        "name": .string("Grilled chicken breast"),
                                        "portions": .number(1.0)
                                    ]),
                                    .object([
                                        "id": .string("i4"),
                                        "name": .string("Brown rice"),
                                        "portions": .number(1.5)
                                    ])
                                ])
                            ])
                        ]),
                        "totals": .object([
                            "kcal": .number(2000),
                            "protein_g": .number(120),
                            "fat_g": .number(70),
                            "carbs_g": .number(210)
                        ])
                    ])
                ]),
                "weekly_coverage": .object([
                    "Protein": .number(98.5),
                    "Iron": .number(95.1),
                    "Vitamin C": .number(120.2),
                    "Calcium": .number(88.4)
                ]),
                "shopping_list": .object([
                    "Oats": .number(0.5),
                    "Chicken breast": .number(1.2),
                    "Rice": .number(0.8)
                ]),
                "total_cost": .number(150.0),
                "adherence_score": .number(0.95)
            ])
        )
    }
}
