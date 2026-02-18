import Foundation
import Combine
import os.log

@MainActor
final class ShoppingListReaderViewModel: ObservableObject {
    enum State: Equatable {
        case idle
        case loading
        case loaded(ShoppingListViewData)
        case empty  // 204 No Content or empty response
        case error(String)
    }

    @Published private(set) var state: State = .idle

    private let service: ShoppingListServicing
    private let apiKeyProvider: () -> String?
    private let logger = Logger(subsystem: "PulsePlate", category: "ShoppingListReader")

    init(service: ShoppingListServicing, apiKeyProvider: @escaping () -> String?) {
        self.service = service
        self.apiKeyProvider = apiKeyProvider
    }

    func load(planData: ShoppingPlan?, preferences: [String: Any]? = nil) async {
        guard let planData, !planData.dailyMenus.isEmpty else {
            state = .error(NSLocalizedString("shopping_list_no_plan_error", comment: ""))
            return
        }

        state = .loading
        do {
            let payload = ShoppingListRequestPayload(planData: planData, preferences: preferences)
            let body = try JSONEncoder().encode(payload)
            let request = ShoppingListRequest(
                endpointPath: "/api/v1/pro/meal/shopping-list",
                body: body,
                apiKey: apiKeyProvider()
            )

            let dto = try await service.fetchShoppingList(request: request)
            let viewData = ShoppingListAdapter.adapt(dto: dto)
            state = .loaded(viewData)
        } catch let error as APIError {
            // Transport contract: 2xx empty body is signaled as `.emptyResponse`.
            if case .emptyResponse = error {
                state = .empty
                return
            }
            handleError("Failed to fetch shopping list.", underlying: error)
        } catch {
            handleError("Failed to build request or load shopping list.", underlying: error)
        }
    }

    /// Centralized error handler: logs error details and sets user-facing error state.
    ///
    /// - Parameters:
    ///   - message: User-facing error message (shown in UI)
    ///   - underlying: Optional underlying error (logged for debugging)
    private func handleError(_ message: String, underlying: Error? = nil) {
        if let underlying {
            logger.error("\(message, privacy: .public) | \(underlying.localizedDescription, privacy: .public)")
        } else {
            logger.error("\(message, privacy: .public)")
        }
        state = .error(message)
    }
}
