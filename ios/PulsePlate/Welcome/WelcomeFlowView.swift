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
        VStack(alignment: .leading, spacing: 16) {
            Text(stepA11yText)
                .font(.footnote)
                .foregroundStyle(.secondary)

            Text(screenTitleKey)
                .font(.largeTitle)
                .fontWeight(.bold)
                .accessibilityAddTraits(.isHeader)

            Text(screenBodyKey)
                .font(.body)

            Spacer()

            HStack {
                if step.back() != nil {
                    Button(backKey) { step = step.back() ?? step }
                        .accessibilityLabel(Text(backKey))
                }

                Spacer()

                Button(primaryCtaKey) {
                    guard let next = step.next() else { return onCompleted() }
                    step = next
                }
                .buttonStyle(.borderedProminent)
                .accessibilityLabel(Text(primaryCtaKey))
            }
        }
        .padding()
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
        step.next() == nil ? "onboarding.welcome.cta.start" : "onboarding.welcome.cta.continue"
    }

    private var backKey: LocalizedStringKey {
        "onboarding.welcome.cta.back"
    }

    private var stepA11yText: String {
        let template = NSLocalizedString("onboarding.welcome.stepA11y", comment: "")
        return String(format: template, step.index + 1, totalSteps)
    }
}
