import SwiftUI

struct SoftPaywallHookView: View {
    let hook: SoftPaywallHook
    let onCtaTap: () -> Void

    var body: some View {
        // Thin-client rule:
        // - render only if hook exists
        // - NO BMI-dependent logic, NO language overrides, use default_* fields
        VStack(alignment: .leading, spacing: 8) {
            Text(hook.message.defaultTitle).font(.headline)
            Text(hook.message.defaultBody).font(.subheadline)
            Button(hook.message.defaultCta, action: onCtaTap)
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
