import Foundation
import SwiftUI
import XCTest
@testable import PulsePlate

@MainActor
final class HomeExperienceTests: XCTestCase {
    private let exactHomeLocalizationKeys: Set<String> = [
        "home.accessibility.screen_label",
        "home.action.bmi.detail",
        "home.action.bmi.title",
        "home.action.coach.detail",
        "home.action.coach.title",
        "home.action.complete_profile.detail",
        "home.action.complete_profile.title",
        "home.action.profile.detail",
        "home.action.profile.title",
        "home.action.progress.detail",
        "home.action.progress.title",
        "home.action.retry.title",
        "home.action.shopping.detail",
        "home.action.shopping.title",
        "home.action.today.detail",
        "home.action.today.title",
        "home.action.week.detail",
        "home.action.week.title",
        "home.navigation.title",
        "home.state.free_ready.detail",
        "home.state.free_ready.title",
        "home.state.loading.detail",
        "home.state.loading.title",
        "home.state.paid_needs_profile.detail",
        "home.state.paid_needs_profile.title",
        "home.state.paid_ready.detail",
        "home.state.paid_ready.title",
        "home.state.unavailable.detail",
        "home.state.unavailable.title",
    ]

    func testEveryInProgressFlowStateProjectsToLoading() {
        for flowState in [
            SubscriptionFlowState.purchasing,
            .sendingReceipt,
            .refreshingEntitlement,
            .restoring,
            .pendingApproval,
        ] {
            for entitlement in [nil, entitlementSnapshot(status: "active")] {
                for readiness in [
                    HomeProfileReadiness.missingRequiredInputs,
                    .readyForBackendValidation,
                ] {
                    XCTAssertEqual(
                        HomeExperience.resolve(
                            flowState: flowState,
                            entitlement: entitlement,
                            profileReadiness: readiness
                        ),
                        .loading,
                        "Unexpected projection for \(flowState), \(String(describing: entitlement)), \(readiness)"
                    )
                }
            }
        }
    }

    func testIdleWithoutSnapshotIsFreeRegardlessOfLocalProfileReadiness() {
        for readiness in [
            HomeProfileReadiness.missingRequiredInputs,
            .readyForBackendValidation,
        ] {
            XCTAssertEqual(
                HomeExperience.resolve(
                    flowState: .idle,
                    entitlement: nil,
                    profileReadiness: readiness
                ),
                .freeReady
            )
        }
    }

    func testUnlockedActiveOrRestoredSnapshotUsesOnlyLocalProfileReadiness() {
        for status in ["active", "restored", " ACTIVE ", "Restored"] {
            XCTAssertEqual(
                HomeExperience.resolve(
                    flowState: .unlocked,
                    entitlement: entitlementSnapshot(status: status),
                    profileReadiness: .missingRequiredInputs
                ),
                .paidNeedsProfile,
                status
            )
            XCTAssertEqual(
                HomeExperience.resolve(
                    flowState: .unlocked,
                    entitlement: entitlementSnapshot(status: status),
                    profileReadiness: .readyForBackendValidation
                ),
                .paidReady,
                status
            )
        }
    }

    func testInconsistentOrUnsupportedTerminalInputsFailClosed() {
        for readiness in [
            HomeProfileReadiness.missingRequiredInputs,
            .readyForBackendValidation,
        ] {
            XCTAssertEqual(
                HomeExperience.resolve(
                    flowState: .idle,
                    entitlement: entitlementSnapshot(status: "active"),
                    profileReadiness: readiness
                ),
                .unavailable
            )
            XCTAssertEqual(
                HomeExperience.resolve(
                    flowState: .unlocked,
                    entitlement: nil,
                    profileReadiness: readiness
                ),
                .unavailable
            )
            XCTAssertEqual(
                HomeExperience.resolve(
                    flowState: .failed("opaque internal diagnostic"),
                    entitlement: nil,
                    profileReadiness: readiness
                ),
                .unavailable
            )

            for status in ["", " ", "pending", "expired", "active-now", "restored_later"] {
                XCTAssertEqual(
                    HomeExperience.resolve(
                        flowState: .unlocked,
                        entitlement: entitlementSnapshot(status: status),
                        profileReadiness: readiness
                    ),
                    .unavailable,
                    status
                )
            }
        }
    }

    func testEntitlementMetadataDoesNotChangePaidProjection() {
        let snapshots = [
            EntitlementSnapshot(
                activationID: "",
                tier: "",
                status: "active",
                expiresAt: .distantPast,
                productID: nil
            ),
            EntitlementSnapshot(
                activationID: "opaque-id",
                tier: "unexpected-tier",
                status: "active",
                expiresAt: .distantFuture,
                productID: "unexpected-product"
            ),
        ]

        for snapshot in snapshots {
            XCTAssertEqual(
                HomeExperience.resolve(
                    flowState: .unlocked,
                    entitlement: snapshot,
                    profileReadiness: .readyForBackendValidation
                ),
                .paidReady
            )
        }
    }

    func testProfileReadinessUsesExistingProfileProviderWithoutAddingTruth() {
        let provider = MutableHomeProfileProvider(profile: nil)
        XCTAssertEqual(
            HomeExperience.profileReadiness(using: provider),
            .missingRequiredInputs
        )

        provider.profile = ProNutritionProfile(
            sex: .female,
            age: 35,
            heightCm: 168,
            weightKg: 65,
            activity: .moderate,
            goal: .maintain
        )
        XCTAssertEqual(
            HomeExperience.profileReadiness(using: provider),
            .readyForBackendValidation
        )
        XCTAssertEqual(provider.readCount, 2)
    }

    func testExactActionProjectionForEveryStateAndPlanningFlag() {
        let expected: [HomeExperienceState: (HomeActionSet, HomeActionSet)] = [
            .loading: (
                HomeActionSet(primary: nil, secondary: []),
                HomeActionSet(primary: nil, secondary: [])
            ),
            .freeReady: (
                HomeActionSet(primary: .checkBMI, secondary: [.profile, .progress]),
                HomeActionSet(primary: .checkBMI, secondary: [.profile, .progress])
            ),
            .paidNeedsProfile: (
                HomeActionSet(primary: .completeProfile, secondary: [.checkBMI, .progress]),
                HomeActionSet(primary: .completeProfile, secondary: [.checkBMI, .progress])
            ),
            .paidReady: (
                HomeActionSet(primary: .todayPlate, secondary: [.fitChefCoach]),
                HomeActionSet(
                    primary: .todayPlate,
                    secondary: [.fitChefCoach, .week, .shoppingList]
                )
            ),
            .unavailable: (
                HomeActionSet(primary: .retry, secondary: [.checkBMI, .profile]),
                HomeActionSet(primary: .retry, secondary: [.checkBMI, .profile])
            ),
        ]

        for state in HomeExperienceState.allCases {
            let pair = expected[state]
            XCTAssertEqual(
                HomeExperience.actions(for: state, planningToolsEnabled: false),
                pair?.0,
                "flag off: \(state)"
            )
            XCTAssertEqual(
                HomeExperience.actions(for: state, planningToolsEnabled: true),
                pair?.1,
                "flag on: \(state)"
            )
        }

        for state in HomeExperienceState.allCases {
            for planningToolsEnabled in [false, true] {
                let actions = HomeExperience.actions(
                    for: state,
                    planningToolsEnabled: planningToolsEnabled
                )
                XCTAssertLessThanOrEqual(actions.secondary.count, 3)
                XCTAssertEqual(
                    actions.secondary.filter { $0 == .fitChefCoach }.count,
                    state == .paidReady ? 1 : 0
                )
                if state != .paidReady {
                    XCTAssertFalse(actions.secondary.contains(.week))
                    XCTAssertFalse(actions.secondary.contains(.shoppingList))
                }
            }
        }
    }

    func testCoachCapabilityProjectionKeepsPlanningAndGatesOnlyAI() {
        XCTAssertEqual(
            HomeExperience.coachCapabilities(aiGuidanceEnabled: false),
            [.planningDirection]
        )
        XCTAssertEqual(
            HomeExperience.coachCapabilities(aiGuidanceEnabled: true),
            [.aiGuidance, .planningDirection]
        )
    }

    func testOrdinaryRenderEvaluatesNeitherDestinationsNorRetry() throws {
        for state in HomeExperienceState.allCases {
            let probe = HomeRenderProbe()
            let screen = makeScreen(
                state: state,
                planningToolsEnabled: true,
                probe: probe
            )
            let renderer = ImageRenderer(
                content: screen
                    .environment(\.locale, Locale(identifier: "en"))
                    .frame(width: 390, height: 844)
            )
            renderer.scale = 1
            renderer.proposedSize = ProposedViewSize(width: 390, height: 844)

            let image = try XCTUnwrap(renderer.uiImage, "Render failed for \(state)")
            XCTAssertGreaterThan(image.size.width, 0)
            XCTAssertGreaterThan(image.size.height, 0)
            XCTAssertEqual(probe.destinationBuildCount, 0, "Eager destination: \(state)")
            XCTAssertEqual(probe.retryCount, 0, "Eager retry: \(state)")
        }
    }

    func testAllMaterialStatesRenderAcrossCompactLargeTabletAndAccessibilityLayouts() throws {
        let configurations: [(CGFloat, CGFloat, UserInterfaceSizeClass, DynamicTypeSize)] = [
            (390, 844, .compact, .large),
            (430, 932, .compact, .large),
            (834, 1194, .regular, .large),
            (390, 844, .compact, .accessibility5),
        ]

        for state in HomeExperienceState.allCases {
            for (width, height, sizeClass, dynamicTypeSize) in configurations {
                let probe = HomeRenderProbe()
                let screen = makeScreen(
                    state: state,
                    planningToolsEnabled: true,
                    probe: probe
                )
                let content = screen
                    .environment(\.locale, Locale(identifier: "en"))
                    .environment(\.horizontalSizeClass, sizeClass)
                    .dynamicTypeSize(dynamicTypeSize)
                    .frame(width: width, height: height)
                let renderer = ImageRenderer(content: content)
                renderer.scale = 1
                renderer.proposedSize = ProposedViewSize(width: width, height: height)

                let image = try XCTUnwrap(
                    renderer.uiImage,
                    "Render failed for \(state), \(width)x\(height), \(dynamicTypeSize)"
                )
                XCTAssertGreaterThan(image.size.width, 0)
                XCTAssertGreaterThan(image.size.height, 0)
                XCTAssertEqual(probe.destinationBuildCount, 0)
                XCTAssertEqual(probe.retryCount, 0)
            }
        }
    }

    func testRealHomeViewUsesAppSelectedLocaleInsteadOfOuterDeviceLocale() throws {
        let localization = LocalizationManager.shared
        let originalLanguage = localization.currentLanguage
        defer { localization.currentLanguage = originalLanguage }
        let profileProvider = MutableHomeProfileProvider(profile: nil)
        let apiClient = HomeNoCallAPIClient()
        let destinationProbe = HomeDestinationFactoryProbe()
        let home = HomeView(
            apiClient: apiClient,
            profileProvider: profileProvider,
            destinationDependencies: destinationProbe.dependencies,
            localization: localization
        )

        let outerDeviceLocale = Locale(identifier: "en")
        XCTAssertEqual(outerDeviceLocale.language.languageCode?.identifier, "en")
        for language in ["en", "ru", "es"] {
            localization.currentLanguage = language
            XCTAssertEqual(
                home.appSelectedLocale.language.languageCode?.identifier,
                language
            )
        }
        let source = try source(at: "ios/PulsePlate/Views/HomeView.swift")
        XCTAssertTrue(source.contains(".environment(\\.locale, appSelectedLocale)"))
        assertNoProductionDestinationWork(
            apiClient: apiClient,
            destinationProbe: destinationProbe
        )
    }

    func testHomeProfileRefreshContractChangesPaidActionAndKeepsFactoriesLazy() async throws {
        let profileProvider = MutableHomeProfileProvider(profile: nil)
        let apiClient = HomeNoCallAPIClient()
        let destinationProbe = HomeDestinationFactoryProbe()
        let manager = await makeUnlockedManager()
        XCTAssertEqual(manager.flowState, .unlocked)

        let beforeReadiness = HomeExperience.profileReadiness(using: profileProvider)

        let beforeState = HomeExperience.resolve(
            flowState: manager.flowState,
            entitlement: manager.entitlement,
            profileReadiness: beforeReadiness
        )
        XCTAssertEqual(beforeState, .paidNeedsProfile)
        XCTAssertEqual(
            HomeExperience.actions(for: beforeState, planningToolsEnabled: false).primary,
            .completeProfile
        )

        _ = HomeView(
            apiClient: apiClient,
            profileProvider: profileProvider,
            destinationDependencies: destinationProbe.dependencies
        )
        XCTAssertEqual(beforeReadiness, .missingRequiredInputs)

        profileProvider.profile = completeProfile()
        let afterReadiness = HomeExperience.profileReadiness(using: profileProvider)

        XCTAssertEqual(afterReadiness, .readyForBackendValidation)
        let afterState = HomeExperience.resolve(
            flowState: manager.flowState,
            entitlement: manager.entitlement,
            profileReadiness: afterReadiness
        )
        XCTAssertEqual(afterState, .paidReady)
        XCTAssertEqual(
            HomeExperience.actions(for: afterState, planningToolsEnabled: false).primary,
            .todayPlate
        )
        XCTAssertGreaterThanOrEqual(profileProvider.readCount, 2)
        let source = try source(at: "ios/PulsePlate/Views/HomeView.swift")
        assertOrdered(
            [
                ".onAppear {",
                "refreshProfileReadiness()",
                "private func refreshProfileReadiness()",
                "profileReadiness = HomeExperience.profileReadiness(using: profileProvider)",
            ],
            in: source
        )
        assertNoProductionDestinationWork(
            apiClient: apiClient,
            destinationProbe: destinationProbe
        )
    }

    func testHomeSourceKeepsAuthorityAndLazyConstructionBoundaries() throws {
        let homeSource = try source(at: "ios/PulsePlate/Views/HomeView.swift")
        let experienceSource = try source(
            at: "ios/PulsePlate/Views/Home/HomeExperience.swift"
        )

        XCTAssertTrue(homeSource.contains("@EnvironmentObject private var subscriptionManager"))
        XCTAssertTrue(homeSource.contains("@ObservedObject private var localization"))
        XCTAssertTrue(homeSource.contains(".onAppear"))
        XCTAssertTrue(homeSource.contains("refreshProfileReadiness()"))
        XCTAssertTrue(homeSource.contains("refreshEntitlement(trigger: .manualRetry)"))
        XCTAssertEqual(
            occurrenceCount(of: "refreshEntitlement(", in: homeSource),
            1
        )
        XCTAssertFalse(homeSource.contains(".task"))
        XCTAssertFalse(homeSource.contains("lastError"))
        XCTAssertFalse(homeSource.contains("StoreKit"))
        XCTAssertFalse(homeSource.contains("AppStoreScreenshotContext"))

        for forbidden in [
            "ProKeyProvider", "previewProKey", "StoreKit", "FeatureFlags", "lastError",
            "activationID", "productID", "expiresAt", "tier",
        ] {
            XCTAssertFalse(
                experienceSource.contains(forbidden),
                "Pure Home experience contains authority input: \(forbidden)"
            )
        }
        XCTAssertFalse(experienceSource.contains("default:"))
        XCTAssertTrue(
            experienceSource.contains(
                "private struct HomeLazyDestination<Destination: View>: View"
            )
        )
        XCTAssertTrue(experienceSource.contains("var body: some View {\n        build()\n    }"))
    }

    func testHomePresentationSourceHasStableAccessibilityAndSourceOrder() throws {
        let source = try source(at: "ios/PulsePlate/Views/Home/HomeExperience.swift")

        assertOrdered(
            [
                "state.titleLocalizationKey",
                "state.detailLocalizationKey",
                "primaryAction",
                "secondaryActions",
            ],
            in: source
        )
        XCTAssertTrue(source.contains(".accessibilityAddTraits(.isHeader)"))
        XCTAssertTrue(source.contains(".accessibilityElement(children: .ignore)"))
        XCTAssertTrue(source.contains(".accessibilityIdentifier(action.accessibilityIdentifier)"))
        XCTAssertTrue(source.contains("PPAccessibility.minimumTouchTarget"))
        XCTAssertTrue(source.contains(".contentShape("))
        XCTAssertTrue(source.contains(".ppElevatedCardStyle()"))
        XCTAssertTrue(source.contains(".ppCardStyle()"))
        assertOrdered(
            [
                "if prominence == .primary",
                ".ppElevatedCardStyle()",
                "} else {",
                ".ppCardStyle()",
            ],
            in: source
        )
        XCTAssertTrue(source.contains("dynamicTypeSize.isAccessibilitySize"))
        XCTAssertTrue(source.contains("horizontalSizeClass != .regular"))
        XCTAssertTrue(source.contains(".frame(maxWidth: 650)"))
    }

    func testLocalizationHasExactFiniteHomeNamespaceAndFrozenValues() throws {
        XCTAssertEqual(exactHomeLocalizationKeys.count, 29)

        for locale in ["en", "ru", "es"] {
            let values = try loadHomeLocalization(locale: locale)
            let expected = try XCTUnwrap(frozenLocalizationValues[locale])
            XCTAssertEqual(Set(values.keys), exactHomeLocalizationKeys, locale)
            XCTAssertEqual(values.count, 29, locale)
            XCTAssertEqual(values, expected, locale)
            XCTAssertTrue(values.values.allSatisfy { !$0.contains("/api/") }, locale)
            XCTAssertTrue(values.values.allSatisfy { !$0.localizedCaseInsensitiveContains("AI Insight") }, locale)
            XCTAssertTrue(values.values.allSatisfy { !$0.localizedCaseInsensitiveContains("reader") }, locale)
            XCTAssertTrue(values.values.allSatisfy { !$0.localizedCaseInsensitiveContains("generator") }, locale)
            for technicalPhrase in [
                "pro key", "pro tools", "clave pro", "herramientas pro",
                "pro ключ", "инструменты pro",
            ] {
                XCTAssertTrue(
                    values.values.allSatisfy {
                        !$0.localizedCaseInsensitiveContains(technicalPhrase)
                    },
                    "\(locale): \(technicalPhrase)"
                )
            }
        }
    }

    func testFileSystemMembershipAndCanonicalTargetRegistrationRemainAutomatic() throws {
        let project = try source(at: "ios/PulsePlate.xcodeproj/project.pbxproj")
        XCTAssertTrue(project.contains("path = PulsePlate; sourceTree = \"<group>\";"))
        XCTAssertTrue(project.contains("path = PulsePlateTests; sourceTree = \"<group>\";"))
        XCTAssertFalse(project.contains("HomeExperience.swift"))
        XCTAssertFalse(project.contains("HomeExperienceTests.swift"))

        let targets = try source(at: "scripts/ios_test_targets.sh")
        let outputCommands = targets.components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { $0.hasPrefix("printf ") }
        XCTAssertEqual(outputCommands, ["printf '%s' 'PulsePlateTests'"])
        XCTAssertFalse(targets.contains("PulsePlateTests/"))
        XCTAssertFalse(targets.contains("TESTS=("))
        XCTAssertFalse(targets.contains("IFS=','"))
    }

    private var frozenLocalizationValues: [String: [String: String]] {
        [
            "en": [
                "home.navigation.title": "Home",
                "home.accessibility.screen_label": "Home screen",
                "home.state.loading.title": "Preparing your next step",
                "home.state.loading.detail":
                    "Checking your access before showing planning options.",
                "home.state.free_ready.title": "Start with a clear baseline",
                "home.state.free_ready.detail":
                    "Check your BMI, then add profile details when you are ready.",
                "home.state.paid_needs_profile.title": "Complete your profile",
                "home.state.paid_needs_profile.detail":
                    "Add the required details before opening your planning options.",
                "home.state.paid_ready.title": "Start with today",
                "home.state.paid_ready.detail":
                    "Open today's plate or choose another planning step.",
                "home.state.unavailable.title": "We couldn't confirm your access",
                "home.state.unavailable.detail":
                    "Try again, or continue with BMI and your profile.",
                "home.action.bmi.title": "Check BMI",
                "home.action.bmi.detail": "Get a clear starting point.",
                "home.action.complete_profile.title": "Complete profile",
                "home.action.complete_profile.detail":
                    "Add the details needed for planning.",
                "home.action.profile.title": "Profile",
                "home.action.profile.detail": "Review your planning details.",
                "home.action.today.title": "Today's plate",
                "home.action.today.detail": "Open today's nutrition view.",
                "home.action.progress.title": "Progress",
                "home.action.progress.detail": "Open your progress view.",
                "home.action.coach.title": "FitChef Coach",
                "home.action.coach.detail": "Choose where to start.",
                "home.action.week.title": "Week",
                "home.action.week.detail": "Open weekly planning.",
                "home.action.shopping.title": "Shopping list",
                "home.action.shopping.detail":
                    "Build from an available weekly plan.",
                "home.action.retry.title": "Try again",
            ],
            "ru": [
                "home.navigation.title": "Главная",
                "home.accessibility.screen_label": "Экран главной",
                "home.state.loading.title": "Готовим следующий шаг",
                "home.state.loading.detail":
                    "Проверяем доступ, прежде чем показать варианты планирования.",
                "home.state.free_ready.title": "Начните с понятной отправной точки",
                "home.state.free_ready.detail":
                    "Проверьте ИМТ, а затем добавьте данные профиля, когда будете готовы.",
                "home.state.paid_needs_profile.title": "Завершите настройку профиля",
                "home.state.paid_needs_profile.detail":
                    "Добавьте обязательные данные, прежде чем открывать варианты планирования.",
                "home.state.paid_ready.title": "Начните с сегодняшнего дня",
                "home.state.paid_ready.detail":
                    "Откройте тарелку на сегодня или выберите другой шаг планирования.",
                "home.state.unavailable.title": "Не удалось подтвердить доступ",
                "home.state.unavailable.detail":
                    "Повторите попытку или продолжите с ИМТ и профилем.",
                "home.action.bmi.title": "Проверить ИМТ",
                "home.action.bmi.detail": "Получите понятную отправную точку.",
                "home.action.complete_profile.title": "Завершить настройку",
                "home.action.complete_profile.detail":
                    "Добавьте данные, нужные для планирования.",
                "home.action.profile.title": "Профиль",
                "home.action.profile.detail": "Проверьте данные для планирования.",
                "home.action.today.title": "Тарелка на сегодня",
                "home.action.today.detail": "Откройте экран питания на сегодня.",
                "home.action.progress.title": "Прогресс",
                "home.action.progress.detail": "Откройте экран прогресса.",
                "home.action.coach.title": "FitChef Coach",
                "home.action.coach.detail": "Выберите, с чего начать.",
                "home.action.week.title": "Неделя",
                "home.action.week.detail": "Откройте планирование на неделю.",
                "home.action.shopping.title": "Список покупок",
                "home.action.shopping.detail":
                    "Соберите список из доступного недельного плана.",
                "home.action.retry.title": "Повторить",
            ],
            "es": [
                "home.navigation.title": "Inicio",
                "home.accessibility.screen_label": "Pantalla de inicio",
                "home.state.loading.title": "Preparando tu próximo paso",
                "home.state.loading.detail":
                    "Comprobamos tu acceso antes de mostrar las opciones de planificación.",
                "home.state.free_ready.title": "Empieza con una base clara",
                "home.state.free_ready.detail":
                    "Calcula tu BMI y añade los datos de tu perfil cuando estés listo.",
                "home.state.paid_needs_profile.title": "Completa tu perfil",
                "home.state.paid_needs_profile.detail":
                    "Añade los datos necesarios antes de abrir las opciones de planificación.",
                "home.state.paid_ready.title": "Empieza por hoy",
                "home.state.paid_ready.detail":
                    "Abre el plato de hoy o elige otro paso de planificación.",
                "home.state.unavailable.title": "No pudimos confirmar tu acceso",
                "home.state.unavailable.detail":
                    "Inténtalo de nuevo o continúa con BMI y tu perfil.",
                "home.action.bmi.title": "Calcular BMI",
                "home.action.bmi.detail": "Obtén un punto de partida claro.",
                "home.action.complete_profile.title": "Completar perfil",
                "home.action.complete_profile.detail":
                    "Añade los datos necesarios para planificar.",
                "home.action.profile.title": "Perfil",
                "home.action.profile.detail": "Revisa tus datos de planificación.",
                "home.action.today.title": "Plato de hoy",
                "home.action.today.detail": "Abre la vista de nutrición de hoy.",
                "home.action.progress.title": "Progreso",
                "home.action.progress.detail": "Abre la vista de progreso.",
                "home.action.coach.title": "FitChef Coach",
                "home.action.coach.detail": "Elige por dónde empezar.",
                "home.action.week.title": "Semana",
                "home.action.week.detail": "Abre la planificación semanal.",
                "home.action.shopping.title": "Lista de compras",
                "home.action.shopping.detail":
                    "Crea una lista a partir de un plan semanal disponible.",
                "home.action.retry.title": "Intentar de nuevo",
            ],
        ]
    }

    private func makeScreen(
        state: HomeExperienceState,
        planningToolsEnabled: Bool,
        probe: HomeRenderProbe
    ) -> HomeExperienceScreen<Text> {
        HomeExperienceScreen(
            state: state,
            actions: HomeExperience.actions(
                for: state,
                planningToolsEnabled: planningToolsEnabled
            ),
            onRetry: { probe.retryCount += 1 },
            destination: { _ in
                probe.destinationBuildCount += 1
                return Text("Destination")
            }
        )
    }

    private func makeUnlockedManager() async -> SubscriptionManager {
        let manager = SubscriptionManager(
            storeKitManager: HomeStoreKitStub(),
            billingService: HomeSubscriptionBillingStub(),
            activationPointerStore: HomeActivationPointerStore(
                activationID: "home-test-activation"
            ),
            apiKeyProvider: { "home-test-api-key" }
        )
        await manager.refreshEntitlement(trigger: .launch)
        return manager
    }

    private func completeProfile() -> ProNutritionProfile {
        ProNutritionProfile(
            sex: .female,
            age: 35,
            heightCm: 168,
            weightKg: 65,
            activity: .moderate,
            goal: .maintain
        )
    }

    private func assertNoProductionDestinationWork(
        apiClient: HomeNoCallAPIClient,
        destinationProbe: HomeDestinationFactoryProbe,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(apiClient.callCount, 0, file: file, line: line)
        XCTAssertEqual(destinationProbe.aiServiceFactoryCount, 0, file: file, line: line)
        XCTAssertEqual(destinationProbe.consentFactoryCount, 0, file: file, line: line)
        XCTAssertEqual(destinationProbe.supportServiceFactoryCount, 0, file: file, line: line)
        XCTAssertEqual(destinationProbe.weeklyServiceFactoryCount, 0, file: file, line: line)
        XCTAssertEqual(destinationProbe.shoppingServiceFactoryCount, 0, file: file, line: line)
        XCTAssertEqual(destinationProbe.clientEventIDCount, 0, file: file, line: line)
    }

    private func entitlementSnapshot(status: String) -> EntitlementSnapshot {
        EntitlementSnapshot(
            activationID: "opaque-activation",
            tier: "opaque-tier",
            status: status,
            expiresAt: nil,
            productID: nil
        )
    }

    private func loadHomeLocalization(locale: String) throws -> [String: String] {
        let data = try Data(contentsOf: localizationURL(locale: locale))
        let propertyList = try PropertyListSerialization.propertyList(
            from: data,
            options: [],
            format: nil
        )
        let values = try XCTUnwrap(propertyList as? [String: String])
        return values.filter { $0.key.hasPrefix("home.") }
    }

    private func localizationURL(locale: String) throws -> URL {
        try repositoryRoot()
            .appendingPathComponent("ios/PulsePlate")
            .appendingPathComponent("\(locale).lproj")
            .appendingPathComponent("Localizable.strings")
    }

    private func source(at relativePath: String) throws -> String {
        try String(
            contentsOf: try repositoryRoot().appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    private func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        while candidate.path != "/" {
            if FileManager.default.fileExists(
                atPath: candidate.appendingPathComponent(".git").path
            ) {
                return candidate
            }
            candidate = candidate.deletingLastPathComponent()
        }
        throw HomeExperienceTestError.repositoryRootNotFound
    }

    private func assertOrdered(
        _ values: [String],
        in source: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        var lowerBound = source.startIndex
        for value in values {
            guard let range = source.range(of: value, range: lowerBound..<source.endIndex) else {
                XCTFail("Missing or out-of-order source value: \(value)", file: file, line: line)
                return
            }
            lowerBound = range.upperBound
        }
    }

    private func occurrenceCount(of value: String, in source: String) -> Int {
        source.components(separatedBy: value).count - 1
    }
}

private final class HomeRenderProbe: @unchecked Sendable {
    // Test-only probe. Confined to one serial XCTest executor.
    var destinationBuildCount = 0
    var retryCount = 0
}

private final class HomeDestinationFactoryProbe: @unchecked Sendable {
    // Test-only factory probe. Confined to one serial XCTest executor.
    private(set) var aiServiceFactoryCount = 0
    private(set) var consentFactoryCount = 0
    private(set) var supportServiceFactoryCount = 0
    private(set) var weeklyServiceFactoryCount = 0
    private(set) var shoppingServiceFactoryCount = 0
    private(set) var clientEventIDCount = 0

    var dependencies: HomeDestinationDependencies {
        HomeDestinationDependencies(
            makeAIService: { [weak self] _ in
                self?.aiServiceFactoryCount += 1
                return HomeNoCallAIService()
            },
            makeConsentProvider: { [weak self] in
                self?.consentFactoryCount += 1
                return HomeNoCallConsentProvider()
            },
            makeSupportService: { [weak self] _ in
                self?.supportServiceFactoryCount += 1
                return HomeNoCallSupportService()
            },
            makeWeeklyService: { [weak self] _ in
                self?.weeklyServiceFactoryCount += 1
                return HomeNoCallWeeklyService()
            },
            makeShoppingService: { [weak self] _ in
                self?.shoppingServiceFactoryCount += 1
                return HomeNoCallShoppingService()
            },
            makeClientEventID: { [weak self] in
                self?.clientEventIDCount += 1
                return UUID(uuidString: "00000000-0000-4000-8000-000000000001")!
            }
        )
    }
}

private final class HomeNoCallAPIClient: APIClientProtocol, @unchecked Sendable {
    // Test-only API spy. Confined to one serial XCTest executor.
    private(set) var callCount = 0

    func postRaw<Response: Decodable>(
        path: String,
        body: Data,
        headers: [String: String]
    ) async throws -> Response {
        callCount += 1
        throw HomeExperienceTestError.unexpectedCall
    }

    func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String]
    ) async throws -> Response {
        callCount += 1
        throw HomeExperienceTestError.unexpectedCall
    }

    func get<Response: Decodable>(
        path: String,
        headers: [String: String]
    ) async throws -> Response {
        callCount += 1
        throw HomeExperienceTestError.unexpectedCall
    }
}

private actor HomeNoCallAIService: CBTInsightServicing {
    func fetchInsight(query: String, apiKey: String) async throws -> CBTInsightResponseDTO {
        throw HomeExperienceTestError.unexpectedCall
    }
}

private struct HomeNoCallConsentProvider: AIWellnessConsentProviding {
    func hasAccepted() -> Bool {
        preconditionFailure("Home render must not read consent")
    }

    func markAccepted() {
        preconditionFailure("Home render must not mutate consent")
    }
}

private actor HomeNoCallSupportService: FitChefSupportServicing {
    func requestHandoff(
        for supportNeed: FitChefSupportNeed,
        apiKey: String
    ) async throws -> FitChefSupportHandoffDescriptor {
        throw HomeExperienceTestError.unexpectedCall
    }

    func recordOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        apiKey: String
    ) async throws -> FitChefSupportOutcomeReceipt {
        throw HomeExperienceTestError.unexpectedCall
    }
}

private actor HomeNoCallWeeklyService: WeeklyPlanServicing {
    func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO {
        throw HomeExperienceTestError.unexpectedCall
    }
}

private actor HomeNoCallShoppingService: ShoppingListServicing {
    func fetchShoppingList(request: ShoppingListRequest) async throws -> ShoppingListDTO {
        throw HomeExperienceTestError.unexpectedCall
    }
}

private final class HomeStoreKitStub: StoreKitManaging {
    func loadProducts() async throws -> [SubscriptionProduct] { [] }

    func purchase(productID: String) async throws -> StorePurchaseResult {
        throw HomeExperienceTestError.unexpectedCall
    }

    func sync() async throws {
        throw HomeExperienceTestError.unexpectedCall
    }

    func latestVerifiedEntitlementTransaction() async -> StoreEntitlementTransaction? { nil }

    func currentReceiptData() async throws -> String {
        throw HomeExperienceTestError.unexpectedCall
    }
}

private final class HomeSubscriptionBillingStub: SubscriptionBillingServicing {
    func verifyReceipt(
        receiptData: String,
        apiKey: String
    ) async throws -> AppleReceiptVerificationResponseDTO {
        throw HomeExperienceTestError.unexpectedCall
    }

    func activateSubscription(
        request: ActivateSubscriptionRequestDTO,
        apiKey: String
    ) async throws -> SubscriptionActivationResponseDTO {
        throw HomeExperienceTestError.unexpectedCall
    }

    func fetchActivationStatus(
        activationID: String,
        apiKey: String
    ) async throws -> SubscriptionActivationResponseDTO {
        SubscriptionActivationResponseDTO(
            activationID: activationID,
            tier: "pro",
            status: "active",
            productID: "home-test-product",
            expiresAt: nil,
            activatedAt: nil,
            subscriptionTier: "pro",
            source: "ios_app_store",
            paymentSource: "ios_app_store"
        )
    }
}

private final class HomeActivationPointerStore: ActivationPointerStoring, @unchecked Sendable {
    // Test-only in-memory store. Confined to one serial XCTest executor.
    private var activationID: String?

    init(activationID: String?) {
        self.activationID = activationID
    }

    func loadActivationID() -> String? { activationID }

    func saveActivationID(_ id: String) { activationID = id }

    func clearActivationID() { activationID = nil }
}

private final class MutableHomeProfileProvider: ProfileProviding, @unchecked Sendable {
    // Test-only mutable provider. Confined to one serial XCTest executor.
    var profile: ProNutritionProfile?
    private(set) var readCount = 0

    init(profile: ProNutritionProfile?) {
        self.profile = profile
    }

    func proNutritionProfile() -> ProNutritionProfile? {
        readCount += 1
        return profile
    }

    func languageCode() -> String {
        "en"
    }
}

private enum HomeExperienceTestError: Error {
    case repositoryRootNotFound
    case unexpectedCall
}
