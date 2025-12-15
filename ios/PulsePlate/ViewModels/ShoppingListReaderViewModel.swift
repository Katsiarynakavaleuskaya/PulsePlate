import Foundation
import Combine

@MainActor
final class ShoppingListReaderViewModel: ObservableObject {
    enum State: Equatable {
        case idle
        case loading
        case loaded(ShoppingListViewData)
        case error(String)
    }

    @Published private(set) var state: State = .idle

    private let service: ShoppingListServicing
    private let apiKeyProvider: () -> String?

    init(service: ShoppingListServicing, apiKeyProvider: @escaping () -> String?) {
        self.service = service
        self.apiKeyProvider = apiKeyProvider
    }

    func load(planData: [String: Any], preferences: [String: Any]? = nil) async {
        state = .loading
        do {
            let body = try ShoppingListFixtures.requestBodyJSON(planData: planData, preferences: preferences)
            let request = ShoppingListRequest(
                endpointPath: "/api/v1/pro/meal/shopping-list",
                body: body,
                apiKey: apiKeyProvider()
            )

            let dto = try await service.fetchShoppingList(request: request)
            let viewData = ShoppingListAdapter.adapt(dto: dto)
            state = .loaded(viewData)
        } catch {
            state = .error(error.localizedDescription)
        }
    }
}
