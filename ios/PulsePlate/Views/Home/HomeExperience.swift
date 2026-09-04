import Foundation
import SwiftUI

enum HomeExperienceState: CaseIterable, Equatable, Hashable {
    case loading
    case freeReady
    case paidNeedsProfile
    case paidReady
    case unavailable

    var titleLocalizationKey: String {
        switch self {
        case .loading:
            return "home.state.loading.title"
        case .freeReady:
            return "home.state.free_ready.title"
        case .paidNeedsProfile:
            return "home.state.paid_needs_profile.title"
        case .paidReady:
            return "home.state.paid_ready.title"
        case .unavailable:
            return "home.state.unavailable.title"
        }
    }

    var detailLocalizationKey: String {
        switch self {
        case .loading:
            return "home.state.loading.detail"
        case .freeReady:
            return "home.state.free_ready.detail"
        case .paidNeedsProfile:
            return "home.state.paid_needs_profile.detail"
        case .paidReady:
            return "home.state.paid_ready.detail"
        case .unavailable:
            return "home.state.unavailable.detail"
        }
    }
}

enum HomeProfileReadiness: Equatable {
    case missingRequiredInputs
    case readyForBackendValidation
}

enum HomeAction: Equatable, Hashable {
    case checkBMI
    case profile
    case completeProfile
    case todayPlate
    case progress
    case fitChefCoach
    case week
    case shoppingList
    case retry

    var titleLocalizationKey: String {
        switch self {
        case .checkBMI:
            return "home.action.bmi.title"
        case .profile:
            return "home.action.profile.title"
        case .completeProfile:
            return "home.action.complete_profile.title"
        case .todayPlate:
            return "home.action.today.title"
        case .progress:
            return "home.action.progress.title"
        case .fitChefCoach:
            return "home.action.coach.title"
        case .week:
            return "home.action.week.title"
        case .shoppingList:
            return "home.action.shopping.title"
        case .retry:
            return "home.action.retry.title"
        }
    }

    var detailLocalizationKey: String? {
        switch self {
        case .checkBMI:
            return "home.action.bmi.detail"
        case .profile:
            return "home.action.profile.detail"
        case .completeProfile:
            return "home.action.complete_profile.detail"
        case .todayPlate:
            return "home.action.today.detail"
        case .progress:
            return "home.action.progress.detail"
        case .fitChefCoach:
            return "home.action.coach.detail"
        case .week:
            return "home.action.week.detail"
        case .shoppingList:
            return "home.action.shopping.detail"
        case .retry:
            return nil
        }
    }

    var symbolName: String {
        switch self {
        case .checkBMI:
            return "gauge"
        case .profile, .completeProfile:
            return "person.crop.circle"
        case .todayPlate:
            return "fork.knife.circle"
        case .progress:
            return "chart.line.uptrend.xyaxis"
        case .fitChefCoach:
            return "sparkles"
        case .week:
            return "calendar"
        case .shoppingList:
            return "cart"
        case .retry:
            return "arrow.clockwise"
        }
    }

    var accessibilityIdentifier: String {
        switch self {
        case .checkBMI:
            return "home.action.check_bmi"
        case .profile:
            return "home.action.profile"
        case .completeProfile:
            return "home.action.complete_profile"
        case .todayPlate:
            return "home.action.today_plate"
        case .progress:
            return "home.action.progress"
        case .fitChefCoach:
            return "home.action.fitchef_coach"
        case .week:
            return "home.action.week"
        case .shoppingList:
            return "home.action.shopping_list"
        case .retry:
            return "home.action.retry"
        }
    }
}

struct HomeActionSet: Equatable {
    let primary: HomeAction?
    let secondary: [HomeAction]
}

enum HomeExperience {
    static func resolve(
        flowState: SubscriptionFlowState,
        entitlement: EntitlementSnapshot?,
        profileReadiness: HomeProfileReadiness
    ) -> HomeExperienceState {
        switch flowState {
        case .purchasing, .sendingReceipt, .refreshingEntitlement, .restoring,
             .pendingApproval:
            return .loading
        case .idle:
            return entitlement == nil ? .freeReady : .unavailable
        case .unlocked:
            guard let entitlement else {
                return .unavailable
            }
            let normalizedStatus = entitlement.status
                .trimmingCharacters(in: .whitespacesAndNewlines)
                .lowercased()
            guard normalizedStatus == "active" || normalizedStatus == "restored" else {
                return .unavailable
            }
            switch profileReadiness {
            case .missingRequiredInputs:
                return .paidNeedsProfile
            case .readyForBackendValidation:
                return .paidReady
            }
        case .failed:
            return .unavailable
        }
    }

    static func profileReadiness(
        using profileProvider: any ProfileProviding
    ) -> HomeProfileReadiness {
        profileProvider.proNutritionProfile() == nil
            ? .missingRequiredInputs
            : .readyForBackendValidation
    }

    static func actions(
        for state: HomeExperienceState,
        planningToolsEnabled: Bool
    ) -> HomeActionSet {
        switch state {
        case .loading:
            return HomeActionSet(primary: nil, secondary: [])
        case .freeReady:
            return HomeActionSet(
                primary: .checkBMI,
                secondary: [.profile, .progress]
            )
        case .paidNeedsProfile:
            return HomeActionSet(
                primary: .completeProfile,
                secondary: [.checkBMI, .progress]
            )
        case .paidReady:
            return HomeActionSet(
                primary: .todayPlate,
                secondary: planningToolsEnabled
                    ? [.fitChefCoach, .week, .shoppingList]
                    : [.fitChefCoach]
            )
        case .unavailable:
            return HomeActionSet(
                primary: .retry,
                secondary: [.checkBMI, .profile]
            )
        }
    }

    static func coachCapabilities(
        aiGuidanceEnabled: Bool
    ) -> [FitChefCoachCapability] {
        aiGuidanceEnabled
            ? [.aiGuidance, .planningDirection]
            : [.planningDirection]
    }
}

struct HomeExperienceScreen<Destination: View>: View {
    let state: HomeExperienceState
    let actions: HomeActionSet

    private let onRetry: () -> Void
    private let makeDestination: (HomeAction) -> Destination

    @Environment(\.locale) private var locale
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    @ScaledMetric(relativeTo: .title) private var headingFontSize =
        PPDesignTokens.Typography.size2XL
    @ScaledMetric(relativeTo: .body) private var bodyFontSize =
        PPDesignTokens.Typography.sizeBase
    @ScaledMetric(relativeTo: .headline) private var actionTitleFontSize =
        PPDesignTokens.Typography.sizeLG
    @ScaledMetric(relativeTo: .caption) private var actionDetailFontSize =
        PPDesignTokens.Typography.sizeSM
    @ScaledMetric(relativeTo: .title3) private var actionSymbolFontSize =
        PPDesignTokens.Typography.sizeXL

    init(
        state: HomeExperienceState,
        actions: HomeActionSet,
        onRetry: @escaping () -> Void,
        @ViewBuilder destination: @escaping (HomeAction) -> Destination
    ) {
        self.state = state
        self.actions = actions
        self.onRetry = onRetry
        makeDestination = destination
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xLarge) {
                PPCard {
                    heroCardContent
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(PPDesignTokens.Spacing.xLarge)
                }

                primaryAction
                secondaryActions
            }
            .frame(maxWidth: 650)
            .frame(maxWidth: .infinity, alignment: .top)
            .padding(.horizontal, outerHorizontalInset)
            .padding(.vertical, PPDesignTokens.Spacing.large)
        }
        .background(PPDesignTokens.Brand.navy.ignoresSafeArea())
        .navigationTitle(localized("home.navigation.title"))
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("home.screen")
    }

    private var outerHorizontalInset: CGFloat {
        dynamicTypeSize.isAccessibilitySize
            ? PPDesignTokens.Spacing.medium
            : PPDesignTokens.Spacing.xLarge
    }

    @ViewBuilder
    private var heroCardContent: some View {
        if let heroAssetName {
            if usesStackedHeroLayout {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                    heroCopy
                    HStack {
                        Spacer(minLength: 0)
                        heroImage(
                            heroAssetName,
                            width: HomeHeroLayout.accessibilityWidth,
                            height: HomeHeroLayout.accessibilityHeight
                        )
                        Spacer(minLength: 0)
                    }
                }
            } else {
                HStack(alignment: .center, spacing: PPDesignTokens.Spacing.xLarge) {
                    heroCopy
                    Spacer(minLength: PPDesignTokens.Spacing.medium)
                    heroImage(
                        heroAssetName,
                        width: usesRegularHeroLayout
                            ? HomeHeroLayout.regularSide
                            : HomeHeroLayout.compactWidth,
                        height: usesRegularHeroLayout
                            ? HomeHeroLayout.regularSide
                            : HomeHeroLayout.compactHeight
                    )
                }
            }
        } else {
            heroCopy
        }
    }

    private var heroCopy: some View {
        VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
            Text(localized(state.titleLocalizationKey))
                .font(.system(size: headingFontSize, weight: .bold))
                .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)

            Text(localized(state.detailLocalizationKey))
                .font(.system(size: bodyFontSize, weight: .regular))
                .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                .fixedSize(horizontal: false, vertical: true)

            if state == .loading {
                ProgressView()
                    .tint(PPDesignTokens.ColorToken.primary)
                    .frame(minHeight: PPAccessibility.minimumTouchTarget)
                    .accessibilityLabel(
                        Text(localized(state.detailLocalizationKey))
                    )
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var heroAssetName: String? {
        switch state {
        case .freeReady:
            return horizontalSizeClass == .regular
                ? "fitchef-portrait-happy-v1.png"
                : "fitchef-onboarding-welcome-v1.png"
        case .paidReady:
            return "fitchef-portrait-encouraging-v1.png"
        case .loading, .paidNeedsProfile, .unavailable:
            return nil
        }
    }

    private var usesRegularHeroLayout: Bool {
        horizontalSizeClass == .regular && !dynamicTypeSize.isAccessibilitySize
    }

    private var usesStackedHeroLayout: Bool {
        horizontalSizeClass != .regular || dynamicTypeSize.isAccessibilitySize
    }

    private func heroImage(
        _ assetName: String,
        width: CGFloat,
        height: CGFloat
    ) -> some View {
        Image(ppRequiredBundleAsset: assetName)
            .resizable()
            .scaledToFill()
            .scaleEffect(
                HomeHeroLayout.zoom,
                anchor: UnitPoint(x: HomeHeroLayout.focalX, y: HomeHeroLayout.focalY)
            )
            .frame(width: width, height: height)
            .clipped()
            .clipShape(
                RoundedRectangle(
                    cornerRadius: PPDesignTokens.Radius.large,
                    style: .continuous
                )
            )
            .accessibilityHidden(true)
    }

    @ViewBuilder
    private var primaryAction: some View {
        if let action = actions.primary {
            if action == .retry {
                PPButton(
                    localized(action.titleLocalizationKey),
                    fullWidth: true,
                    action: onRetry
                )
                .frame(minHeight: PPAccessibility.minimumTouchTarget)
                .accessibilityIdentifier(action.accessibilityIdentifier)
            } else {
                actionLink(action, prominence: .primary)
            }
        }
    }

    @ViewBuilder
    private var secondaryActions: some View {
        if actions.secondary.isEmpty == false {
            if dynamicTypeSize.isAccessibilitySize || horizontalSizeClass != .regular {
                VStack(spacing: PPDesignTokens.Spacing.medium) {
                    ForEach(actions.secondary, id: \.self) { action in
                        actionLink(action, prominence: .secondary)
                    }
                }
            } else {
                HStack(alignment: .top, spacing: PPDesignTokens.Spacing.medium) {
                    ForEach(actions.secondary, id: \.self) { action in
                        actionLink(action, prominence: .secondary)
                    }
                }
            }
        }
    }

    private func actionLink(
        _ action: HomeAction,
        prominence: HomeActionProminence
    ) -> some View {
        NavigationLink {
            HomeLazyDestination {
                makeDestination(action)
            }
        } label: {
            actionCard(action, prominence: prominence)
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(actionAccessibilityLabel(action)))
        .accessibilityIdentifier(action.accessibilityIdentifier)
    }

    @ViewBuilder
    private func actionCard(
        _ action: HomeAction,
        prominence: HomeActionProminence
    ) -> some View {
        if prominence == .primary {
            actionCardContent(action, prominence: prominence)
                .ppElevatedCardStyle()
                .contentShape(
                    RoundedRectangle(
                        cornerRadius: PPDesignTokens.Radius.large,
                        style: .continuous
                    )
                )
        } else {
            actionCardContent(action, prominence: prominence)
                .ppCardStyle()
                .contentShape(
                    RoundedRectangle(
                        cornerRadius: PPDesignTokens.Radius.large,
                        style: .continuous
                    )
                )
        }
    }

    private func actionCardContent(
        _ action: HomeAction,
        prominence: HomeActionProminence
    ) -> some View {
        HStack(alignment: .top, spacing: PPDesignTokens.Spacing.medium) {
            Image(systemName: action.symbolName)
                .font(.system(size: actionSymbolFontSize, weight: .semibold))
                .foregroundStyle(PPDesignTokens.ColorToken.primary)
                .frame(
                    minWidth: PPAccessibility.minimumTouchTarget,
                    minHeight: PPAccessibility.minimumTouchTarget,
                    alignment: .top
                )
                .accessibilityHidden(true)

            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xSmall) {
                Text(localized(action.titleLocalizationKey))
                    .font(.system(size: actionTitleFontSize, weight: .semibold))
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                if let detailLocalizationKey = action.detailLocalizationKey {
                    Text(localized(detailLocalizationKey))
                        .font(.system(size: actionDetailFontSize, weight: .regular))
                        .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(maxWidth: .infinity, alignment: .topLeading)

            Image(systemName: "chevron.right")
                .font(.caption.bold())
                .foregroundStyle(PPDesignTokens.ColorToken.textTertiary)
                .frame(minHeight: PPAccessibility.minimumTouchTarget, alignment: .top)
                .accessibilityHidden(true)
        }
        .padding(
            prominence == .primary
                ? PPDesignTokens.Spacing.xLarge
                : PPDesignTokens.Spacing.large
        )
        .frame(
            maxWidth: .infinity,
            minHeight: PPAccessibility.minimumTouchTarget,
            alignment: .leading
        )
    }

    private func actionAccessibilityLabel(_ action: HomeAction) -> String {
        let title = localized(action.titleLocalizationKey)
        guard let detailLocalizationKey = action.detailLocalizationKey else {
            return title
        }
        return "\(title). \(localized(detailLocalizationKey))"
    }

    private func localized(_ key: String) -> String {
        let requestedLanguageCode = locale.language.languageCode?.identifier ?? "en"
        guard
            let bundle = localizationBundle(for: requestedLanguageCode)
                ?? localizationBundle(for: "en")
        else {
            return key
        }
        return bundle.localizedString(forKey: key, value: key, table: nil)
    }

    private func localizationBundle(for languageCode: String) -> Bundle? {
        guard let path = Bundle.main.path(forResource: languageCode, ofType: "lproj") else {
            return nil
        }
        return Bundle(path: path)
    }
}

private enum HomeActionProminence {
    case primary
    case secondary
}

private enum HomeHeroLayout {
    static let compactWidth: CGFloat = 112
    static let compactHeight: CGFloat = 148
    static let accessibilityWidth: CGFloat = 148
    static let accessibilityHeight: CGFloat = 148
    static let regularSide: CGFloat = 220
    static let focalX: CGFloat = 0.5
    static let focalY: CGFloat = 0.44
    static let zoom: CGFloat = 1.02
}

extension Image {
    init(ppRequiredBundleAsset filename: String, bundle: Bundle = .main) {
        guard let image = UIImage(named: filename, in: bundle, compatibleWith: nil) else {
            preconditionFailure("Missing required PulsePlate bundle image: \(filename)")
        }
        self.init(uiImage: image)
    }
}

private struct HomeLazyDestination<Destination: View>: View {
    private let build: () -> Destination

    init(@ViewBuilder build: @escaping () -> Destination) {
        self.build = build
    }

    var body: some View {
        build()
    }
}

#if DEBUG
private struct HomeExperiencePreview: View {
    let state: HomeExperienceState
    let planningToolsEnabled: Bool

    var body: some View {
        NavigationStack {
            HomeExperienceScreen(
                state: state,
                actions: HomeExperience.actions(
                    for: state,
                    planningToolsEnabled: planningToolsEnabled
                ),
                onRetry: {},
                destination: { _ in Text("Preview destination") }
            )
        }
        .environment(\.locale, Locale(identifier: "en"))
    }
}

#Preview("Home — Loading", traits: .fixedLayout(width: 390, height: 844)) {
    HomeExperiencePreview(state: .loading, planningToolsEnabled: false)
}

#Preview("Home — FREE", traits: .fixedLayout(width: 390, height: 844)) {
    HomeExperiencePreview(state: .freeReady, planningToolsEnabled: false)
}

#Preview("Home — Complete profile", traits: .fixedLayout(width: 390, height: 844)) {
    HomeExperiencePreview(state: .paidNeedsProfile, planningToolsEnabled: false)
}

#Preview("Home — Paid ready", traits: .fixedLayout(width: 834, height: 1194)) {
    HomeExperiencePreview(state: .paidReady, planningToolsEnabled: true)
        .environment(\.horizontalSizeClass, .regular)
}

#Preview("Home — Unavailable", traits: .fixedLayout(width: 390, height: 844)) {
    HomeExperiencePreview(state: .unavailable, planningToolsEnabled: false)
        .dynamicTypeSize(.accessibility5)
}
#endif
