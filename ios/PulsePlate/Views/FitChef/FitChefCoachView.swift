import Foundation
import SwiftUI

enum FitChefCoachCapability: Equatable {
    case aiGuidance
    case planningDirection
}

struct FitChefCoachAvailability: Equatable {
    let capabilities: [FitChefCoachCapability]

    init(capabilities: [FitChefCoachCapability]) {
        var normalizedCapabilities: [FitChefCoachCapability] = []
        for capability in capabilities where !normalizedCapabilities.contains(capability) {
            normalizedCapabilities.append(capability)
        }
        self.capabilities = normalizedCapabilities
    }
}

struct FitChefCoachView<AIGuidanceDestination: View, PlanningDirectionDestination: View>: View {
    let availability: FitChefCoachAvailability

    private let makeAIGuidanceDestination: () -> AIGuidanceDestination
    private let makePlanningDirectionDestination: () -> PlanningDirectionDestination

    @Environment(\.locale) private var locale
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    @ScaledMetric(relativeTo: .title2) private var headingFontSize =
        PPDesignTokens.Typography.size2XL
    @ScaledMetric(relativeTo: .body) private var bodyFontSize =
        PPDesignTokens.Typography.sizeBase
    @ScaledMetric(relativeTo: .headline) private var cardTitleFontSize =
        PPDesignTokens.Typography.sizeLG
    @ScaledMetric(relativeTo: .body) private var cardDetailFontSize =
        PPDesignTokens.Typography.sizeBase
    @ScaledMetric(relativeTo: .title3) private var cardSymbolFontSize =
        PPDesignTokens.Typography.sizeXL
    @ScaledMetric(relativeTo: .body) private var chevronFontSize =
        PPDesignTokens.Typography.sizeSM

    /// Destination builders are navigation factories. Callers must keep them
    /// side-effect-free; the Hub stores them without evaluating either closure.
    init(
        availability: FitChefCoachAvailability,
        @ViewBuilder aiGuidanceDestination: @escaping () -> AIGuidanceDestination,
        @ViewBuilder planningDirectionDestination: @escaping () -> PlanningDirectionDestination
    ) {
        self.availability = availability
        makeAIGuidanceDestination = aiGuidanceDestination
        makePlanningDirectionDestination = planningDirectionDestination
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xLarge) {
                intro

                VStack(spacing: PPDesignTokens.Spacing.medium) {
                    ForEach(availability.capabilities.indices, id: \.self) { index in
                        capabilityLink(for: availability.capabilities[index])
                    }
                }
            }
            .frame(maxWidth: 650)
            .frame(maxWidth: .infinity, alignment: .top)
            .padding(.horizontal, outerHorizontalInset)
            .padding(.vertical, PPDesignTokens.Spacing.large)
        }
        .background(PPDesignTokens.Brand.navy.ignoresSafeArea())
        .navigationTitle(localized("fitchef.coach_hub.navigation.title"))
        .navigationBarTitleDisplayMode(.inline)
        .accessibilityIdentifier("fitchef.coach_hub.screen")
    }

    private var outerHorizontalInset: CGFloat {
        dynamicTypeSize.isAccessibilitySize
            ? PPDesignTokens.Spacing.medium
            : PPDesignTokens.Spacing.xLarge
    }

    private var cardHorizontalInset: CGFloat {
        dynamicTypeSize.isAccessibilitySize
            ? PPDesignTokens.Spacing.medium
            : PPDesignTokens.Spacing.large
    }

    private var fitChefImageSize: CGFloat {
        horizontalSizeClass == .regular ? 72 : 64
    }

    @ViewBuilder
    private var intro: some View {
        if dynamicTypeSize.isAccessibilitySize {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                introCopy

                fitChefImage
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        } else {
            HStack(alignment: .top, spacing: PPDesignTokens.Spacing.large) {
                introCopy
                fitChefImage
            }
        }
    }

    private var introCopy: some View {
        VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
            Text(localized("fitchef.coach_hub.header.title"))
                .font(.system(size: headingFontSize, weight: .bold))
                .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)

            Text(localized("fitchef.coach_hub.header.description"))
                .font(.system(size: bodyFontSize, weight: .regular))
                .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
    }

    private var fitChefImage: some View {
        Image("FitChef")
            .resizable()
            .scaledToFit()
            .frame(width: fitChefImageSize, height: fitChefImageSize)
            .accessibilityHidden(true)
    }

    @ViewBuilder
    private func capabilityLink(for capability: FitChefCoachCapability) -> some View {
        switch capability {
        case .aiGuidance:
            NavigationLink {
                FitChefCoachLazyDestination(build: makeAIGuidanceDestination)
            } label: {
                capabilityCard(
                    title: localized("fitchef.coach_hub.ai_guidance.title"),
                    detail: localized("fitchef.coach_hub.ai_guidance.detail"),
                    symbol: "brain.head.profile"
                )
            }
            .buttonStyle(.plain)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(
                Text(
                    "\(localized("fitchef.coach_hub.ai_guidance.title")). "
                        + localized("fitchef.coach_hub.ai_guidance.detail")
                )
            )
            .accessibilityHint(
                Text(localized("fitchef.coach_hub.ai_guidance.accessibility_hint"))
            )
            .accessibilityIdentifier("fitchef.coach_hub.card.ai_guidance")

        case .planningDirection:
            NavigationLink {
                FitChefCoachLazyDestination(build: makePlanningDirectionDestination)
            } label: {
                capabilityCard(
                    title: localized("fitchef.coach_hub.planning_direction.title"),
                    detail: localized("fitchef.coach_hub.planning_direction.detail"),
                    symbol: "calendar.badge.clock"
                )
            }
            .buttonStyle(.plain)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(
                Text(
                    "\(localized("fitchef.coach_hub.planning_direction.title")). "
                        + localized("fitchef.coach_hub.planning_direction.detail")
                )
            )
            .accessibilityHint(
                Text(localized("fitchef.coach_hub.planning_direction.accessibility_hint"))
            )
            .accessibilityIdentifier("fitchef.coach_hub.card.planning_direction")
        }
    }

    private func capabilityCard(
        title: String,
        detail: String,
        symbol: String
    ) -> some View {
        PPCard {
            HStack(alignment: .top, spacing: PPDesignTokens.Spacing.medium) {
                Image(systemName: symbol)
                    .font(.system(size: cardSymbolFontSize, weight: .semibold))
                    .foregroundStyle(PPDesignTokens.ColorToken.primary)
                    .frame(
                        minWidth: PPAccessibility.minimumTouchTarget,
                        minHeight: PPAccessibility.minimumTouchTarget,
                        alignment: .top
                    )
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xSmall) {
                    Text(title)
                        .font(.system(size: cardTitleFontSize, weight: .semibold))
                        .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(detail)
                        .font(.system(size: cardDetailFontSize, weight: .regular))
                        .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .topLeading)

                Image(systemName: "chevron.right")
                    .font(.system(size: chevronFontSize, weight: .semibold))
                    .foregroundStyle(PPDesignTokens.ColorToken.textTertiary)
                    .frame(minHeight: PPAccessibility.minimumTouchTarget, alignment: .top)
                    .accessibilityHidden(true)
            }
            .padding(.horizontal, cardHorizontalInset)
            .padding(.vertical, PPDesignTokens.Spacing.large)
            .frame(
                maxWidth: .infinity,
                minHeight: PPAccessibility.minimumTouchTarget,
                alignment: .leading
            )
        }
        .contentShape(
            RoundedRectangle(
                cornerRadius: PPDesignTokens.Radius.large,
                style: .continuous
            )
        )
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
        guard
            let path = Bundle.main.path(forResource: languageCode, ofType: "lproj")
        else {
            return nil
        }
        return Bundle(path: path)
    }
}

private struct FitChefCoachLazyDestination<Destination: View>: View {
    private let build: () -> Destination

    init(@ViewBuilder build: @escaping () -> Destination) {
        self.build = build
    }

    var body: some View {
        build()
    }
}
