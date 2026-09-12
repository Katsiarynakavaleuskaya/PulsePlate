import XCTest
@testable import PulsePlate

@MainActor
final class PlateLoadIssueTests: XCTestCase {

    func test_missingProKeyUsesAppLanguageWithoutDeveloperInstructions() {
        let localization = LocalizationManager.shared
        let originalLanguage = localization.currentLanguage
        defer { localization.currentLanguage = originalLanguage }
        let issue = PlateLoadIssue.missingProKey
        let expected = [
            ("en", "PRO access required", "PRO is not available on this device."),
            ("ru", "Нужен доступ PRO", "PRO недоступен на этом устройстве."),
            ("es", "Se requiere acceso PRO", "PRO no está disponible en este dispositivo."),
        ]
        for (language, title, message) in expected {
            localization.currentLanguage = language
            XCTAssertEqual(issue.title, title)
            XCTAssertEqual(issue.message, message)
            XCTAssertEqual(issue.primaryAction, .openProSetup)
            for diagnostic in ["Debug Tools", "Keychain", "Xcode", "injected", "test provider"] {
                XCTAssertFalse(issue.message.contains(diagnostic))
            }
        }
    }

    func test_primaryAction_missingProfile_opensProfile() {
        XCTAssertEqual(PlateLoadIssue.missingProfile.primaryAction, .openProfile)
    }

    func test_primaryAction_missingProKey_opensProSetup() {
        XCTAssertEqual(PlateLoadIssue.missingProKey.primaryAction, .openProSetup)
    }

    func test_primaryAction_transport_retries() {
        XCTAssertEqual(PlateLoadIssue.transport(message: "offline").primaryAction, .retry)
    }

    func test_message_api_isSanitized() {
        let localization = LocalizationManager.shared
        let originalLanguage = localization.currentLanguage
        defer { localization.currentLanguage = originalLanguage }
        localization.currentLanguage = "es"
        let key = "plate_issue_message_api_generic"
        let expected = localization.localized(key)
        let rawSentinel = "internal stack trace blah"
        let issue = PlateLoadIssue.api(statusCode: 500, message: rawSentinel)

        XCTAssertNotEqual(expected, key)
        XCTAssertEqual(issue.message, expected)
        XCTAssertFalse(issue.message.contains(rawSentinel))
    }

    func test_message_transport_isSanitized() {
        let localization = LocalizationManager.shared
        let originalLanguage = localization.currentLanguage
        defer { localization.currentLanguage = originalLanguage }
        localization.currentLanguage = "ru"
        let key = "plate_issue_message_transport_generic"
        let expected = localization.localized(key)
        let rawSentinel = "App Transport Security blah"
        let issue = PlateLoadIssue.transport(message: rawSentinel)

        XCTAssertNotEqual(expected, key)
        XCTAssertEqual(issue.message, expected)
        XCTAssertFalse(issue.message.contains(rawSentinel))
    }
}
