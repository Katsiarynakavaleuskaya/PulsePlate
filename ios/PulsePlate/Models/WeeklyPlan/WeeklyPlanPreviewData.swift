import Foundation

/// Preview data fixtures for Weekly Plan Reader
///
/// Provides realistic mock data for SwiftUI previews and UI testing.
/// Use in #Preview macros to validate UI states without running the app.
public enum WeeklyPlanPreviewData {

    // MARK: - Complete Plans

    /// Full 7-day plan with all sections populated
    public static let loadedPlan = WeeklyPlanVM(
        days: [
            dayMonday,
            dayTuesday,
            dayWednesday,
            dayThursday,
            dayFriday,
            daySaturday,
            daySunday
        ],
        weeklyCoverage: fullCoverage,
        weeklyAdherence: 0.92,
        totalCost: 87.50,
        shoppingList: sampleShoppingList
    )

    /// Minimal valid plan (1 day, 1 meal)
    public static let minimalPlan = WeeklyPlanVM(
        days: [
            DayPlanVM(
                dayName: "Monday",
                date: "Dec 16",
                sections: [
                    MealSectionVM(
                        mealType: .breakfast,
                        items: [
                            RecipeItemVM(
                                name: "Oatmeal with Berries",
                                quantity: "1 serving",
                                kcal: 320
                            )
                        ],
                        totalKcal: 320
                    )
                ],
                macros: MacroTotalsVM(kcal: 320, proteinG: 12, fatG: 8, carbsG: 52)
            )
        ],
        weeklyCoverage: nil,
        weeklyAdherence: nil,
        totalCost: nil,
        shoppingList: nil
    )

    // MARK: - Individual Days

    private static let dayMonday = DayPlanVM(
        dayName: "Monday",
        date: "Dec 16",
        sections: [
            MealSectionVM(
                mealType: .breakfast,
                items: [
                    RecipeItemVM(name: "Greek Yogurt Bowl", quantity: "1 bowl", kcal: 280),
                    RecipeItemVM(name: "Granola", quantity: "30g", kcal: 140)
                ],
                totalKcal: 420
            ),
            MealSectionVM(
                mealType: .lunch,
                items: [
                    RecipeItemVM(name: "Grilled Chicken Salad", quantity: "1 plate", kcal: 480),
                    RecipeItemVM(name: "Olive Oil Dressing", quantity: "2 tbsp", kcal: 80)
                ],
                totalKcal: 560
            ),
            MealSectionVM(
                mealType: .dinner,
                items: [
                    RecipeItemVM(name: "Salmon Fillet", quantity: "150g", kcal: 310),
                    RecipeItemVM(name: "Roasted Vegetables", quantity: "200g", kcal: 120),
                    RecipeItemVM(name: "Quinoa", quantity: "100g", kcal: 220)
                ],
                totalKcal: 650
            ),
            MealSectionVM(
                mealType: .snacks,
                items: [
                    RecipeItemVM(name: "Apple", quantity: "1 medium", kcal: 95),
                    RecipeItemVM(name: "Almonds", quantity: "20g", kcal: 115)
                ],
                totalKcal: 210
            )
        ],
        macros: MacroTotalsVM(kcal: 1840, proteinG: 98, fatG: 62, carbsG: 185)
    )

    private static let dayTuesday = DayPlanVM(
        dayName: "Tuesday",
        date: "Dec 17",
        sections: [
            MealSectionVM(
                mealType: .breakfast,
                items: [RecipeItemVM(name: "Scrambled Eggs", quantity: "2 eggs", kcal: 360)],
                totalKcal: 360
            ),
            MealSectionVM(
                mealType: .lunch,
                items: [RecipeItemVM(name: "Lentil Soup", quantity: "300ml", kcal: 420)],
                totalKcal: 420
            ),
            MealSectionVM(
                mealType: .dinner,
                items: [RecipeItemVM(name: "Chicken Stir-Fry", quantity: "1 plate", kcal: 580)],
                totalKcal: 580
            )
        ],
        macros: MacroTotalsVM(kcal: 1360, proteinG: 82, fatG: 48, carbsG: 142)
    )

    private static let dayWednesday = DayPlanVM(
        dayName: "Wednesday",
        date: "Dec 18",
        sections: [
            MealSectionVM(
                mealType: .breakfast,
                items: [RecipeItemVM(name: "Protein Smoothie", quantity: "1 glass", kcal: 320)],
                totalKcal: 320
            ),
            MealSectionVM(
                mealType: .lunch,
                items: [RecipeItemVM(name: "Turkey Wrap", quantity: "1 wrap", kcal: 520)],
                totalKcal: 520
            ),
            MealSectionVM(
                mealType: .dinner,
                items: [RecipeItemVM(name: "Beef Tacos", quantity: "3 tacos", kcal: 680)],
                totalKcal: 680
            )
        ],
        macros: MacroTotalsVM(kcal: 1520, proteinG: 92, fatG: 54, carbsG: 158)
    )

    private static let dayThursday = DayPlanVM(
        dayName: "Thursday",
        date: "Dec 19",
        sections: [
            MealSectionVM(
                mealType: .breakfast,
                items: [RecipeItemVM(name: "Avocado Toast", quantity: "2 slices", kcal: 380)],
                totalKcal: 380
            ),
            MealSectionVM(
                mealType: .lunch,
                items: [RecipeItemVM(name: "Pasta Primavera", quantity: "1 plate", kcal: 560)],
                totalKcal: 560
            ),
            MealSectionVM(
                mealType: .dinner,
                items: [RecipeItemVM(name: "Baked Cod", quantity: "1 fillet", kcal: 520)],
                totalKcal: 520
            )
        ],
        macros: MacroTotalsVM(kcal: 1460, proteinG: 78, fatG: 52, carbsG: 172)
    )

    private static let dayFriday = DayPlanVM(
        dayName: "Friday",
        date: "Dec 20",
        sections: [
            MealSectionVM(
                mealType: .breakfast,
                items: [RecipeItemVM(name: "Pancakes", quantity: "3 pancakes", kcal: 420)],
                totalKcal: 420
            ),
            MealSectionVM(
                mealType: .lunch,
                items: [RecipeItemVM(name: "Caesar Salad", quantity: "1 bowl", kcal: 480)],
                totalKcal: 480
            ),
            MealSectionVM(
                mealType: .dinner,
                items: [RecipeItemVM(name: "Pizza", quantity: "3 slices", kcal: 720)],
                totalKcal: 720
            )
        ],
        macros: MacroTotalsVM(kcal: 1620, proteinG: 68, fatG: 62, carbsG: 198)
    )

    private static let daySaturday = DayPlanVM(
        dayName: "Saturday",
        date: "Dec 21",
        sections: [
            MealSectionVM(
                mealType: .breakfast,
                items: [RecipeItemVM(name: "French Toast", quantity: "2 slices", kcal: 380)],
                totalKcal: 380
            ),
            MealSectionVM(
                mealType: .lunch,
                items: [RecipeItemVM(name: "Veggie Burger", quantity: "1 burger", kcal: 520)],
                totalKcal: 520
            ),
            MealSectionVM(
                mealType: .dinner,
                items: [RecipeItemVM(name: "Steak", quantity: "200g", kcal: 640)],
                totalKcal: 640
            )
        ],
        macros: MacroTotalsVM(kcal: 1540, proteinG: 88, fatG: 58, carbsG: 162)
    )

    private static let daySunday = DayPlanVM(
        dayName: "Sunday",
        date: "Dec 22",
        sections: [
            MealSectionVM(
                mealType: .breakfast,
                items: [RecipeItemVM(name: "Waffles", quantity: "2 waffles", kcal: 400)],
                totalKcal: 400
            ),
            MealSectionVM(
                mealType: .lunch,
                items: [RecipeItemVM(name: "Sushi Platter", quantity: "12 pieces", kcal: 580)],
                totalKcal: 580
            ),
            MealSectionVM(
                mealType: .dinner,
                items: [RecipeItemVM(name: "Roast Chicken", quantity: "1/4 chicken", kcal: 620)],
                totalKcal: 620
            )
        ],
        macros: MacroTotalsVM(kcal: 1600, proteinG: 94, fatG: 56, carbsG: 168)
    )

    // MARK: - Weekly Coverage

    private static let fullCoverage: [CoverageItemVM] = [
        CoverageItemVM(label: "Protein", percent: 105),
        CoverageItemVM(label: "Vitamin C", percent: 98),
        CoverageItemVM(label: "Iron", percent: 87),
        CoverageItemVM(label: "Calcium", percent: 112),
        CoverageItemVM(label: "Vitamin D", percent: 78),
        CoverageItemVM(label: "Omega 3", percent: 92),
        CoverageItemVM(label: "Fiber", percent: 102),
        CoverageItemVM(label: "Vitamin B12", percent: 95),
        CoverageItemVM(label: "Zinc", percent: 88),
        CoverageItemVM(label: "Magnesium", percent: 110)
    ]

    // MARK: - Shopping List

    /// Shopping list quantities
    /// - Weights in grams (e.g., Chicken Breast: 800)
    /// - Liquids in ml (e.g., Olive Oil: 250)
    /// - Discrete items as count (e.g., Eggs: 12)
    private static let sampleShoppingList: [String: Double] = [
        "Chicken Breast": 800,
        "Salmon Fillet": 300,
        "Greek Yogurt": 500,
        "Eggs": 12,
        "Quinoa": 200,
        "Almonds": 100,
        "Spinach": 300,
        "Tomatoes": 500,
        "Olive Oil": 250,
        "Oats": 400
    ]
}
