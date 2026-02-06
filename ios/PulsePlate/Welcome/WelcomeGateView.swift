import SwiftUI

struct WelcomeGateView: View {
    @AppStorage("has_seen_welcome_v1") private var hasSeenWelcome: Bool = false

    var body: some View {
        if hasSeenWelcome {
            RootTabs()
        } else {
            WelcomeFlowView(onCompleted: { hasSeenWelcome = true })
        }
    }
}
