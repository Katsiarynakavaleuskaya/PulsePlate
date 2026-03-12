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

    private var hasProTools: Bool {
        FeatureFlags.aiInsightEnabled || FeatureFlags.weeklyPlanReaderEnabled
    }

    private func localized(_ key: String) -> String {
        NSLocalizedString(key, comment: "")
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                heroCard

                HStack(spacing: 12) {
                    HomeStatusCard(
                        title: localized("home.status.pro_key.title"),
                        value: hasProKey
                            ? localized("home.status.pro_key.configured")
                            : localized("home.status.pro_key.missing"),
                        color: hasProKey ? .success : .warning
                    )

                    HomeStatusCard(
                        title: localized("home.status.profile.title"),
                        value: hasProfile
                            ? localized("home.status.profile.ready")
                            : localized("home.status.profile.incomplete"),
                        color: hasProfile ? .success : .warning
                    )
                }

                GlassCard {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(localized("home.section.quick_actions"))
                            .font(.headline)
                            .foregroundStyle(Color.textPrimary)

                        NavigationLink {
                            BMICalculatorScreen()
                        } label: {
                            HomeActionRow(
                                title: localized("home.action.bmi.title"),
                                subtitle: localized("home.action.bmi.subtitle"),
                                icon: "gauge"
                            )
                        }

                        NavigationLink {
                            ProfileView()
                        } label: {
                            HomeActionRow(
                                title: localized("home.action.profile_setup.title"),
                                subtitle: localized("home.action.profile_setup.subtitle"),
                                icon: "person.crop.circle"
                            )
                        }

                        NavigationLink {
                            PlateViewPP()
                        } label: {
                            HomeActionRow(
                                title: localized("home.action.open_plate.title"),
                                subtitle: localized("home.action.open_plate.subtitle"),
                                icon: "fork.knife.circle"
                            )
                        }
                    }
                }

                if hasProTools {
                    GlassCard {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(localized("home.section.pro_tools"))
                                .font(.headline)
                                .foregroundStyle(Color.textPrimary)

                            if FeatureFlags.aiInsightEnabled {
                                NavigationLink {
                                    makeAIInsightScreen()
                                } label: {
                                    HomeActionRow(
                                        title: localized("home.action.ai_insight.title"),
                                        subtitle: localized("home.action.ai_insight.subtitle"),
                                        icon: "brain.head.profile"
                                    )
                                }
                            }

                            if FeatureFlags.weeklyPlanReaderEnabled {
                                NavigationLink {
                                    makeWeeklyPlanReaderScreen()
                                } label: {
                                    HomeActionRow(
                                        title: localized("home.action.weekly_plan_reader.title"),
                                        subtitle: localized("home.action.weekly_plan_reader.subtitle"),
                                        icon: "calendar.badge.clock"
                                    )
                                }

                                NavigationLink {
                                    makeShoppingListScreen()
                                } label: {
                                    HomeActionRow(
                                        title: localized("home.action.shopping_list.title"),
                                        subtitle: localized("home.action.shopping_list.subtitle"),
                                        icon: "cart"
                                    )
                                }
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
        .navigationTitle(localized("home.navigation.title"))
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityLabel(localized("home.accessibility.screen_label"))
        .appStoreScreenshotRoot("appstore.home.screen")
    }

    private var heroCard: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text(localized("home.hero.title"))
                    .font(.largeTitle)
                    .bold()
                    .foregroundStyle(Color.textPrimary)

                Text(localized("home.hero.subtitle"))
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
        #if DEBUG
        let bootstrapPlanData: ShoppingPlan? = ShoppingListStubPlan.minimal()
        #else
        let bootstrapPlanData: ShoppingPlan? = nil
        #endif

        return ShoppingListReaderScreen(
            vm: shoppingListViewModel,
            planData: bootstrapPlanData
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

    private func makeAIInsightScreen() -> some View {
        let service = DefaultCBTInsightService(apiClient: apiClient)
        let viewModel = AIInsightViewModel(
            service: service,
            apiKeyProvider: { ProKeyProvider.value() }
        )
        return AIInsightView(vm: viewModel)
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
                        .accessibilityHidden(true)
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
                .accessibilityHidden(true)

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
                .accessibilityHidden(true)
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
    }
}
