import SwiftUI

private enum WelcomeStep: Equatable {
    case value
    case usage

    var index: Int {
        switch self {
        case .value: return 0
        case .usage: return 1
        }
    }

    func next() -> WelcomeStep? {
        switch self {
        case .value: return .usage
        case .usage: return nil
        }
    }

    func back() -> WelcomeStep? {
        switch self {
        case .value: return nil
        case .usage: return .value
        }
    }
}

struct WelcomeFlowView: View {
    let onCompleted: () -> Void

    @State private var step: WelcomeStep = .value
    private let totalSteps: Int = 2

    var body: some View {
        ZStack {
            PPDesignTokens.Brand.navy
                .ignoresSafeArea()

            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.large) {
                Text(stepA11yText)
                    .ppStyle(.caption, color: .secondary)
                    .accessibilityIdentifier("appstore.welcome.step")

                Text(screenTitleKey)
                    .ppStyle(.largeTitle, color: .primary)
                    .accessibilityAddTraits(.isHeader)
                    .accessibilityIdentifier("appstore.welcome.title")

                Text(screenBodyKey)
                    .ppStyle(.body, color: .primary)
                    .accessibilityIdentifier("appstore.welcome.body")

                Spacer()

                HStack {
                    if step.back() != nil {
                        PPButton(backTitle, variant: .ghost, size: .md) {
                            step = step.back() ?? step
                        }
                            .accessibilityLabel(Text(backKey))
                            .accessibilityIdentifier("appstore.welcome.back")
                    }

                    Spacer()

                    PPButton(primaryCtaTitle, variant: .primary, size: .lg) {
                        guard let next = step.next() else { return onCompleted() }
                        step = next
                    }
                    .accessibilityLabel(Text(primaryCtaKey))
                    .accessibilityIdentifier("appstore.welcome.primary_cta")
                }
            }
            .padding(PPDesignTokens.Spacing.large)
        }
    }

    // MARK: - Localization keys (match audit namespace onboarding.welcome.*)

    private var screenTitleKey: LocalizedStringKey {
        switch step {
        case .value: return "onboarding.welcome.screen1.title"
        case .usage: return "onboarding.welcome.screen2.title"
        }
    }

    private var screenBodyKey: LocalizedStringKey {
        switch step {
        case .value: return "onboarding.welcome.screen1.body"
        case .usage: return "onboarding.welcome.screen2.body"
        }
    }

    private var primaryCtaKey: LocalizedStringKey {
        LocalizedStringKey(primaryCtaLocalizationKey)
    }

    private var backKey: LocalizedStringKey {
        "onboarding.welcome.cta.back"
    }

    private var primaryCtaTitle: String {
        NSLocalizedString(primaryCtaLocalizationKey, comment: "")
    }

    private var backTitle: String {
        NSLocalizedString("onboarding.welcome.cta.back", comment: "")
    }

    private var primaryCtaLocalizationKey: String {
        step.next() == nil ? "onboarding.welcome.cta.start" : "onboarding.welcome.cta.continue"
    }

    private var stepA11yText: String {
        let template = NSLocalizedString("onboarding.welcome.stepA11y", comment: "")
        return String(format: template, step.index + 1, totalSteps)
    }
}
