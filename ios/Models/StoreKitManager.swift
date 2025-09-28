import Foundation
import StoreKit

class StoreKitManager: ObservableObject {
    @Published var isPremium = false
    @Published var products: [Product] = []
    @Published var error: Error?

    private var productIds = ["com.pulseplate.premium.monthly", "com.pulseplate.premium.yearly"]

    private var transactionUpdatesTask: Task<Void, Never>?

    init() {
        Task {
            await loadProducts()
            await updatePurchaseStatus()
        }

        // Subscribe to Transaction.updates to stay in sync with live changes
        transactionUpdatesTask = Task {
            for await result in Transaction.updates {
                do {
                    let transaction = try result.get()
                    await transaction.finish()
                    await updatePurchaseStatus()
                } catch {
                    // Handle transaction update errors
                    await MainActor.run {
                        self.error = error
                    }
                }
            }
        }
    }

    deinit {
        transactionUpdatesTask?.cancel()
    }

    @MainActor
    func loadProducts() async {
        do {
            products = try await Product.products(for: productIds)
        } catch {
            self.error = error
        }
    }

    @MainActor
    func updatePurchaseStatus() async {
        var foundPremium = false
        for await result in Transaction.currentEntitlements {
            if case .verified(let transaction) = result {
                if transaction.productID.contains("premium") {
                    foundPremium = true
                    break
                }
            }
        }
        isPremium = foundPremium
    }

    func purchase(_ product: Product) async {
        do {
            let result = try await product.purchase()

            switch result {
            case .success(let verification):
                if case .verified(let transaction) = verification {
                    await transaction.finish()
                    await updatePurchaseStatus()
                }
            case .userCancelled:
                break
            case .pending:
                break
            @unknown default:
                break
            }
        } catch {
            self.error = error
        }
    }

    func restorePurchases() async {
        try? await AppStore.sync()
        await updatePurchaseStatus()
    }
}
