import StoreKit
import SwiftUI

/// Minimal paywall screen powered by StoreKitManager.
///
/// This is wiring/UI only:
/// - No tier/business logic in the client.
/// - Purchases are handled by StoreKit.
struct PaywallScreen: View {
    @StateObject private var storeKit = StoreKitManager()

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Upgrade to PRO")
                        .font(.title3.weight(.semibold))
                    Text("Unlock more detailed wellness insights and planning features.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 6)
            }

            if storeKit.isPremium {
                Section {
                    Label("Premium active", systemImage: "checkmark.seal.fill")
                        .foregroundStyle(.green)
                }
            }

            Section("Plans") {
                if storeKit.products.isEmpty {
                    Text("Loading plans…")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(storeKit.products, id: \.id) { product in
                        Button {
                            Task { await storeKit.purchase(product) }
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(product.displayName)
                                    Text(product.displayPrice)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Image(systemName: "chevron.right")
                                    .foregroundStyle(.tertiary)
                            }
                        }
                    }
                }
            }

            Section {
                Button("Restore Purchases") {
                    Task { await storeKit.restorePurchases() }
                }
            }

            if let error = storeKit.error {
                Section("Error") {
                    Text(error.localizedDescription)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("PRO")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    NavigationStack {
        PaywallScreen()
    }
}
