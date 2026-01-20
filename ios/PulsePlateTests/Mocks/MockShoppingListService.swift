import Foundation
@testable import PulsePlate

final class MockShoppingListService: ShoppingListServicing {
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
