import SwiftUI

struct WelcomeFlowView: View {
    let onCompleted: () -> Void

    @State private var stepIndex: Int = 0
    private let totalSteps: Int = 4

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            stepA11yText
                .font(.footnote)
                .foregroundStyle(.secondary)
                .accessibilityHidden(true)

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
                    if stepIndex < totalSteps - 1 {
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
        switch stepIndex {
        case 0: return "onboarding.welcome.screen1.title"
        case 1: return "onboarding.welcome.screen2.title"
        case 2: return "onboarding.welcome.screen3.title"
        default: return "onboarding.welcome.screen4.title"
        }
    }

    private var screenBodyKey: LocalizedStringKey {
        switch stepIndex {
        case 0: return "onboarding.welcome.screen1.body"
        case 1: return "onboarding.welcome.screen2.body"
        case 2: return "onboarding.welcome.screen3.body"
        default: return "onboarding.welcome.screen4.body"
        }
    }

    private var primaryCtaKey: LocalizedStringKey {
        stepIndex < totalSteps - 1 ? "onboarding.welcome.cta.continue" : "onboarding.welcome.cta.start"
    }

    private var backKey: LocalizedStringKey {
        "onboarding.welcome.cta.back"
    }

    private var stepA11yText: Text {
        let template = NSLocalizedString("onboarding.welcome.stepA11y", comment: "")
        return Text(String(format: template, stepIndex + 1, totalSteps))
    }
}
