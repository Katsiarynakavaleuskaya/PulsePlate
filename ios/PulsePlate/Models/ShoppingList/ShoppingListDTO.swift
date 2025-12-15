import Foundation

/// Raw API response from POST /api/v1/pro/meal/shopping-list
/// Strongly typed DTO matching backend contract with categorized items
public struct ShoppingListDTO: Codable, Sendable, Equatable {
    public let categories: [ShoppingListCategoryDTO]
    public let totalItems: Int
    public let generatedAt: String
    public let meta: ShoppingListMetaDTO

    enum CodingKeys: String, CodingKey {
        case categories
        case totalItems = "total_items"
        case generatedAt = "generated_at"
        case meta
    }
}

public struct ShoppingListMetaDTO: Codable, Sendable, Equatable {
    public let source: String
    public let unitSystem: String
    public let warnings: [String]

    enum CodingKeys: String, CodingKey {
        case source
        case unitSystem = "unit_system"
        case warnings
    }
}

public struct ShoppingListCategoryDTO: Codable, Sendable, Equatable, Identifiable {
    public var id: String { key }
    public let key: String
    public let title: String
    public let items: [ShoppingListItemDTO]
}

public struct ShoppingListItemDTO: Codable, Sendable, Equatable, Identifiable {
    public var id: String { key }
    public let key: String
    public let name: String
    public let quantity: Double
    public let unit: String
    public let recipeRefs: [String]

    enum CodingKeys: String, CodingKey {
        case key, name, quantity, unit
        case recipeRefs = "recipe_refs"
    }
}
