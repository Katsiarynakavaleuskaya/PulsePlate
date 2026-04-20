import Foundation
import StoreKit

protocol StoreKitDisplayProduct {
    var id: String { get }
    var displayName: String { get }
    var displayPrice: String { get }
}

extension Product: StoreKitDisplayProduct {}

struct SubscriptionProduct: Identifiable, Equatable, Sendable {
    let id: String
    let displayName: String
    let displayPrice: String
}

struct StoreEntitlementTransaction: Equatable, Sendable {
    let transactionID: String
    let originalTransactionID: String?
    let productID: String
}

enum StorePurchaseResult: Equatable, Sendable {
    case success(StoreEntitlementTransaction)
    case pending
    case cancelled
}

enum StoreKitAdapterError: Error, Equatable, Sendable {
    case missingReceipt
    case productNotFound(String)
    case unverifiedTransaction
    case unsupportedPurchaseResult
    case receiptReadFailed(String)
}

extension StoreKitAdapterError: LocalizedError {
    var errorDescription: String? {
        switch self {
        case .missingReceipt:
            return "App Store receipt is unavailable."
        case .productNotFound(let productID):
            return "StoreKit product is unavailable: \(productID)"
        case .unverifiedTransaction:
            return "StoreKit transaction could not be verified."
        case .unsupportedPurchaseResult:
            return "StoreKit returned an unsupported purchase result."
        case .receiptReadFailed(let message):
            return "Failed to read App Store receipt: \(message)"
        }
    }
}

protocol StoreKitManaging {
    func loadProducts() async throws -> [SubscriptionProduct]
    func purchase(productID: String) async throws -> StorePurchaseResult
    func sync() async throws
    func latestVerifiedEntitlementTransaction() async -> StoreEntitlementTransaction?
    func currentReceiptData() async throws -> String
}

@MainActor
final class StoreKitManager: StoreKitManaging {
    private let catalog: [StoreKitCatalogProduct]
    private let productIDs: [String]
    private var cachedProducts: [String: Product] = [:]

    init(catalog: [StoreKitCatalogProduct] = StoreKitProductCatalog.all) {
        self.catalog = catalog
        self.productIDs = catalog.map(\.productID)
    }

    func loadProducts() async throws -> [SubscriptionProduct] {
        let fetchedProducts = try await Product.products(for: productIDs)
        cachedProducts = Dictionary(uniqueKeysWithValues: fetchedProducts.map { ($0.id, $0) })

        return Self.mapLoadedProducts(fetchedProducts, orderedBy: productIDs)
    }

    func purchase(productID: String) async throws -> StorePurchaseResult {
        let product = try await product(for: productID)
        let result = try await product.purchase()

        switch result {
        case .success(let verification):
            switch verification {
            case .verified(let transaction):
                let mappedTransaction = mapTransaction(transaction)
                await transaction.finish()
                return .success(mappedTransaction)
            case .unverified:
                throw StoreKitAdapterError.unverifiedTransaction
            }
        case .userCancelled:
            return .cancelled
        case .pending:
            return .pending
        @unknown default:
            throw StoreKitAdapterError.unsupportedPurchaseResult
        }
    }

    func sync() async throws {
        try await AppStore.sync()
    }

    func latestVerifiedEntitlementTransaction() async -> StoreEntitlementTransaction? {
        for await result in Transaction.currentEntitlements {
            guard case .verified(let transaction) = result else {
                continue
            }
            guard managesProductID(transaction.productID) else {
                continue
            }
            return mapTransaction(transaction)
        }
        return nil
    }

    func currentReceiptData() async throws -> String {
        guard let receiptURL = Bundle.main.appStoreReceiptURL else {
            throw StoreKitAdapterError.missingReceipt
        }

        do {
            let data = try await Task.detached(priority: .utility) {
                try Data(contentsOf: receiptURL)
            }.value
            guard data.isEmpty == false else {
                throw StoreKitAdapterError.missingReceipt
            }
            return data.base64EncodedString()
        } catch let adapterError as StoreKitAdapterError {
            throw adapterError
        } catch {
            throw StoreKitAdapterError.receiptReadFailed(error.localizedDescription)
        }
    }

    private func product(for productID: String) async throws -> Product {
        if let cachedProduct = cachedProducts[productID] {
            return cachedProduct
        }

        let fetchedProducts = try await Product.products(for: [productID])
        guard let product = fetchedProducts.first else {
            throw StoreKitAdapterError.productNotFound(productID)
        }
        cachedProducts[product.id] = product
        return product
    }

    func managesProductID(_ productID: String) -> Bool {
        catalog.contains { $0.productID == productID }
    }

    nonisolated static func mapLoadedProducts<ProductView: StoreKitDisplayProduct>(
        _ fetchedProducts: [ProductView],
        orderedBy productIDs: [String]
    ) -> [SubscriptionProduct] {
        let productsByID = Dictionary(uniqueKeysWithValues: fetchedProducts.map { ($0.id, $0) })

        return productIDs.compactMap { productID in
            guard let product = productsByID[productID] else {
                return nil
            }
            return SubscriptionProduct(
                id: product.id,
                displayName: product.displayName,
                displayPrice: product.displayPrice
            )
        }
    }


    private func mapTransaction(_ transaction: Transaction) -> StoreEntitlementTransaction {
        StoreEntitlementTransaction(
            transactionID: String(transaction.id),
            originalTransactionID: String(transaction.originalID),
            productID: transaction.productID
        )
    }
}
