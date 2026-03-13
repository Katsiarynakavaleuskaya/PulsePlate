import XCTest

final class AppStoreScreenshotTests: XCTestCase {
    private enum Scenario: String, CaseIterable {
        case welcome
        case home
        case plate
        case paywall
        case profile
        case healthPermission = "health_permission"

        var screenshotName: String {
            switch self {
            case .welcome:
                return "01_welcome"
            case .home:
                return "02_home"
            case .plate:
                return "03_plate"
            case .paywall:
                return "04_pro_vip_paywall"
            case .profile:
                return "05_privacy_profile"
            case .healthPermission:
                return "06_health_permission"
            }
        }

        var accessibilityIdentifier: String {
            switch self {
            case .welcome:
                return "appstore.welcome.screen"
            case .home:
                return "appstore.home.screen"
            case .plate:
                return "appstore.plate.screen"
            case .paywall:
                return "appstore.paywall.screen"
            case .profile:
                return "appstore.profile.screen"
            case .healthPermission:
                return "appstore.health_permission.screen"
            }
        }
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    @MainActor
    func testWelcomeScreenshot() {
        captureScreenshot(for: .welcome)
    }

    @MainActor
    func testHomeScreenshot() {
        captureScreenshot(for: .home)
    }

    @MainActor
    func testPlateScreenshot() {
        captureScreenshot(for: .plate)
    }

    @MainActor
    func testPaywallScreenshot() {
        captureScreenshot(for: .paywall)
    }

    @MainActor
    func testProfileScreenshot() {
        captureScreenshot(for: .profile)
    }

    @MainActor
    func testHealthPermissionScreenshot() {
        captureScreenshot(for: .healthPermission)
    }

    @MainActor
    private func captureScreenshot(for scenario: Scenario) {
        let app = XCUIApplication()
        setupSnapshot(app, waitForAnimations: false)
        app.launchArguments += [
            "-appstore-screenshot-mode",
            "-appstore-screenshot-scenario", scenario.rawValue,
            "-appstore-screenshot-language", preferredLanguageCode()
        ]
        app.launchEnvironment["APPSTORE_SCREENSHOT_MODE"] = "1"
        app.launchEnvironment["APPSTORE_SCREENSHOT_LANGUAGE"] = preferredLanguageCode()
        app.launch()

        let root = app.descendants(matching: .any)
            .matching(identifier: scenario.accessibilityIdentifier)
            .firstMatch
        XCTAssertTrue(
            root.waitForExistence(timeout: 20),
            "App Store screenshot root did not appear for \(scenario.rawValue)"
        )

        snapshot(scenario.screenshotName, timeWaitingForIdle: 0)
        app.terminate()
    }

    private func preferredLanguageCode() -> String {
        let raw = Locale.preferredLanguages.first ?? "en-US"
        if raw.hasPrefix("ru") {
            return "ru-RU"
        }
        if raw.hasPrefix("es") {
            return "es-ES"
        }
        return "en-US"
    }
}
