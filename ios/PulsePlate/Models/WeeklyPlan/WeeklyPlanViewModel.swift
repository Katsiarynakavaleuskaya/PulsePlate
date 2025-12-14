import Foundation

// MARK: - VM (UI-friendly, stable)

public struct WeeklyPlanVM: Equatable, Sendable {
    public let days: [DayPlanVM]
    public let weeklyCoverage: [CoverageItemVM]
    public let metrics: PlanMetricsVM?
    public let shoppingList: [String: Double]?

    public init(
        days: [DayPlanVM],
        weeklyCoverage: [CoverageItemVM] = [],
        metrics: PlanMetricsVM? = nil,
        shoppingList: [String: Double]? = nil
    ) {
        self.days = days
        self.weeklyCoverage = weeklyCoverage
        self.metrics = metrics
        self.shoppingList = shoppingList
    }

    public var isEmpty: Bool { days.isEmpty }
}

public struct DayPlanVM: Equatable, Sendable, Identifiable {
    public let id: String
    public let index: Int              // 0...6
    public let title: String           // "Monday" / "Day 1"
    public let meals: [MealSectionVM]
    public let totals: MacroTotalsVM?

    public init(id: String, index: Int, title: String, meals: [MealSectionVM], totals: MacroTotalsVM? = nil) {
        self.id = id
        self.index = index
        self.title = title
        self.meals = meals
        self.totals = totals
    }
}

public struct MealSectionVM: Equatable, Sendable, Identifiable {
    public let id: String
    public let mealType: MealType
    public let title: String
    public let kcal: Int?
    public let items: [MealItemVM]

    public init(id: String, mealType: MealType, title: String, kcal: Int?, items: [MealItemVM]) {
        self.id = id
        self.mealType = mealType
        self.title = title
        self.kcal = kcal
        self.items = items
    }
}

public struct MealItemVM: Equatable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let portions: Double?

    public init(id: String, name: String, portions: Double? = nil) {
        self.id = id
        self.name = name
        self.portions = portions
    }
}

public struct MacroTotalsVM: Equatable, Sendable {
    public let kcal: Int?
    public let proteinG: Int?
    public let fatG: Int?
    public let carbsG: Int?

    public init(kcal: Int? = nil, proteinG: Int? = nil, fatG: Int? = nil, carbsG: Int? = nil) {
        self.kcal = kcal
        self.proteinG = proteinG
        self.fatG = fatG
        self.carbsG = carbsG
    }
}

public struct CoverageItemVM: Equatable, Sendable, Identifiable {
    public let id: String
    public let label: String
    public let percent: Double          // e.g. 98.5
    public let isOver: Bool

    public init(label: String, percent: Double) {
        self.id = label
        self.label = label
        self.percent = percent
        self.isOver = percent >= 100.0
    }
}

public struct PlanMetricsVM: Equatable, Sendable {
    public let totalCost: Double?
    public let adherenceScore: Double?

    public init(totalCost: Double? = nil, adherenceScore: Double? = nil) {
        self.totalCost = totalCost
        self.adherenceScore = adherenceScore
    }
}

public enum MealType: String, CaseIterable, Sendable {
    case breakfast, morningSnack = "morning_snack", lunch, afternoonSnack = "afternoon_snack", dinner, eveningSnack = "evening_snack", snacks, other

    public var emoji: String {
        switch self {
        case .breakfast: return "🍳"
        case .morningSnack: return "🍎"
        case .lunch: return "🍽️"
        case .afternoonSnack: return "🥨"
        case .dinner: return "🍴"
        case .eveningSnack: return "🍵"
        case .snacks: return "🍎"
        case .other: return "🍽️"
        }
    }

    public var displayName: String {
        switch self {
        case .breakfast: return "Breakfast"
        case .morningSnack: return "Morning snack"
        case .lunch: return "Lunch"
        case .afternoonSnack: return "Afternoon snack"
        case .dinner: return "Dinner"
        case .eveningSnack: return "Evening snack"
        case .snacks: return "Snacks"
        case .other: return "Meal"
        }
    }

    /// Sort rank for stable meal ordering: breakfast → lunch → dinner → snacks → other
    public var sortRank: Int {
        switch self {
        case .breakfast: return 0
        case .morningSnack: return 1
        case .lunch: return 2
        case .afternoonSnack: return 3
        case .dinner: return 4
        case .eveningSnack: return 5
        case .snacks: return 6
        case .other: return 7
        }
    }
}

// MARK: - Loading States
public enum WeeklyPlanState: Equatable {
    case idle
    case loading
    case loaded(WeeklyPlanVM)
    case empty
    case failed(String)

    public var isLoading: Bool {
        if case .loading = self { return true }
        return false
    }

    public var error: String? {
        if case .failed(let message) = self { return message }
        return nil
    }
}
