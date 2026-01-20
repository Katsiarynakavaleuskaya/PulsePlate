import Foundation

// MARK: - Typed Stub Plan Models

/// Represents a weekly shopping plan with typed structure
public struct ShoppingPlan: Codable {
    let dailyMenus: [DailyMenu]

    enum CodingKeys: String, CodingKey {
        case dailyMenus = "daily_menus"
    }
}

/// Represents a day's menu with meals
struct DailyMenu: Codable {
    let meals: [Meal]
}

/// Represents a single meal with ingredients
struct Meal: Codable {
    let title: String
    let grams: [String: Double]
}

enum ShoppingListStubPlan {
    /// Returns a minimal typed stub plan for testing
    static func minimal() -> ShoppingPlan {
        ShoppingPlan(
            dailyMenus: [
                DailyMenu(
                    meals: [
                        Meal(
                            title: "oatmeal_banana",
                            grams: [
                                "oats": 80.0,
                                "banana": 120.0,
                                "milk": 200.0
                            ]
                        )
                    ]
                )
            ]
        )
    }

    /// Returns encoded JSON Data for API stub responses
    static func minimalData() throws -> Data {
        try JSONEncoder().encode(minimal())
    }
}
