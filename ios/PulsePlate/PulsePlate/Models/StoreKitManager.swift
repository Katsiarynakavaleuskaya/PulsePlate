import Foundation
import Combine
import StoreKit

@MainActor
final class StoreKitManager: ObservableObject {

    @Published var isPremium = false
    @Published var products: [Product] = []
    @Published var error: Error?

    private let productIds = ["com.pulseplate.premium.monthly", "com.pulseplate.premium.yearly"]

    init() {
        Task { [weak self] in
            await self?.loadProducts()
            await self?.updatePurchaseStatus()
        }
    }

    func loadProducts() async {
        do {
            products = try await Product.products(for: productIds)
        } catch {
            self.error = error
        }
    }

    func updatePurchaseStatus() async {
        var premiumActive = false
        for await result in Transaction.currentEntitlements {
            if case .verified(let transaction) = result,
               transaction.productID.contains("premium") {
                premiumActive = true
                break
            }
        }
        isPremium = premiumActive
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
        do {
            try await AppStore.sync()
            await updatePurchaseStatus()
        } catch {
            await MainActor.run {
                self.error = error
            }
        }
    }
}
