import XCTest

@testable import PulsePlate

final class ProKeyProviderTests: XCTestCase {
    override func tearDown() {
        unsetenv("PRO_API_KEY")
        try? ProKeyProvider.clear()
        super.tearDown()
    }

    func test_value_returnsNil_whenNoEnvKeyAndNoKeychainKey() throws {
        try ProKeyProvider.clear()
        XCTAssertNil(ProKeyProvider.value())
    }

    func test_value_ignoresDebugEnvKey_whenKeychainIsEmpty() throws {
        try ProKeyProvider.clear()
        setenv("PRO_API_KEY", "env_key_should_be_ignored", 1)

        XCTAssertNil(ProKeyProvider.value())
    }

    func test_value_returnsKeychainValue_whenSet() throws {
        try ProKeyProvider.clear()
        try ProKeyProvider.set(value: "pro_key_abc_123")
        XCTAssertEqual(ProKeyProvider.value(), "pro_key_abc_123")
    }

    func test_value_prefersKeychain_evenWhenEnvKeyExists() throws {
        try ProKeyProvider.clear()
        setenv("PRO_API_KEY", "env_key_should_be_ignored", 1)
        try ProKeyProvider.set(value: "pro_key_abc_123")

        XCTAssertEqual(ProKeyProvider.value(), "pro_key_abc_123")
    }
}
