import Foundation
@testable import PulsePlate

// Test-only mock. Used from a single thread in unit tests.
final class MockShoppingListService: ShoppingListServicing, @unchecked Sendable {
    var result: Result<ShoppingListDTO, Error> = .success(ShoppingListFixtures.dtoSimple())

    func fetchShoppingList(request: ShoppingListRequest) async throws -> ShoppingListDTO {
        switch result {
        case .success(let dto):
            return dto
        case .failure(let error):
            throw error
        }
    }
}
