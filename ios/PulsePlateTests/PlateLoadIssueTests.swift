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
        let issue = PlateLoadIssue.api(statusCode: 500, message: "internal stack trace blah")
        XCTAssertEqual(issue.message, "We ran into a server problem. Please try again.")
    }

    func test_message_transport_isSanitized() {
        let issue = PlateLoadIssue.transport(message: "App Transport Security blah")
        XCTAssertEqual(
            issue.message,
            "We couldn't reach the server. Check your internet connection and try again."
        )
    }
}
