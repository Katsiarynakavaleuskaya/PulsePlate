import XCTest
@testable import PulsePlate

final class StoreKitManagerCatalogTests: XCTestCase {
    func test_loadsOnlyCanonicalStoreKitProducts() {
        let fetchedProducts = [
            StubStoreKitDisplayProduct(
                id: "com.pulseplate.premium.yearly",
                displayName: "Yearly",
                displayPrice: "$59.99"
            ),
            StubStoreKitDisplayProduct(
                id: "com.pulseplate.premium.legacy",
                displayName: "Legacy",
                displayPrice: "$19.99"
            ),
            StubStoreKitDisplayProduct(
                id: "com.pulseplate.premium.monthly",
                displayName: "Monthly",
                displayPrice: "$9.99"
            )
        ]

        let products = StoreKitManager.mapLoadedProducts(
            fetchedProducts,
            orderedBy: StoreKitProductCatalog.allowedProductIDs
        )

        XCTAssertEqual(products.map(\.id), StoreKitProductCatalog.allowedProductIDs)
    }

    func test_preservesCatalogOrderInLoadedProducts() {
        let fetchedProducts = [
            StubStoreKitDisplayProduct(
                id: "com.pulseplate.premium.yearly",
                displayName: "Yearly",
                displayPrice: "$59.99"
            ),
            StubStoreKitDisplayProduct(
                id: "com.pulseplate.premium.monthly",
                displayName: "Monthly",
                displayPrice: "$9.99"
            )
        ]

        let products = StoreKitManager.mapLoadedProducts(
            fetchedProducts,
            orderedBy: StoreKitProductCatalog.allowedProductIDs
        )

        XCTAssertEqual(
            products.map(\.displayName),
            ["Monthly", "Yearly"]
        )
    }

    func test_unknownProductIDIsIgnored() {
        let fetchedProducts = [
            StubStoreKitDisplayProduct(
                id: "com.pulseplate.premium.weekly",
                displayName: "Weekly",
                displayPrice: "$4.99"
            )
        ]

        let products = StoreKitManager.mapLoadedProducts(
            fetchedProducts,
            orderedBy: StoreKitProductCatalog.allowedProductIDs
        )

        XCTAssertTrue(products.isEmpty)
    }

    func test_entitlementFilterRejectsNonCatalogProducts() {
        XCTAssertTrue(StoreKitProductCatalog.contains("com.pulseplate.premium.monthly"))
        XCTAssertFalse(StoreKitProductCatalog.contains("com.pulseplate.premium.weekly"))
    }

    func test_emptyStoreKitResponseResultsInEmptyCatalog() {
        let products = StoreKitManager.mapLoadedProducts(
            [StubStoreKitDisplayProduct](),
            orderedBy: StoreKitProductCatalog.allowedProductIDs
        )

        XCTAssertTrue(products.isEmpty)
    }

    func test_partialStoreKitResponseRendersSubsetWithoutFallbackProducts() {
        let fetchedProducts = [
            StubStoreKitDisplayProduct(
                id: "com.pulseplate.premium.yearly",
                displayName: "Yearly",
                displayPrice: "$59.99"
            )
        ]

        let products = StoreKitManager.mapLoadedProducts(
            fetchedProducts,
            orderedBy: StoreKitProductCatalog.allowedProductIDs
        )

        XCTAssertEqual(products.map(\.id), ["com.pulseplate.premium.yearly"])
    }

    private struct StubStoreKitDisplayProduct: StoreKitDisplayProduct {
        let id: String
        let displayName: String
        let displayPrice: String
    }
}
