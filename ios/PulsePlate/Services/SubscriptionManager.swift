import Combine
import Foundation
import OSLog

struct SubscriptionErrorState: Equatable, Sendable {
    let message: String
}

enum ProductCatalogState: Equatable, Sendable {
    case idle
    case loading
    case loaded
    case failed(String)
}

enum SubscriptionFlowState: Equatable, Sendable {
    case idle
    case purchasing
    case sendingReceipt
    case refreshingEntitlement
    case restoring
    case pendingApproval
    case unlocked
    case failed(String)
}

enum EntitlementRefreshTrigger: Sendable {
    case launch
    case foreground
    case postPurchase
    case postRestore
    case manualRetry
}

enum ActiveSubscriptionOperation: Equatable, Sendable {
    case purchase
    case restore
    case refreshLaunch
    case refreshForeground
    case refreshManual

    var isRefresh: Bool {
        switch self {
        case .refreshLaunch, .refreshForeground, .refreshManual:
            return true
        case .purchase, .restore:
            return false
        }
    }
}

struct EntitlementSnapshot: Equatable, Sendable {
    let activationID: String
    let tier: String
    let status: String
    let expiresAt: Date?
    let productID: String?
}

enum SubscriptionManagerError: Error, Equatable, Sendable {
    case missingAPIKey
    case missingActivationID
    case missingActivationPayload
    case restoreTransactionMissing
}

extension SubscriptionManagerError: LocalizedError {
    var errorDescription: String? {
        switch self {
        case .missingAPIKey:
            return "Subscription flow requires a configured API key."
        case .missingActivationID:
            return "Subscription activation id is unavailable."
        case .missingActivationPayload:
            return "Backend verification did not return an activation payload."
        case .restoreTransactionMissing:
            return "Restore did not produce a verified entitlement transaction."
        }
    }
}

@MainActor
final class SubscriptionManager: ObservableObject {
    private static let iso8601Formatters: [ISO8601DateFormatter] = {
        let fractionalFormatter = ISO8601DateFormatter()
        fractionalFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        let basicFormatter = ISO8601DateFormatter()
        basicFormatter.formatOptions = [.withInternetDateTime]

        return [fractionalFormatter, basicFormatter]
    }()
    private static let logger = Logger(
        subsystem: "PulsePlate",
        category: "SubscriptionManager"
    )

    @Published private(set) var products: [SubscriptionProduct] = []
    @Published private(set) var catalogState: ProductCatalogState = .idle
    @Published private(set) var flowState: SubscriptionFlowState = .idle
    @Published private(set) var entitlement: EntitlementSnapshot?
    @Published private(set) var lastError: SubscriptionErrorState?

    private let storeKitManager: StoreKitManaging
    private let billingService: SubscriptionBillingServicing
    private let activationPointerStore: ActivationPointerStoring
    private let apiKeyProvider: @Sendable () -> String?

    private var hasBootstrapped = false
    private var activeOperation: ActiveSubscriptionOperation?
    private var operationToken = UUID()

    init(
        storeKitManager: StoreKitManaging? = nil,
        billingService: SubscriptionBillingServicing? = nil,
        activationPointerStore: ActivationPointerStoring = UserDefaultsActivationPointerStore(),
        apiKeyProvider: @escaping @Sendable () -> String? = { ProKeyProvider.value() }
    ) {
        self.storeKitManager = storeKitManager ?? StoreKitManager()
        self.activationPointerStore = activationPointerStore
        self.apiKeyProvider = apiKeyProvider

        if let billingService {
            self.billingService = billingService
        } else {
            self.billingService = SubscriptionBillingService(
                apiClient: APIClient(baseURL: AppConfig.baseURL())
            )
        }
    }

    func bootstrap() async {
        guard hasBootstrapped == false else {
            return
        }
        hasBootstrapped = true

        if activationPointerStore.loadActivationID() != nil {
            async let productLoad: Void = loadProducts()
            await refreshEntitlement(trigger: .launch)
            _ = await productLoad
            return
        }

        await loadProducts()
    }

    func loadProducts() async {
        guard catalogState != .loading else {
            return
        }

        catalogState = .loading
        do {
            products = try await storeKitManager.loadProducts()
            catalogState = .loaded
        } catch {
            products = []
            catalogState = .failed(describe(error))
        }
    }

    func purchase(productID: String) async {
        guard let token = startOperation(.purchase) else {
            return
        }

        clearErrorState()
        flowState = .purchasing

        do {
            let apiKey = try requiredAPIKey()
            let purchaseResult = try await storeKitManager.purchase(productID: productID)

            switch purchaseResult {
            case .cancelled:
                finishOperation(.purchase, token: token)
                flowState = .idle
                return
            case .pending:
                finishOperation(.purchase, token: token)
                flowState = .pendingApproval
                return
            case .success:
                let receiptData = try await storeKitManager.currentReceiptData()
                flowState = .sendingReceipt
                let verification = try await billingService.verifyReceipt(
                    receiptData: receiptData,
                    apiKey: apiKey
                )
                let activationRequest = try makeActivationRequest(
                    receiptData: receiptData,
                    verification: verification
                )
                let activation = try await billingService.activateSubscription(
                    request: activationRequest,
                    apiKey: apiKey
                )
                let activationID = try validatedActivationID(activation.activationID)
                activationPointerStore.saveActivationID(activationID)
                finishOperation(.purchase, token: token)
                await refreshEntitlement(trigger: .postPurchase)
            }
        } catch {
            failOperation(.purchase, token: token, error: error)
        }
    }

    func restore() async {
        guard let token = startOperation(.restore) else {
            return
        }

        clearErrorState()
        flowState = .restoring

        do {
            let apiKey = try requiredAPIKey()
            try await storeKitManager.sync()
            guard let transaction = await storeKitManager.latestVerifiedEntitlementTransaction() else {
                throw SubscriptionManagerError.restoreTransactionMissing
            }
            let receiptData = try await storeKitManager.currentReceiptData()
            flowState = .sendingReceipt
            let verification = try await billingService.verifyReceipt(
                receiptData: receiptData,
                apiKey: apiKey
            )
            let activationRequest = try makeActivationRequest(
                receiptData: receiptData,
                verification: verification
            )
            let activation = try await billingService.activateSubscription(
                request: activationRequest,
                apiKey: apiKey
            )
            let activationID = try validatedActivationID(activation.activationID)
            activationPointerStore.saveActivationID(activationID)
            finishOperation(.restore, token: token)
            await refreshEntitlement(trigger: .postRestore)
        } catch {
            failOperation(.restore, token: token, error: error)
        }
    }

    func refreshEntitlement(trigger: EntitlementRefreshTrigger) async {
        let operation = operation(for: trigger)
        guard let token = startOperation(operation) else {
            return
        }

        guard let rawActivationID = activationPointerStore.loadActivationID() else {
            finishOperation(operation, token: token)
            clearErrorState()
            entitlement = nil
            flowState = .idle
            return
        }

        let storedActivationID: String
        do {
            storedActivationID = try validatedActivationID(rawActivationID)
        } catch {
            activationPointerStore.clearActivationID()
            finishOperation(operation, token: token)
            clearErrorState()
            entitlement = nil
            flowState = .idle
            return
        }

        do {
            let apiKey = try requiredAPIKey()
            clearErrorState()
            flowState = .refreshingEntitlement
            let activation = try await billingService.fetchActivationStatus(
                activationID: storedActivationID,
                apiKey: apiKey
            )

            if shouldClearPointer(for: activation) {
                activationPointerStore.clearActivationID()
                entitlement = nil
                finishOperation(operation, token: token)
                flowState = .idle
                clearErrorState()
                return
            }

            let activationID = try validatedActivationID(activation.activationID)
            let snapshot = makeEntitlementSnapshot(
                from: activation,
                activationID: activationID
            )
            entitlement = snapshot
            activationPointerStore.saveActivationID(snapshot.activationID)
            finishOperation(operation, token: token)
            clearErrorState()
            flowState = shouldUnlockEntitlement(for: activation) ? .unlocked : .idle
        } catch {
            if isStalePointerError(error) {
                activationPointerStore.clearActivationID()
                entitlement = nil
                finishOperation(operation, token: token)
                clearErrorState()
                flowState = .idle
                return
            }

            entitlement = nil
            failOperation(operation, token: token, error: error)
        }
    }

    private func requiredAPIKey() throws -> String {
        guard let apiKey = apiKeyProvider()?.trimmingCharacters(in: .whitespacesAndNewlines),
              apiKey.isEmpty == false
        else {
            throw SubscriptionManagerError.missingAPIKey
        }
        return apiKey
    }

    private func makeActivationRequest(
        receiptData: String,
        verification: AppleReceiptVerificationResponseDTO
    ) throws -> ActivateSubscriptionRequestDTO {
        guard let verificationResult = verification.activationPayload else {
            throw SubscriptionManagerError.missingActivationPayload
        }

        // RU: `activationPayload` — это канонический backend handoff для activate-запроса.
        // `verificationState` остаётся envelope-метаданными verify-ответа и намеренно не
        // ремапится здесь, чтобы клиент не реконструировал billing truth локально.
        // EN: `activationPayload` is the canonical backend handoff for the activate request.
        // `verificationState` stays verify-response envelope metadata and is intentionally
        // not remapped here so the client does not reconstruct billing truth locally.
        return ActivateSubscriptionRequestDTO(
            source: .iosAppStore,
            payload: IOSAppStoreActivationPayloadDTO(
                verificationResult: verificationResult,
                receiptData: receiptData
            )
        )
    }

    private func makeEntitlementSnapshot(
        from response: SubscriptionActivationResponseDTO,
        activationID: String
    ) -> EntitlementSnapshot {
        EntitlementSnapshot(
            activationID: activationID,
            tier: (response.tier ?? response.subscriptionTier ?? "").lowercased(),
            status: response.status.lowercased(),
            expiresAt: parseISO8601(response.expiresAt),
            productID: response.productID
        )
    }

    private func validatedActivationID(_ rawValue: String) throws -> String {
        let normalizedValue = rawValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard normalizedValue.isEmpty == false else {
            Self.logger.error("Subscription activation id validation failed: blank or whitespace-only value.")
            throw SubscriptionManagerError.missingActivationID
        }
        return normalizedValue
    }


    private func parseISO8601(_ value: String?) -> Date? {
        guard let value, value.isEmpty == false else {
            return nil
        }
        for formatter in SubscriptionManager.iso8601Formatters {
            if let parsedDate = formatter.date(from: value) {
                return parsedDate
            }
        }
        return nil
    }

    private func shouldClearPointer(for response: SubscriptionActivationResponseDTO) -> Bool {
        let normalizedStatus = response.status.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return ["expired", "rejected", "cancelled"].contains(normalizedStatus)
    }

    private func isStalePointerError(_ error: Error) -> Bool {
        guard let statusCode = apiStatusCode(from: error) else {
            return false
        }
        return statusCode == 403 || statusCode == 404 || statusCode == 410
    }

    private func shouldUnlockEntitlement(for response: SubscriptionActivationResponseDTO) -> Bool {
        let normalizedStatus = response.status.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return ["active", "restored"].contains(normalizedStatus)
    }

    private func apiStatusCode(from error: Error) -> Int? {
        guard let apiError = error as? APIError else {
            return nil
        }

        switch apiError {
        case .api(let statusCode, _):
            return statusCode
        case .emptyResponse(let statusCode):
            return statusCode
        case .validation, .transport, .unknown, .encodingFailed, .decodingFailed, .invalidResponse, .unhandledStatusCode:
            return nil
        }
    }

    private func operation(for trigger: EntitlementRefreshTrigger) -> ActiveSubscriptionOperation {
        switch trigger {
        case .launch:
            return .refreshLaunch
        case .foreground:
            return .refreshForeground
        case .postPurchase, .postRestore, .manualRetry:
            return .refreshManual
        }
    }

    private func startOperation(_ operation: ActiveSubscriptionOperation) -> UUID? {
        if let currentOperation = activeOperation {
            switch operation {
            case .purchase, .restore:
                return nil
            case .refreshLaunch, .refreshForeground, .refreshManual:
                if currentOperation == .purchase || currentOperation == .restore || currentOperation.isRefresh {
                    return nil
                }
            }
        }

        let token = UUID()
        activeOperation = operation
        operationToken = token
        return token
    }

    private func finishOperation(_ operation: ActiveSubscriptionOperation, token: UUID) {
        guard activeOperation == operation, operationToken == token else {
            return
        }
        activeOperation = nil
    }

    private func failOperation(
        _ operation: ActiveSubscriptionOperation,
        token: UUID,
        error: Error
    ) {
        finishOperation(operation, token: token)
        let message = describe(error)
        lastError = SubscriptionErrorState(message: message)
        flowState = .failed(message)
    }

    private func clearErrorState() {
        lastError = nil
        if case .failed = flowState {
            flowState = .idle
        }
    }

    private func describe(_ error: Error) -> String {
        if let localizedError = error as? LocalizedError,
           let description = localizedError.errorDescription,
           description.isEmpty == false {
            return description
        }
        return error.localizedDescription
    }
}

private extension String {
    var nilIfEmpty: String? {
        let trimmed = trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.isEmpty ? nil : trimmed
    }
}
