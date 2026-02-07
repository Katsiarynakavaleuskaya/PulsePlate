import SwiftUI

private enum WelcomeStep: Int, CaseIterable {
    case first = 0
    case second = 1
}

struct WelcomeFlowView: View {
    let onCompleted: () -> Void

    @State private var stepIndex: Int = 0
    private var totalSteps: Int { WelcomeStep.allCases.count }

    private var clampedStepIndex: Int {
        min(max(stepIndex, 0), max(0, totalSteps - 1))
    }

    private var currentStep: WelcomeStep {
        WelcomeStep(rawValue: clampedStepIndex) ?? .first
    }

    private var isLastStep: Bool {
        clampedStepIndex == totalSteps - 1
    }

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
                if stepIndex > 0 {
                    Button(backKey) { stepIndex -= 1 }
                        .accessibilityLabel(Text(backKey))
                }

                Spacer()

                Button(primaryCtaKey) {
                    if !isLastStep {
                        stepIndex += 1
                    } else {
                        onCompleted()
                    }
                }
                .buttonStyle(.borderedProminent)
                .accessibilityLabel(Text(primaryCtaKey))
            }
        }
        .padding()
    }

    // MARK: - Localization keys (match audit namespace onboarding.welcome.*)

    private var screenTitleKey: LocalizedStringKey {
        switch currentStep {
        case .first: return "onboarding.welcome.screen1.title"
        case .second: return "onboarding.welcome.screen2.title"
        }
    }

    private var screenBodyKey: LocalizedStringKey {
        switch currentStep {
        case .first: return "onboarding.welcome.screen1.body"
        case .second: return "onboarding.welcome.screen2.body"
        }
    }

    private var primaryCtaKey: LocalizedStringKey {
        isLastStep ? "onboarding.welcome.cta.start" : "onboarding.welcome.cta.continue"
    }

    private var backKey: LocalizedStringKey {
        "onboarding.welcome.cta.back"
    }

    private var stepA11yText: String {
        let template = NSLocalizedString("onboarding.welcome.stepA11y", comment: "")
        return String(format: template, clampedStepIndex + 1, totalSteps)
    }
}
