import Foundation
import SwiftUI

struct FitChefSupportFlowScreen: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(\.locale) private var locale
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @State private var viewModel: FitChefSupportFlowViewModel
    @ScaledMetric(relativeTo: .headline) private var titleFontSize =
        PPDesignTokens.Typography.sizeLG
    @ScaledMetric(relativeTo: .caption) private var captionFontSize =
        PPDesignTokens.Typography.sizeXS
    @ScaledMetric(relativeTo: .body) private var bodyFontSize =
        PPDesignTokens.Typography.sizeBase

    init(viewModel: FitChefSupportFlowViewModel) {
        _viewModel = State(initialValue: viewModel)
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

            content
        }
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear {
            viewModel.cancel()
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.state {
        case .selecting:
            FitChefSupportChoiceExperience(
                onConfirm: { need in
                    viewModel.select(need)
                    viewModel.confirm()
                },
                onDismiss: close
            )
        case .requesting:
            versionedStatusScrollView
        case .handoffFailed:
            versionedStatusScrollView
        case .presenting, .recording, .outcomeFailed, .completed:
            versionedResultScrollView
        }
    }

    private var statusScrollView: some View {
        ScrollView {
            PPCard {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                    if case .requesting = viewModel.state {
                        ProgressView()
                            .tint(PPDesignTokens.ColorToken.primary)
                    }

                    if let messageKey = viewModel.userFacingMessageKey {
                        Text(localized(messageKey))
                            .font(.system(size: bodyFontSize, weight: .regular))
                            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    if case .handoffFailed = viewModel.state {
                        if viewModel.canRetryHandoff {
                            PPButton(
                                localized("fitchef.support_flow.action.retry"),
                                fullWidth: true
                            ) {
                                viewModel.retryHandoff()
                            }
                            .frame(minHeight: PPAccessibility.minimumTouchTarget)
                        }

                        PPButton(
                            localized("fitchef.support_flow.action.close"),
                            variant: .secondary,
                            fullWidth: true,
                            action: close
                        )
                        .frame(minHeight: PPAccessibility.minimumTouchTarget)
                    }
                }
                .padding(PPDesignTokens.Spacing.xLarge)
            }
            .frame(maxWidth: 650)
            .frame(maxWidth: .infinity, alignment: .top)
            .padding(.horizontal, PPDesignTokens.Spacing.large)
            .padding(.vertical, PPDesignTokens.Spacing.large)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .defaultScrollAnchor(.top)
    }

    @ViewBuilder
    private var versionedStatusScrollView: some View {
        if #available(iOS 18.0, *) {
            statusScrollView
                .defaultScrollAnchor(scrollAnchor, for: .alignment)
        } else {
            statusScrollView
        }
    }

    private var resultScrollView: some View {
        ScrollView {
            PPCard {
                VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                    Text(localized("fitchef.support_flow.result.title"))
                        .font(.system(size: titleFontSize, weight: .semibold))
                        .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityAddTraits(.isHeader)

                    VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.xSmall) {
                        Text(localized("fitchef.support_flow.result.target_label"))
                            .font(.system(size: captionFontSize, weight: .regular))
                            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)

                        Text(localized(viewModel.targetDisplayKey))
                            .font(.system(size: bodyFontSize, weight: .semibold))
                            .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .accessibilityElement(children: .combine)

                    Text(localized("fitchef.support_flow.result.boundary"))
                        .font(.system(size: bodyFontSize, weight: .regular))
                        .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)

                    if case .presenting = viewModel.state {
                        Text(localized("fitchef.support_flow.result.response_notice"))
                            .font(.system(size: bodyFontSize, weight: .regular))
                            .foregroundStyle(PPDesignTokens.ColorToken.textSecondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    resultActions
                }
                .padding(PPDesignTokens.Spacing.xLarge)
            }
            .frame(maxWidth: 650)
            .frame(maxWidth: .infinity, alignment: .top)
            .padding(.horizontal, PPDesignTokens.Spacing.large)
            .padding(.vertical, PPDesignTokens.Spacing.large)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        .defaultScrollAnchor(.top)
    }

    @ViewBuilder
    private var versionedResultScrollView: some View {
        if #available(iOS 18.0, *) {
            resultScrollView
                .defaultScrollAnchor(scrollAnchor, for: .alignment)
        } else {
            resultScrollView
        }
    }

    @ViewBuilder
    private var resultActions: some View {
        switch viewModel.state {
        case .presenting:
            VStack(spacing: PPDesignTokens.Spacing.small) {
                PPButton(
                    localized("fitchef.support_flow.action.acknowledge"),
                    fullWidth: true
                ) {
                    viewModel.acknowledge()
                }
                .frame(minHeight: PPAccessibility.minimumTouchTarget)

                PPButton(
                    localized("fitchef.support_flow.action.dismiss"),
                    variant: .secondary,
                    fullWidth: true
                ) {
                    viewModel.dismissResult()
                }
                .frame(minHeight: PPAccessibility.minimumTouchTarget)
            }
        case .recording:
            ProgressView(localized(viewModel.userFacingMessageKey))
                .tint(PPDesignTokens.ColorToken.primary)
                .frame(minHeight: PPAccessibility.minimumTouchTarget)
        case .outcomeFailed:
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
                Text(localized(viewModel.userFacingMessageKey))
                    .font(.system(size: bodyFontSize, weight: .regular))
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                if viewModel.canRetryOutcome {
                    PPButton(
                        localized("fitchef.support_flow.action.retry"),
                        fullWidth: true
                    ) {
                        viewModel.retryOutcome()
                    }
                    .frame(minHeight: PPAccessibility.minimumTouchTarget)
                }

                PPButton(
                    localized("fitchef.support_flow.action.close"),
                    variant: .secondary,
                    fullWidth: true,
                    action: close
                )
                .frame(minHeight: PPAccessibility.minimumTouchTarget)
            }
        case .completed:
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
                Text(localized(viewModel.userFacingMessageKey))
                    .font(.system(size: bodyFontSize, weight: .regular))
                    .foregroundStyle(PPDesignTokens.ColorToken.textPrimary)
                    .fixedSize(horizontal: false, vertical: true)

                PPButton(
                    localized("fitchef.support_flow.action.done"),
                    fullWidth: true,
                    action: close
                )
                .frame(minHeight: PPAccessibility.minimumTouchTarget)
            }
        case .selecting, .requesting, .handoffFailed:
            EmptyView()
        }
    }

    private func close() {
        viewModel.cancel()
        dismiss()
    }

    private func localized(_ key: String?) -> String {
        guard let key else { return "" }
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

#if DEBUG
private struct FitChefSupportPreviewService: FitChefSupportServicing {
    let dailyDescriptor: FitChefSupportHandoffDescriptor
    let weeklyDescriptor: FitChefSupportHandoffDescriptor
    let receipt: FitChefSupportOutcomeReceipt

    func requestHandoff(
        for supportNeed: FitChefSupportNeed,
        apiKey: String
    ) async throws -> FitChefSupportHandoffDescriptor {
        switch supportNeed {
        case .dailyStructure:
            return dailyDescriptor
        case .weeklyStructure:
            return weeklyDescriptor
        }
    }

    func recordOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        apiKey: String
    ) async throws -> FitChefSupportOutcomeReceipt {
        receipt
    }
}

private enum FitChefSupportFlowPreviewFixtures {
    static let dailyDescriptor = makeDescriptor(
        Data(
            """
            {
              "schema_version": "fitchef_support_handoff.v1",
              "scenario": "support_handoff",
              "support_need": "daily_structure",
              "action": {
                "action_type": "handoff_to_product_surface",
                "target_surface": "pro_daily_plate"
              },
              "user_confirmation_required": true,
              "execution_authority": false,
              "plan_mutation_authority": false,
              "used_llm": false,
              "wellness_boundary": "wellness_planning_only"
            }
            """.utf8
        )
    )
    static let weeklyDescriptor = makeDescriptor(
        Data(
            """
            {
              "schema_version": "fitchef_support_handoff.v1",
              "scenario": "support_handoff",
              "support_need": "weekly_structure",
              "action": {
                "action_type": "handoff_to_product_surface",
                "target_surface": "pro_weekly_plan"
              },
              "user_confirmation_required": true,
              "execution_authority": false,
              "plan_mutation_authority": false,
              "used_llm": false,
              "wellness_boundary": "wellness_planning_only"
            }
            """.utf8
        )
    )
    static let attempt = FitChefSupportOutcomeAttempt(
        supportNeed: .dailyStructure,
        outcome: .acknowledged,
        clientEventID: "00000000-0000-4000-8000-000000000001"
    )

    static func viewModel(
        _ state: FitChefSupportFlowState
    ) -> FitChefSupportFlowViewModel {
        FitChefSupportFlowViewModel(
            previewState: state,
            service: FitChefSupportPreviewService(
                dailyDescriptor: dailyDescriptor,
                weeklyDescriptor: weeklyDescriptor,
                receipt: FitChefSupportOutcomeReceipt(state: .recorded)
            )
        )
    }

    private static func makeDescriptor(
        _ payload: Data
    ) -> FitChefSupportHandoffDescriptor {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .useDefaultKeys
        do {
            return try decoder.decode(FitChefSupportHandoffDescriptor.self, from: payload)
        } catch {
            preconditionFailure("Invalid FitChef support preview fixture")
        }
    }
}

#Preview(
    "Selection",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(.selecting(nil))
    )
    .environment(\.locale, Locale(identifier: "en"))
}

#Preview(
    "Requesting",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(.requesting(.dailyStructure))
    )
}

#Preview(
    "Result",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(
            .presenting(FitChefSupportFlowPreviewFixtures.dailyDescriptor)
        )
    )
}

#Preview(
    "Recording",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(
            .recording(
                FitChefSupportFlowPreviewFixtures.dailyDescriptor,
                FitChefSupportFlowPreviewFixtures.attempt
            )
        )
    )
}

#Preview(
    "Recorded",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(
            .completed(
                FitChefSupportFlowPreviewFixtures.dailyDescriptor,
                .acknowledged,
                .recorded
            )
        )
    )
}

#Preview(
    "Replayed",
    traits: .fixedLayout(width: 834, height: 1194)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(
            .completed(
                FitChefSupportFlowPreviewFixtures.dailyDescriptor,
                .dismissed,
                .replayed
            )
        )
    )
    .environment(\.horizontalSizeClass, .regular)
}

#Preview(
    "Retryable failure",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(
            .outcomeFailed(
                FitChefSupportFlowPreviewFixtures.dailyDescriptor,
                FitChefSupportFlowPreviewFixtures.attempt,
                .retryable
            )
        )
    )
    .environment(\.locale, Locale(identifier: "es"))
    .dynamicTypeSize(.accessibility5)
}

#Preview(
    "Restart required",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(
            .outcomeFailed(
                FitChefSupportFlowPreviewFixtures.dailyDescriptor,
                FitChefSupportFlowPreviewFixtures.attempt,
                .restartRequired
            )
        )
    )
}

#Preview(
    "Terminal failure",
    traits: .fixedLayout(width: 390, height: 844)
) {
    FitChefSupportFlowScreen(
        viewModel: FitChefSupportFlowPreviewFixtures.viewModel(
            .outcomeFailed(
                FitChefSupportFlowPreviewFixtures.dailyDescriptor,
                FitChefSupportFlowPreviewFixtures.attempt,
                .terminal
            )
        )
    )
}
#endif
