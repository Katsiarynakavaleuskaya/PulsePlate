import XCTest

@testable import PulsePlate

final class ProKeyProviderTests: XCTestCase {
    func test_value_returnsNil_whenNoEnvKeyAndNoKeychainKey() throws {
        if ProcessInfo.processInfo.environment["PRO_API_KEY"] != nil {
            throw XCTSkip("PRO_API_KEY is set; skipping no-env-key assertion.")
        }
        try ProKeyProvider.clear()
        XCTAssertNil(ProKeyProvider.value())
    }

    func test_value_returnsKeychainValue_whenSet() throws {
        if ProcessInfo.processInfo.environment["PRO_API_KEY"] != nil {
            throw XCTSkip("PRO_API_KEY is set; skipping keychain value assertion.")
        }
        try ProKeyProvider.clear()
        try ProKeyProvider.set(value: "pro_key_abc_123")
        XCTAssertEqual(ProKeyProvider.value(), "pro_key_abc_123")
        try ProKeyProvider.clear()
    }
}
