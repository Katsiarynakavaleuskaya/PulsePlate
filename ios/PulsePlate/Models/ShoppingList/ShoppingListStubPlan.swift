import Foundation

enum ShoppingListStubPlan {
    static func minimal() -> [String: Any] {
        [
            "daily_menus": [
                [
                    "meals": [
                        [
                            "title": "oatmeal_banana",
                            "grams": [
                                "oats": 80.0,
                                "banana": 120.0,
                                "milk": 200.0
                            ]
                        ]
                    ]
                ]
            ]
        ]
    }
}
