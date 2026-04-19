import SwiftUI

struct SoftPaywallHookView: View {
    let hook: SoftPaywallHookDTO
    let nextBestAction: NextBestActionDTO?
    let onCtaTap: () -> Void

    var body: some View {
        // Thin-client rule:
        // - render only if hook exists
        // - NO BMI-dependent logic, NO language overrides, use default_* fields
        // - nextBestAction is advisory route context only
        VStack(alignment: .leading, spacing: 8) {
            Text(hook.message.defaultTitle ?? "").font(.headline)
            Text(hook.message.defaultBody ?? "").font(.subheadline)
            if let cta = hook.message.defaultCta, !cta.isEmpty {
                Button(cta, action: onCtaTap)
                    .buttonStyle(.borderedProminent)
            }
        }
        .padding()
        .background(.thinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
