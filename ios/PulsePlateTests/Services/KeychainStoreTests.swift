import Foundation
import XCTest

@testable import PulsePlate

final class KeychainStoreTests: XCTestCase {
    func test_set_get_delete_roundtrip() throws {
        let service = "com.pulseplate.tests.keychain.\(UUID().uuidString)"
        let store = KeychainStore(service: service)
        let account = "pro_api_key"

        try store.delete(account: account)
        XCTAssertNil(try store.getString(account: account))

        try store.setString("k_test_value_123", account: account)
        XCTAssertEqual(try store.getString(account: account), "k_test_value_123")

        try store.delete(account: account)
        XCTAssertNil(try store.getString(account: account))
    }
}
