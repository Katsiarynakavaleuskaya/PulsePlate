import XCTest
@testable import PulsePlate

final class PlateLoadIssueTests: XCTestCase {

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
        let key = "plate_issue_message_api_generic"
        let expected = NSLocalizedString(key, comment: "")
        let rawSentinel = "internal stack trace blah"
        let issue = PlateLoadIssue.api(statusCode: 500, message: rawSentinel)

        XCTAssertNotEqual(expected, key)
        XCTAssertEqual(issue.message, expected)
        XCTAssertFalse(issue.message.contains(rawSentinel))
    }

    func test_message_transport_isSanitized() {
        let key = "plate_issue_message_transport_generic"
        let expected = NSLocalizedString(key, comment: "")
        let rawSentinel = "App Transport Security blah"
        let issue = PlateLoadIssue.transport(message: rawSentinel)

        XCTAssertNotEqual(expected, key)
        XCTAssertEqual(issue.message, expected)
        XCTAssertFalse(issue.message.contains(rawSentinel))
    }
}
