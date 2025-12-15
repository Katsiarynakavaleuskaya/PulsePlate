import Foundation
@testable import PulsePlate

/// Mock service for WeeklyPlan testing with predefined states
final class MockWeeklyPlanService: WeeklyPlanServicing {
    enum MockMode {
        case loaded
        case loadedTwoDays
        case empty
        case error(String)
    }

    private let mode: MockMode
    private let delay: Duration

    init(mode: MockMode = .loaded, delay: Duration = .milliseconds(100)) {
        self.mode = mode
        self.delay = delay
    }

    func fetchWeeklyPlan(request: WeeklyPlanRequest) async throws -> WeeklyPlanDTO {
        // Simulate network delay
        try? await Task.sleep(for: delay)

        switch mode {
        case .loaded:
            return mockLoadedResponse()
        case .loadedTwoDays:
            return mockLoadedTwoDaysResponse()
        case .empty:
            return mockEmptyResponse()
        case .error(let message):
            throw MockError.serverError(message)
        }
    }

    // MARK: - Factory Methods

    static func previewLoaded() -> MockWeeklyPlanService {
        MockWeeklyPlanService(mode: .loadedTwoDays, delay: .milliseconds(300))
    }

    static func previewEmpty() -> MockWeeklyPlanService {
        MockWeeklyPlanService(mode: .empty, delay: .milliseconds(300))
    }

    static func previewError(message: String = "Failed to load weekly plan") -> MockWeeklyPlanService {
        MockWeeklyPlanService(mode: .error(message), delay: .milliseconds(300))
    }

    // MARK: - Mock Responses

    private func mockLoadedResponse() -> WeeklyPlanDTO {
        // Single day for basic testing
        WeeklyPlanDTO(
            root: .object([
                "daily_menus": .array([
                    .object([
                        "day_number": .number(1),
                        "meals": .array([
                            .object([
                                "meal_type": .string("breakfast"),
                                "title": .string("Breakfast"),
                                "kcal": .number(450),
                                "items": .array([
                                    .object([
                                        "id": .string("i1"),
                                        "name": .string("Oatmeal with berries"),
                                        "portions": .number(1.5)
                                    ])
                                ])
                            ])
                        ]),
                        "totals": .object([
                            "kcal": .number(1800),
                            "protein_g": .number(110),
                            "fat_g": .number(60),
                            "carbs_g": .number(200)
                        ])
                    ])
                ]),
                "weekly_coverage": .object([
                    "Protein": .number(95.0),
                    "Iron": .number(88.0)
                ]),
                "total_cost": .number(125.0),
                "adherence_score": .number(0.92)
            ])
        )
    }

    private func mockLoadedTwoDaysResponse() -> WeeklyPlanDTO {
        WeeklyPlanDTO(
            root: .object([
                "daily_menus": .array([
                    .object([
                        "day_number": .number(1),
                        "meals": .array([
                            .object([
                                "meal_type": .string("breakfast"),
                                "title": .string("Breakfast"),
                                "kcal": .number(450),
                                "items": .array([
                                    .object([
                                        "id": .string("i1"),
                                        "name": .string("Oatmeal with berries"),
                                        "portions": .number(1.5)
                                    ]),
                                    .object([
                                        "id": .string("i2"),
                                        "name": .string("Green tea"),
                                        "portions": .number(1.0)
                                    ])
                                ])
                            ]),
                            .object([
                                "meal_type": .string("lunch"),
                                "title": .string("Lunch"),
                                "kcal": .number(650),
                                "items": .array([
                                    .object([
                                        "id": .string("i3"),
                                        "name": .string("Grilled chicken breast"),
                                        "portions": .number(1.0)
                                    ]),
                                    .object([
                                        "id": .string("i4"),
                                        "name": .string("Brown rice"),
                                        "portions": .number(1.5)
                                    ])
                                ])
                            ])
                        ]),
                        "totals": .object([
                            "kcal": .number(2000),
                            "protein_g": .number(120),
                            "fat_g": .number(70),
                            "carbs_g": .number(210)
                        ])
                    ]),
                    .object([
                        "day_number": .number(2),
                        "meals": .array([
                            .object([
                                "meal_type": .string("breakfast"),
                                "title": .string("Breakfast"),
                                "kcal": .number(480),
                                "items": .array([
                                    .object([
                                        "id": .string("i5"),
                                        "name": .string("Greek yogurt with honey"),
                                        "portions": .number(1.0)
                                    ])
                                ])
                            ])
                        ]),
                        "totals": .object([
                            "kcal": .number(1950),
                            "protein_g": .number(115),
                            "fat_g": .number(65),
                            "carbs_g": .number(200)
                        ])
                    ])
                ]),
                "weekly_coverage": .object([
                    "Protein": .number(98.5),
                    "Iron": .number(95.1),
                    "Vitamin C": .number(120.2),
                    "Calcium": .number(88.4)
                ]),
                "shopping_list": .object([
                    "Oats": .number(0.5),
                    "Chicken breast": .number(1.2),
                    "Rice": .number(0.8),
                    "Greek yogurt": .number(0.3)
                ]),
                "total_cost": .number(150.0),
                "adherence_score": .number(0.95)
            ])
        )
    }

    private func mockEmptyResponse() -> WeeklyPlanDTO {
        WeeklyPlanDTO(
            root: .object([
                "daily_menus": .array([]),
                "weekly_coverage": .object([:]),
                "shopping_list": .null,
                "total_cost": .null,
                "adherence_score": .null
            ])
        )
    }
}

// MARK: - Mock Error

enum MockError: Error, LocalizedError {
    case serverError(String)

    var errorDescription: String? {
        switch self {
        case .serverError(let message):
            return message
        }
    }
}
