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

    static func requestBodyJSON(planDataEncoded: Data, preferences: [String: Any]? = nil) throws -> Data {
        // Decode the encoded plan data to embed it in the payload
        let planObject = try JSONSerialization.jsonObject(with: planDataEncoded, options: [])
        var payload: [String: Any] = ["plan_data": planObject]
        if let preferences {
            payload["preferences"] = preferences
        }
        return try JSONSerialization.data(withJSONObject: payload, options: [])
    }
}
