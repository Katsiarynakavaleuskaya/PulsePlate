import Foundation

enum StoreKitEntitlementTier: String, Equatable, Sendable {
    case pro
    case vip
}

enum StoreKitBillingInterval: String, Equatable, Sendable {
    case monthly
    case yearly
}

enum StoreKitProductFamily: String, Equatable, Sendable {
    case premiumSubscription = "premium_subscription"
}

enum StoreKitCatalogStatus: String, Equatable, Sendable {
    case active
}

struct StoreKitCatalogProduct: Equatable, Sendable {
    let productID: String
    let tier: StoreKitEntitlementTier
    let billingInterval: StoreKitBillingInterval
    let productFamily: StoreKitProductFamily
    let status: StoreKitCatalogStatus
}

enum StoreKitProductCatalog {
    static let all: [StoreKitCatalogProduct] = [
        StoreKitCatalogProduct(
            productID: "com.pulseplate.premium.monthly",
            tier: .pro,
            billingInterval: .monthly,
            productFamily: .premiumSubscription,
            status: .active
        ),
        StoreKitCatalogProduct(
            productID: "com.pulseplate.premium.yearly",
            tier: .pro,
            billingInterval: .yearly,
            productFamily: .premiumSubscription,
            status: .active
        )
    ]

    static var allowedProductIDs: [String] {
        all.map(\.productID)
    }

    static func contains(_ productID: String) -> Bool {
        product(for: productID) != nil
    }

    static func product(for productID: String) -> StoreKitCatalogProduct? {
        all.first { $0.productID == productID }
    }
}
