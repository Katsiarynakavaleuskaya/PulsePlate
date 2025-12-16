import Foundation
@testable import PulsePlate

enum ShoppingListFixtures {
    static func dtoEmptyWithWarning() -> ShoppingListDTO {
        ShoppingListDTO(
            categories: [],
            totalItems: 0,
            generatedAt: "2025-12-15T10:00:00Z",
            meta: ShoppingListMetaDTO(
                source: "inline_plan",
                unitSystem: "metric",
                warnings: ["missing_ingredients"]
            )
        )
    }

    static func dtoSimple() -> ShoppingListDTO {
        ShoppingListDTO(
            categories: [
                ShoppingListCategoryDTO(
                    key: "grains",
                    title: "Grains",
                    items: [
                        ShoppingListItemDTO(
                            key: "rice",
                            name: "Rice",
                            quantity: 350.0,
                            unit: "g",
                            recipeRefs: ["breakfast", "lunch"]
                        )
                    ]
                )
            ],
            totalItems: 1,
            generatedAt: "2025-12-15T10:00:00Z",
            meta: ShoppingListMetaDTO(
                source: "inline_plan",
                unitSystem: "metric",
                warnings: []
            )
        )
    }

    static func requestBodyJSON(plan: ShoppingPlan, preferences: [String: Any]? = nil) throws -> Data {
        let payload = ShoppingListRequestPayload(planData: plan, preferences: preferences)
        return try JSONEncoder().encode(payload)
    }
}
