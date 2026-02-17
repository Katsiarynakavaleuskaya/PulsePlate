import SwiftUI

struct HomeView: View {
    private let apiClient: APIClientProtocol
    private let profileProvider: ProfileProviding

    init(
        apiClient: APIClientProtocol = APIClient(baseURL: AppConfig.baseURL()),
        profileProvider: ProfileProviding = DefaultProfileProvider()
    ) {
        self.apiClient = apiClient
        self.profileProvider = profileProvider
    }

    private var hasProKey: Bool {
        guard let key = ProKeyProvider.value() else { return false }
        return !key.isEmpty
    }

    private var hasProfile: Bool {
        profileProvider.proNutritionProfile() != nil
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                heroCard

                HStack(spacing: 12) {
                    HomeStatusCard(
                        title: "PRO Key",
                        value: hasProKey ? "Configured" : "Missing",
                        color: hasProKey ? .success : .warning
                    )

                    HomeStatusCard(
                        title: "Profile",
                        value: hasProfile ? "Ready" : "Incomplete",
                        color: hasProfile ? .success : .warning
                    )
                }

                GlassCard {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Quick actions")
                            .font(.headline)
                            .foregroundStyle(Color.textPrimary)

                        NavigationLink {
                            BMICalculatorScreen()
                        } label: {
                            HomeActionRow(
                                title: "BMI Calculator",
                                subtitle: "Update core body metrics",
                                icon: "gauge"
                            )
                        }

                        NavigationLink {
                            ProfileView()
                        } label: {
                            HomeActionRow(
                                title: "Profile Setup",
                                subtitle: "Configure PRO profile and language",
                                icon: "person.crop.circle"
                            )
                        }

                        NavigationLink {
                            PlateViewPP()
                        } label: {
                            HomeActionRow(
                                title: "Open Plate",
                                subtitle: "Review your daily nutrition split",
                                icon: "fork.knife.circle"
                            )
                        }
                    }
                }

                if FeatureFlags.weeklyPlanReaderEnabled {
                    GlassCard {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("PRO tools")
                                .font(.headline)
                                .foregroundStyle(Color.textPrimary)

                            NavigationLink {
                                makeWeeklyPlanReaderScreen()
                            } label: {
                                HomeActionRow(
                                    title: "Weekly Plan Reader",
                                    subtitle: "Review canonical /api/v1/pro/meal/weekly output",
                                    icon: "calendar.badge.clock"
                                )
                            }

                            NavigationLink {
                                makeShoppingListScreen()
                            } label: {
                                HomeActionRow(
                                    title: "Shopping List Generator",
                                    subtitle: "Build list via /api/v1/pro/meal/shopping-list",
                                    icon: "cart"
                                )
                            }
                        }
                    }
                }

                MascotBubble(textKey: "mascot.plate.hint")
            }
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 20)
        }
        .background(Color.navy.ignoresSafeArea())
        .navigationTitle("Home")
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityLabel("Home Screen")
    }

    private var heroCard: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text("PulsePlate")
                    .font(.largeTitle)
                    .bold()
                    .foregroundStyle(Color.textPrimary)

                Text("Home + Plate + Progress production slice")
                    .font(.subheadline)
                    .foregroundStyle(Color.textSecondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func makeShoppingListScreen() -> some View {
        let service = DefaultShoppingListService(apiClient: apiClient)
        let shoppingListViewModel = ShoppingListReaderViewModel(
            service: service,
            apiKeyProvider: { ProKeyProvider.value() }
        )
        return ShoppingListReaderScreen(
            vm: shoppingListViewModel,
            planData: ShoppingListStubPlan.minimal()
        )
    }

    private func makeWeeklyPlanReaderScreen() -> some View {
        let service = DefaultWeeklyPlanService(apiClient: apiClient)
        let weeklyPlanViewModel = WeeklyPlanReaderViewModel(
            service: service,
            apiKeyProvider: { ProKeyProvider.value() }
        )
        return WeeklyPlanReaderView(vm: weeklyPlanViewModel)
    }
}

private struct HomeStatusCard: View {
    let title: String
    let value: String
    let color: Color

    var body: some View {
        GlassCard(cornerRadius: 14) {
            VStack(alignment: .leading, spacing: 8) {
                Text(title)
                    .font(.caption)
                    .foregroundStyle(Color.textSecondary)

                HStack(spacing: 8) {
                    Circle()
                        .fill(color)
                        .frame(width: 8, height: 8)
                    Text(value)
                        .font(.headline)
                        .foregroundStyle(Color.textPrimary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct HomeActionRow: View {
    let title: String
    let subtitle: String
    let icon: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(Color.appPrimary)
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color.textPrimary)
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(Color.textSecondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption.bold())
                .foregroundStyle(Color.textTertiary)
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
    }
}
