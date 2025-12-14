import SwiftUI

struct EmptyPlanView: View {
    let onGenerate: () -> Void

    var body: some View {
        VStack(spacing: 12) {
            Text("📅").font(.system(size: 48))
            Text("No weekly plan yet").font(.headline)
            Text("Generate a plan from your targets to see it day-by-day here.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            Button(action: onGenerate) {
                Text("Generate plan")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 12)
            }
            .buttonStyle(.borderedProminent)
            .padding(.top, 6)
        }
        .padding(24)
    }
}
