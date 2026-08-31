import Foundation
import SwiftUI

struct HomeDestinationDependencies: Sendable {
    let makeAIService: @Sendable (APIClientProtocol) -> any CBTInsightServicing
    let makeConsentProvider: @Sendable () -> any AIWellnessConsentProviding
    let makeSupportService: @Sendable (APIClientProtocol) -> any FitChefSupportServicing
    let makeWeeklyService: @Sendable (APIClientProtocol) -> any WeeklyPlanServicing
    let makeShoppingService: @Sendable (APIClientProtocol) -> any ShoppingListServicing
    let makeClientEventID: @Sendable () -> UUID

    static var live: HomeDestinationDependencies {
        HomeDestinationDependencies(
            makeAIService: { DefaultCBTInsightService(apiClient: $0) },
            makeConsentProvider: { AIWellnessConsentStore() },
            makeSupportService: { DefaultFitChefSupportService(apiClient: $0) },
            makeWeeklyService: { DefaultWeeklyPlanService(apiClient: $0) },
            makeShoppingService: { DefaultShoppingListService(apiClient: $0) },
            makeClientEventID: { UUID() }
        )
    }
}

struct HomeView: View {
    @EnvironmentObject private var subscriptionManager: SubscriptionManager
    @ObservedObject private var localization: LocalizationManager

    private let apiClient: APIClientProtocol
    private let profileProvider: any ProfileProviding
    private let destinationDependencies: HomeDestinationDependencies

    @State private var profileReadiness: HomeProfileReadiness

    init(
        apiClient: APIClientProtocol = APIClient(baseURL: AppConfig.baseURL()),
        profileProvider: any ProfileProviding = DefaultProfileProvider(),
        destinationDependencies: HomeDestinationDependencies = .live,
        localization: LocalizationManager = .shared
    ) {
        self.apiClient = apiClient
        self.profileProvider = profileProvider
        self.destinationDependencies = destinationDependencies
        _localization = ObservedObject(wrappedValue: localization)
        _profileReadiness = State(
            initialValue: HomeExperience.profileReadiness(using: profileProvider)
        )
    }

    var body: some View {
        HomeExperienceScreen(
            state: experienceState,
            actions: actionSet,
            onRetry: retryEntitlement,
            destination: destination(for:)
        )
        .environment(\.locale, appSelectedLocale)
        .onAppear {
            refreshProfileReadiness()
        }
    }

    var appSelectedLocale: Locale {
        Locale(identifier: localization.currentLanguage)
    }

    private var experienceState: HomeExperienceState {
        HomeExperience.resolve(
            flowState: subscriptionManager.flowState,
            entitlement: subscriptionManager.entitlement,
            profileReadiness: profileReadiness
        )
    }

    private var actionSet: HomeActionSet {
        HomeExperience.actions(
            for: experienceState,
            planningToolsEnabled: FeatureFlags.weeklyPlanReaderEnabled
        )
    }

    private var coachCapabilities: [FitChefCoachCapability] {
        HomeExperience.coachCapabilities(
            aiGuidanceEnabled: FeatureFlags.aiInsightEnabled
        )
    }

    private func refreshProfileReadiness() {
        profileReadiness = HomeExperience.profileReadiness(using: profileProvider)
    }

    private func retryEntitlement() {
        Task {
            await subscriptionManager.refreshEntitlement(trigger: .manualRetry)
        }
    }

    @ViewBuilder
    private func destination(for action: HomeAction) -> some View {
        switch action {
        case .checkBMI:
            BMICalculatorScreen()
        case .profile, .completeProfile:
            ProfileView()
        case .todayPlate:
            PlateViewPP()
        case .progress:
            ProgressViewPP()
        case .fitChefCoach:
            makeFitChefCoachScreen()
        case .week:
            makeWeeklyPlanReaderScreen()
        case .shoppingList:
            makeShoppingListScreen()
        case .retry:
            EmptyView()
        }
    }

    private func makeFitChefCoachScreen() -> some View {
        FitChefCoachView(
            availability: FitChefCoachAvailability(capabilities: coachCapabilities),
            aiGuidanceDestination: {
                makeAIInsightScreen()
            },
            planningDirectionDestination: {
                makeFitChefSupportScreen()
            }
        )
    }

    private func makeAIInsightScreen() -> some View {
        let service = destinationDependencies.makeAIService(apiClient)
        let consentStore = destinationDependencies.makeConsentProvider()
        let viewModel = AIInsightViewModel(
            service: service,
            apiKeyProvider: { ProKeyProvider.value() },
            consentProvider: consentStore
        )
        return AIInsightView(vm: viewModel)
    }

    private func makeFitChefSupportScreen() -> some View {
        let service = destinationDependencies.makeSupportService(apiClient)
        let viewModel = FitChefSupportFlowViewModel(
            service: service,
            apiKeyProvider: { ProKeyProvider.value() },
            makeClientEventID: destinationDependencies.makeClientEventID
        )
        return FitChefSupportFlowScreen(viewModel: viewModel)
    }

    private func makeWeeklyPlanReaderScreen() -> some View {
        let service = destinationDependencies.makeWeeklyService(apiClient)
        let weeklyPlanViewModel = WeeklyPlanReaderViewModel(
            service: service,
            apiKeyProvider: { ProKeyProvider.value() }
        )
        return WeeklyPlanReaderView(vm: weeklyPlanViewModel)
    }

    private func makeShoppingListScreen() -> some View {
        let service = destinationDependencies.makeShoppingService(apiClient)
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
}
