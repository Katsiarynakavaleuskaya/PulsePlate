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
        guard let key = AppStoreScreenshotContext.previewProKey ?? ProKeyProvider.value() else { return false }
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
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                heroCard

                HStack(spacing: PPDesignTokens.Spacing.medium) {
                    HomeStatusCard(
                        title: localized("home.status.pro_key.title"),
                        value: hasProKey
                            ? localized("home.status.pro_key.configured")
                            : localized("home.status.pro_key.missing"),
                        color: hasProKey
                            ? PPDesignTokens.ColorToken.success
                            : PPDesignTokens.ColorToken.warning
                    )

                    HomeStatusCard(
                        title: localized("home.status.profile.title"),
                        value: hasProfile
                            ? localized("home.status.profile.ready")
                            : localized("home.status.profile.incomplete"),
                        color: hasProfile
                            ? PPDesignTokens.ColorToken.success
                            : PPDesignTokens.ColorToken.warning
                    )
                }

                GlassCard {
                    VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
                        Text(localized("home.section.quick_actions"))
                            .font(PPDesignTokens.Typography.title)
                            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)

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
                        VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.medium) {
                            Text(localized("home.section.pro_tools"))
                                .font(PPDesignTokens.Typography.title)
                                .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)

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
            .padding(.horizontal, PPDesignTokens.Spacing.large)
            .padding(.top, PPDesignTokens.Spacing.medium)
            .padding(.bottom, PPDesignTokens.Spacing.xLarge)
        }
        .background(PPDesignTokens.Brand.navy.ignoresSafeArea())
        .navigationTitle(localized("home.navigation.title"))
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityLabel(localized("home.accessibility.screen_label"))
    }

    private var heroCard: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
                Text(localized("home.hero.title"))
                    .font(PPDesignTokens.Typography.largeTitle)
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)

                Text(localized("home.hero.subtitle"))
                    .font(PPDesignTokens.Typography.body)
                    .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
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
        let consentStore = AIWellnessConsentStore()
        let viewModel = AIInsightViewModel(
            service: service,
            apiKeyProvider: { ProKeyProvider.value() },
            consentProvider: consentStore
        )
        return AIInsightView(vm: viewModel)
    }
}

private struct HomeStatusCard: View {
    let title: String
    let value: String
    let color: Color

    var body: some View {
        GlassCard(
            cornerRadius: PPDesignTokens.Radius.large,
            contentPadding: PPDesignTokens.Spacing.large,
            strokeColor: PPDesignTokens.ColorToken.strokeSubtle
        ) {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
                Text(title)
                    .font(PPDesignTokens.Typography.caption)
                    .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)

                HStack(spacing: PPDesignTokens.Spacing.small) {
                    Circle()
                        .fill(color)
                        .frame(width: PPDesignTokens.Spacing.small, height: PPDesignTokens.Spacing.small)
                        .accessibilityHidden(true)
                    Text(value)
                        .font(PPDesignTokens.Typography.title)
                        .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
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
        HStack(spacing: PPDesignTokens.Spacing.medium) {
            Image(systemName: icon)
                .foregroundStyle(PPDesignTokens.ColorToken.primary)
                .frame(width: PPDesignTokens.Spacing.xLarge)
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xSmall) {
                Text(title)
                    .font(PPDesignTokens.Typography.bodyStrong)
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                Text(subtitle)
                    .font(PPDesignTokens.Typography.caption)
                    .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption.bold())
                .foregroundStyle(PPDesignTokens.ColorToken.textTertiary)
                .accessibilityHidden(true)
        }
        .padding(.vertical, PPDesignTokens.Spacing.xSmall)
        .contentShape(Rectangle())
    }
}
