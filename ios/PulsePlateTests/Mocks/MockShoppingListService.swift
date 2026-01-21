import Foundation
@testable import PulsePlate

// Test-only mock.
// Safety: used from a single executor (MainActor) in unit tests; CI runs unit tests with parallel testing disabled.
@MainActor
final class MockShoppingListService: ShoppingListServicing, @unchecked Sendable {
    var result: Result<ShoppingListDTO, Error>

    init(result: Result<ShoppingListDTO, Error> = .success(ShoppingListFixtures.dtoSimple())) {
        self.result = result
    }

    func fetchShoppingList(request: ShoppingListRequest) async throws -> ShoppingListDTO {
        switch result {
        case .success(let dto):
            return dto
        case .failure(let error):
            throw error
        }
    }
}
