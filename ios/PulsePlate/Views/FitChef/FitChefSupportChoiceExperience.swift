import Foundation
import SwiftUI

struct FitChefSupportChoiceExperience: View {
    let choices: FitChefSupportHandoffChoices
    let onConfirm: (FitChefSupportHandoffDescriptor) -> Void
    let onDismiss: () -> Void

    @Environment(\.locale) private var locale
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var selectionState: FitChefSupportChoiceSelectionState
    @ScaledMetric(relativeTo: .title2) private var headingFontSize =
        PPDesignTokens.Typography.size2XL
    @ScaledMetric(relativeTo: .body) private var bodyFontSize =
        PPDesignTokens.Typography.sizeBase

    init(
        choices: FitChefSupportHandoffChoices,
        onConfirm: @escaping (FitChefSupportHandoffDescriptor) -> Void,
        onDismiss: @escaping () -> Void
    ) {
        self.choices = choices
        self.onConfirm = onConfirm
        self.onDismiss = onDismiss
        _selectionState = State(initialValue: FitChefSupportChoiceSelectionState())
    }

    // Smallest existing PPButton size: closest to the frozen 48/52pt target
    // while preserving the primitive's minimum touch target.
    private let actionButtonSize: PPButtonSize = .sm

    private var horizontalRailPadding: CGFloat {
        dynamicTypeSize.isAccessibilitySize
            ? PPDesignTokens.Spacing.medium
            : PPDesignTokens.Spacing.xLarge
    }

    private var cardHorizontalPadding: CGFloat {
        dynamicTypeSize.isAccessibilitySize
            ? PPDesignTokens.Spacing.large
            : PPDesignTokens.Spacing.xLarge
    }

    private var choiceRowHorizontalPadding: CGFloat {
        dynamicTypeSize.isAccessibilitySize
            ? PPDesignTokens.Spacing.small
            : PPDesignTokens.Spacing.medium
    }

    private var fitChefImageSize: CGFloat {
        horizontalSizeClass == .regular ? 72 : 64
    }

    private var usesStackedActions: Bool {
        dynamicTypeSize.isAccessibilitySize || horizontalSizeClass != .regular
    }

    private var scrollAnchor: UnitPoint {
        if dynamicTypeSize.isAccessibilitySize {
            return .top
        }
        return horizontalSizeClass == .regular ? .center : .bottom
    }

    var body: some View {
        ZStack(alignment: .top) {
            PPDesignTokens.Brand.navy
                .ignoresSafeArea()

            versionedSupportChoiceScrollView
        }
        .onChange(of: choices) { _, newChoices in
            selectionState.revalidate(against: newChoices)
        }
    }

    private var supportChoiceScrollView: some View {
        ScrollView {
            PPCard {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                    header

                    FitChefSupportChoiceRow(
                        title: localized("fitchef.support_choice.daily.title"),
                        detail: localized("fitchef.support_choice.daily.detail"),
                        isSelected: selectionState.selectedDescriptor
                            == choices.dailyDescriptor,
                        horizontalPadding: choiceRowHorizontalPadding
                    ) {
                        selectionState.select(choices.dailyDescriptor)
                    }

                    FitChefSupportChoiceRow(
                        title: localized("fitchef.support_choice.weekly.title"),
                        detail: localized("fitchef.support_choice.weekly.detail"),
                        isSelected: selectionState.selectedDescriptor
                            == choices.weeklyDescriptor,
                        horizontalPadding: choiceRowHorizontalPadding
                    ) {
                        selectionState.select(choices.weeklyDescriptor)
                    }

                    actions
                }
                .padding(.horizontal, cardHorizontalPadding)
                .padding(.vertical, PPDesignTokens.Spacing.xLarge)
            }
            .frame(maxWidth: 650)
            .frame(maxWidth: .infinity, alignment: .top)
            .padding(.horizontal, horizontalRailPadding)
            .padding(.vertical, PPDesignTokens.Spacing.large)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .defaultScrollAnchor(.top)
    }

    @ViewBuilder
    private var versionedSupportChoiceScrollView: some View {
        if #available(iOS 18.0, *) {
            supportChoiceScrollView
                .defaultScrollAnchor(scrollAnchor, for: .alignment)
        } else {
            supportChoiceScrollView
        }
    }

    @ViewBuilder
    private var header: some View {
        if dynamicTypeSize.isAccessibilitySize {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                headerCopy

                fitChefImage
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
        } else {
            HStack(alignment: .top, spacing: PPDesignTokens.Spacing.large) {
                headerCopy
                fitChefImage
            }
        }
    }

    private var headerCopy: some View {
        VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
            Text(localized("fitchef.support_choice.question"))
                .font(.system(size: headingFontSize, weight: .bold))
                .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)

            Text(localized("fitchef.support_choice.agency"))
                .font(.system(size: bodyFontSize, weight: .regular))
                .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var fitChefImage: some View {
        Image("FitChef")
            .resizable()
            .scaledToFit()
            .frame(width: fitChefImageSize, height: fitChefImageSize)
            .accessibilityHidden(true)
    }

    private var actions: some View {
        Group {
            if usesStackedActions {
                VStack(spacing: PPDesignTokens.Spacing.small) {
                    confirmButton(fullWidth: true)
                    dismissButton(fullWidth: true)
                }
            } else {
                HStack(spacing: PPDesignTokens.Spacing.small) {
                    confirmButton(fullWidth: true)
                    dismissButton(fullWidth: false)
                }
            }
        }
    }

    private func confirmButton(fullWidth: Bool) -> some View {
        PPButton(
            localized("fitchef.support_choice.confirm"),
            variant: selectionState.canConfirm ? .primary : .secondary,
            size: actionButtonSize,
            fullWidth: fullWidth
        ) {
            confirmSelection()
        }
        .disabled(!selectionState.canConfirm)
        .opacity(selectionState.canConfirm ? 1 : 0.45)
    }

    private func dismissButton(fullWidth: Bool) -> some View {
        PPButton(
            localized("fitchef.support_choice.dismiss"),
            variant: .secondary,
            size: actionButtonSize,
            fullWidth: fullWidth
        ) {
            onDismiss()
        }
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

    private func confirmSelection() {
        guard let descriptor = selectionState.confirmationDescriptor else {
            return
        }
        onConfirm(descriptor)
    }

    #if DEBUG
    fileprivate init(
        choices: FitChefSupportHandoffChoices,
        selectedNeed: FitChefSupportNeed?,
        onConfirm: @escaping (FitChefSupportHandoffDescriptor) -> Void,
        onDismiss: @escaping () -> Void
    ) {
        self.choices = choices
        self.onConfirm = onConfirm
        self.onDismiss = onDismiss

        var initialState = FitChefSupportChoiceSelectionState()
        switch selectedNeed {
        case .dailyStructure:
            initialState.select(choices.dailyDescriptor)
        case .weeklyStructure:
            initialState.select(choices.weeklyDescriptor)
        case nil:
            break
        }
        _selectionState = State(initialValue: initialState)
    }
    #endif
}

private struct FitChefSupportChoiceRow: View {
    let title: String
    let detail: String
    let isSelected: Bool
    let horizontalPadding: CGFloat
    let action: () -> Void

    @ScaledMetric(relativeTo: .headline) private var choiceTitleFontSize =
        PPDesignTokens.Typography.sizeBase
    @ScaledMetric(relativeTo: .body) private var choiceDetailFontSize =
        PPDesignTokens.Typography.sizeBase
    @ScaledMetric(relativeTo: .title3) private var radioSymbolFontSize =
        PPDesignTokens.Typography.sizeLG

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: PPDesignTokens.Spacing.medium) {
                Image(systemName: isSelected ? "largecircle.fill.circle" : "circle")
                    .font(.system(size: radioSymbolFontSize, weight: .semibold))
                    .foregroundStyle(
                        isSelected
                            ? PPDesignTokens.ColorToken.primary
                            : PPDesignTokens.ColorToken.textSecondary
                    )
                    .frame(
                        minWidth: PPAccessibility.minimumTouchTarget,
                        minHeight: PPAccessibility.minimumTouchTarget,
                        alignment: .top
                    )
                    .accessibilityHidden(true)

                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xSmall) {
                    Text(title)
                        .font(.system(size: choiceTitleFontSize, weight: .semibold))
                        .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)

                    Text(detail)
                        .font(.system(size: choiceDetailFontSize, weight: .regular))
                        .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(.vertical, PPDesignTokens.Spacing.small)
            .padding(.horizontal, horizontalPadding)
            .frame(
                maxWidth: .infinity,
                minHeight: PPAccessibility.minimumTouchTarget,
                alignment: .leading
            )
            .background(
                isSelected
                    ? PPDesignTokens.ColorToken.surfaceHighlight
                    : PPDesignTokens.ColorToken.surface
            )
            .clipShape(
                RoundedRectangle(
                    cornerRadius: PPDesignTokens.Radius.large,
                    style: .continuous
                )
            )
            .overlay {
                RoundedRectangle(
                    cornerRadius: PPDesignTokens.Radius.large,
                    style: .continuous
                )
                .stroke(
                    isSelected
                        ? PPDesignTokens.ColorToken.primary
                        : PPDesignTokens.ColorToken.strokeSubtle,
                    lineWidth: isSelected
                        ? PPDesignTokens.Spacing.xSmall
                        : PPDesignTokens.Spacing.xxSmall
                )
            }
            .contentShape(
                RoundedRectangle(
                    cornerRadius: PPDesignTokens.Radius.large,
                    style: .continuous
                )
            )
        }
        .buttonStyle(.plain)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text("\(title). \(detail)"))
        .accessibilityAddTraits(isSelected ? .isSelected : [])
    }
}

#if DEBUG
private enum FitChefSupportChoicePreviewFixtures {
    static let choices = makeChoices()

    private static func makeChoices() -> FitChefSupportHandoffChoices {
        let daily = descriptor(
            supportNeed: "daily_structure",
            targetSurface: "pro_daily_plate"
        )
        let weekly = descriptor(
            supportNeed: "weekly_structure",
            targetSurface: "pro_weekly_plan"
        )

        do {
            return try FitChefSupportHandoffChoices(
                dailyDescriptor: daily,
                weeklyDescriptor: weekly
            )
        } catch {
            preconditionFailure("Invalid FitChef support-choice preview catalog: \(error)")
        }
    }

    private static func descriptor(
        supportNeed: String,
        targetSurface: String
    ) -> FitChefSupportHandoffDescriptor {
        let json = Data(
            """
            {
              "schema_version": "fitchef_support_handoff.v1",
              "scenario": "support_handoff",
              "support_need": "\(supportNeed)",
              "action": {
                "action_type": "handoff_to_product_surface",
                "target_surface": "\(targetSurface)"
              },
              "user_confirmation_required": true,
              "execution_authority": false,
              "plan_mutation_authority": false,
              "used_llm": false,
              "wellness_boundary": "wellness_planning_only"
            }
            """.utf8
        )
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .useDefaultKeys

        do {
            return try decoder.decode(FitChefSupportHandoffDescriptor.self, from: json)
        } catch {
            preconditionFailure("Invalid FitChef support-choice preview fixture: \(error)")
        }
    }
}

#Preview(
    "390×844 · EN · Unselected",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportChoiceExperience(
        choices: FitChefSupportChoicePreviewFixtures.choices,
        selectedNeed: nil,
        onConfirm: { _ in },
        onDismiss: {}
    )
    .environment(\.locale, Locale(identifier: "en"))
    .environment(\.horizontalSizeClass, .compact)
    .dynamicTypeSize(.large)
    .preferredColorScheme(.dark)
}

#Preview(
    "390×844 · RU · Weekly selected",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportChoiceExperience(
        choices: FitChefSupportChoicePreviewFixtures.choices,
        selectedNeed: .weeklyStructure,
        onConfirm: { _ in },
        onDismiss: {}
    )
    .environment(\.locale, Locale(identifier: "ru"))
    .environment(\.horizontalSizeClass, .compact)
    .dynamicTypeSize(.large)
    .preferredColorScheme(.light)
}

#Preview(
    "390×844 · ES · Accessibility 5 · Daily selected",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportChoiceExperience(
        choices: FitChefSupportChoicePreviewFixtures.choices,
        selectedNeed: .dailyStructure,
        onConfirm: { _ in },
        onDismiss: {}
    )
    .environment(\.locale, Locale(identifier: "es"))
    .environment(\.horizontalSizeClass, .compact)
    .dynamicTypeSize(.accessibility5)
    .preferredColorScheme(.light)
}

#Preview(
    "834×1194 · EN · Weekly selected",
    traits: .fixedLayout(width: 834, height: 1194)
) {
    FitChefSupportChoiceExperience(
        choices: FitChefSupportChoicePreviewFixtures.choices,
        selectedNeed: .weeklyStructure,
        onConfirm: { _ in },
        onDismiss: {}
    )
    .environment(\.locale, Locale(identifier: "en"))
    .environment(\.horizontalSizeClass, .regular)
    .dynamicTypeSize(.large)
    .preferredColorScheme(.dark)
}
#endif
