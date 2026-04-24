import XCTest
@testable import PulsePlate

final class StoreKitProductCatalogTests: XCTestCase {
    func test_catalogContainsOnlyCanonicalProducts() {
        XCTAssertEqual(
            StoreKitProductCatalog.allowedProductIDs,
            [
                "com.pulseplate.premium.monthly",
                "com.pulseplate.premium.yearly"
            ]
        )
    }

    func test_catalogAllowedProductIDsAreDerivedFromAll() {
        XCTAssertEqual(
            StoreKitProductCatalog.allowedProductIDs,
            StoreKitProductCatalog.all.map(\.productID)
        )
    }

    func test_monthlyProductMapsToExpectedTierAndInterval() throws {
        let product = try XCTUnwrap(
            StoreKitProductCatalog.product(for: "com.pulseplate.premium.monthly")
        )

        XCTAssertEqual(product.tier, .pro)
        XCTAssertEqual(product.billingInterval, .monthly)
        XCTAssertEqual(product.productFamily, .premiumSubscription)
        XCTAssertEqual(product.status, .active)
    }

    func test_yearlyProductMapsToExpectedTierAndInterval() throws {
        let product = try XCTUnwrap(
            StoreKitProductCatalog.product(for: "com.pulseplate.premium.yearly")
        )

        XCTAssertEqual(product.tier, .pro)
        XCTAssertEqual(product.billingInterval, .yearly)
        XCTAssertEqual(product.productFamily, .premiumSubscription)
        XCTAssertEqual(product.status, .active)
    }

    func test_productIDIsNotUsedAsTierVocabulary() throws {
        let product = try XCTUnwrap(
            StoreKitProductCatalog.product(for: "com.pulseplate.premium.monthly")
        )

        XCTAssertEqual(product.tier, .pro)
        XCTAssertNotEqual(product.tier.rawValue, "premium")
        XCTAssertTrue(product.productID.contains("premium"))
    }
}
