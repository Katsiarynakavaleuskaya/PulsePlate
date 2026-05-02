import XCTest
@testable import PulsePlate

/// Tests for ``AppConfig.validateReleaseBaseURL(_:)``.
///
/// The validation helper gates the Release `fatalError` path. By testing the
/// helper directly we cover the acceptance/rejection logic without crashing
/// the test runner.
final class AppConfigTests: XCTestCase {

    // MARK: - Accepted inputs

    func testValidHTTPSURL() {
        let url = AppConfig.validateReleaseBaseURL("https://pulseplate.app")
        XCTAssertNotNil(url)
        XCTAssertEqual(url?.absoluteString, "https://pulseplate.app")
    }

    func testValidHTTPSURLWithPath() {
        let url = AppConfig.validateReleaseBaseURL("https://pulseplate.app/api/v1")
        XCTAssertNotNil(url)
        XCTAssertEqual(url?.scheme, "https")
        XCTAssertEqual(url?.host, "pulseplate.app")
    }

    func testValidHTTPSURLWithPort() {
        let url = AppConfig.validateReleaseBaseURL("https://pulseplate.app:443")
        XCTAssertNotNil(url)
        XCTAssertEqual(url?.host, "pulseplate.app")
    }

    func testUppercaseHTTPSAccepted() {
        // RFC 3986: schemes are case-insensitive
        let url = AppConfig.validateReleaseBaseURL("HTTPS://pulseplate.app")
        XCTAssertNotNil(url)
    }

    // MARK: - Rejected inputs

    func testNilRejected() {
        XCTAssertNil(AppConfig.validateReleaseBaseURL(nil))
    }

    func testEmptyStringRejected() {
        XCTAssertNil(AppConfig.validateReleaseBaseURL(""))
    }

    func testHTTPRejected() {
        XCTAssertNil(AppConfig.validateReleaseBaseURL("http://pulseplate.app"))
    }

    func testNoHostRejected() {
        XCTAssertNil(AppConfig.validateReleaseBaseURL("https://"))
    }

    func testInvalidURLStringRejected() {
        XCTAssertNil(AppConfig.validateReleaseBaseURL("not a url at all"))
    }

    func testFTPSchemeRejected() {
        XCTAssertNil(AppConfig.validateReleaseBaseURL("ftp://files.example.com"))
    }

    func testWhitespaceOnlyRejected() {
        XCTAssertNil(AppConfig.validateReleaseBaseURL("   "))
    }

    func testSchemeOnlyRejected() {
        // "https:" parses as a valid URL with scheme but no host
        XCTAssertNil(AppConfig.validateReleaseBaseURL("https:"))
    }

    func testSchemelessURLRejected() {
        // No scheme → scheme is nil → rejected
        XCTAssertNil(AppConfig.validateReleaseBaseURL("pulseplate.app"))
    }
}
