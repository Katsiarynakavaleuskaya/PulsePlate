import SwiftUI

@main
struct PulsePlateApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var subscriptionManager = SubscriptionManager()

    init() {
        AppStoreScreenshotContext.bootstrapIfNeeded()
    }

    var body: some Scene {
        WindowGroup {
            rootView
                .environmentObject(subscriptionManager)
                .task {
                    guard AppStoreScreenshotContext.isEnabled == false else {
                        return
                    }
                    await subscriptionManager.bootstrap()
                }
                .onChange(of: scenePhase) { _, newPhase in
                    guard newPhase == .active else {
                        return
                    }
                    Task {
                        guard AppStoreScreenshotContext.isEnabled == false else {
                            return
                        }
                        await subscriptionManager.refreshEntitlement(trigger: .foreground)
                    }
                }
        }
    }

    @ViewBuilder
    private var rootView: some View {
        if let scenarioView = AppStoreScreenshotContext.scenarioView() {
            scenarioView
        } else {
            WelcomeGateView()
        }
    }
}
