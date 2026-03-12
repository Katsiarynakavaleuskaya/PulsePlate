import SwiftUI

@main
struct PulsePlateApp: App {
    init() {
        AppStoreScreenshotContext.bootstrapIfNeeded()
    }

    var body: some Scene {
        WindowGroup {
            if let scenarioView = AppStoreScreenshotContext.scenarioView() {
                scenarioView
            } else {
                WelcomeGateView()
            }
        }
    }
}
