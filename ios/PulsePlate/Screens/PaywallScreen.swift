import SwiftUI

struct PaywallScreen: View {
    @EnvironmentObject private var subscriptionManager: SubscriptionManager

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

            if let entitlement = subscriptionManager.entitlement, entitlement.hasPaidAccess {
                Section("Entitlement") {
                    Label("Backend access active", systemImage: "checkmark.seal.fill")
                        .foregroundStyle(.green)
                    Text("Tier: \(entitlement.tier.uppercased())")
                        .font(.footnote)
                    if let expiresAt = entitlement.expiresAt {
                        Text("Expires: \(expiresAt.formatted(date: .abbreviated, time: .shortened))")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section("Status") {
                Text(statusText)
                    .foregroundStyle(.secondary)
            }

            Section("Plans") {
                switch subscriptionManager.catalogState {
                case .idle, .loading:
                    Text("Loading plans…")
                        .foregroundStyle(.secondary)
                case .loaded:
                    if subscriptionManager.products.isEmpty {
                        Text("No plans available.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(subscriptionManager.products) { product in
                            Button {
                                Task {
                                    await subscriptionManager.purchase(productID: product.id)
                                }
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
                            .disabled(isActionDisabled)
                        }
                    }
                case .failed(let message):
                    VStack(alignment: .leading, spacing: 8) {
                        Text(message)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                        Button("Retry loading plans") {
                            Task {
                                await subscriptionManager.loadProducts()
                            }
                        }
                    }
                }
            }

            Section {
                Button("Restore Purchases") {
                    Task {
                        await subscriptionManager.restore()
                    }
                }
                .disabled(isActionDisabled)

                Button("Retry entitlement refresh") {
                    Task {
                        await subscriptionManager.refreshEntitlement(trigger: .manualRetry)
                    }
                }
                .disabled(isActionDisabled)
            }

            if let error = subscriptionManager.lastError {
                Section("Error") {
                    Text(error.message)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("PRO")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var isActionDisabled: Bool {
        switch subscriptionManager.flowState {
        case .purchasing, .sendingReceipt, .refreshingEntitlement, .restoring:
            return true
        case .idle, .pendingApproval, .unlocked, .failed:
            return false
        }
    }

    private var statusText: String {
        switch subscriptionManager.flowState {
        case .idle:
            return "Ready"
        case .purchasing:
            return "Purchasing…"
        case .sendingReceipt:
            return "Sending receipt…"
        case .refreshingEntitlement:
            return "Refreshing entitlement…"
        case .restoring:
            return "Restoring purchases…"
        case .pendingApproval:
            return "Purchase pending approval."
        case .unlocked:
            return "Paid access is unlocked by backend entitlement."
        case .failed(let message):
            return message
        }
    }
}

#Preview {
    NavigationStack {
        PaywallScreen()
            .environmentObject(SubscriptionManager())
    }
}
