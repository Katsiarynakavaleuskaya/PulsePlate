import Testing
@testable import PulsePlate

struct WeeklyPlanMealTypeTests {
    @Test func mealType_mapsBackendStrings() {
        // Backend-defined meal types (matches Python core/meal_types.py)
        #expect(MealType(rawValue: "breakfast") == .breakfast)
        #expect(MealType(rawValue: "morning_snack") == .morningSnack)
        #expect(MealType(rawValue: "lunch") == .lunch)
        #expect(MealType(rawValue: "afternoon_snack") == .afternoonSnack)
        #expect(MealType(rawValue: "dinner") == .dinner)
        #expect(MealType(rawValue: "evening_snack") == .eveningSnack)
    }

    @Test func mealType_sortRank_ordersMealsPredictably() {
        let ordered: [MealType] = [
            .breakfast, .morningSnack, .lunch, .afternoonSnack, .dinner, .eveningSnack, .snacks, .other
        ]
        let shuffled = ordered.shuffled()
        let sorted = shuffled.sorted { $0.sortRank < $1.sortRank }
        #expect(sorted == ordered)
    }

    @Test func mealType_rawValue_roundTrip() {
        // Verify all cases can round-trip through rawValue
        for mealType in MealType.allCases {
            let recreated = MealType(rawValue: mealType.rawValue)
            #expect(recreated == mealType)
        }
    }

    @Test func mealType_sortRank_isUnique() {
        // Verify no duplicate sort ranks (would cause unstable sorting)
        let ranks = MealType.allCases.map { $0.sortRank }
        let uniqueRanks = Set(ranks)
        #expect(ranks.count == uniqueRanks.count)
    }
}
