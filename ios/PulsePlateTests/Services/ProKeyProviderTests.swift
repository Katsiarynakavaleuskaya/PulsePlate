import XCTest

@testable import PulsePlate

final class ProKeyProviderTests: XCTestCase {
    func test_value_returnsNil_whenNoEnvKeyAndNoKeychainKey() throws {
        // We cannot reliably control ProcessInfo environment in tests,
        // but in CI/local runs it should not contain PRO_API_KEY by default.
        try ProKeyProvider.clear()
        XCTAssertNil(ProKeyProvider.value())
    }

    func test_value_returnsKeychainValue_whenSet() throws {
        try ProKeyProvider.clear()
        try ProKeyProvider.set(value: "pro_key_abc_123")
        XCTAssertEqual(ProKeyProvider.value(), "pro_key_abc_123")
        try ProKeyProvider.clear()
    }
}
