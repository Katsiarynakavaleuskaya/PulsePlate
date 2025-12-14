import Testing
@testable import PulsePlate

struct WeeklyPlanAdapterSmokeTests {
    @Test func adapter_handlesNullJSON() {
        let dto = WeeklyPlanDTO(root: .null)
        let vm = WeeklyPlanAdapter.toVM(dto: dto)
        #expect(vm.isEmpty)
        #expect(vm.days.isEmpty)
    }

    @Test func adapter_handlesEmptyObject() {
        let dto = WeeklyPlanDTO(root: .object([:]))
        let vm = WeeklyPlanAdapter.toVM(dto: dto)
        #expect(vm.isEmpty)
        #expect(vm.days.isEmpty)
    }

    @Test func adapter_handlesMinimalDayWithoutCrashing() {
        // Minimal valid shape: one day with no meals
        let root: JSONValue = .object([
            "daily_menus": .array([
                .object([
                    "day": .number(1),
                    "meals": .array([])
                ])
            ])
        ])

        let dto = WeeklyPlanDTO(root: root)
        let vm = WeeklyPlanAdapter.toVM(dto: dto)

        #expect(vm.days.count == 1)
        #expect(vm.days[0].index == 0)
        #expect(vm.days[0].meals.isEmpty)
    }

    @Test func adapter_handlesMinimalMealWithoutCrashing() {
        // One meal with minimal fields
        let root: JSONValue = .object([
            "daily_menus": .array([
                .object([
                    "meals": .array([
                        .object([
                            "meal_type": .string("breakfast"),
                            "recipes": .array([])
                        ])
                    ])
                ])
            ])
        ])

        let dto = WeeklyPlanDTO(root: root)
        let vm = WeeklyPlanAdapter.toVM(dto: dto)

        #expect(vm.days.count == 1)
        #expect(vm.days[0].meals.count == 0) // Empty meal should be skipped (no kcal, no items)
    }

    @Test func adapter_handlesMissingFieldsGracefully() {
        // Missing optional fields should not crash
        let root: JSONValue = .object([
            "daily_menus": .array([
                .object([
                    "meals": .array([
                        .object([
                            "meal_type": .string("lunch"),
                            "kcal": .number(500), // Has kcal, so won't be skipped
                            "recipes": .array([])
                        ])
                    ])
                ])
            ])
        ])

        let dto = WeeklyPlanDTO(root: root)
        let vm = WeeklyPlanAdapter.toVM(dto: dto)

        #expect(vm.days.count == 1)
        #expect(vm.days[0].meals.count == 1)
        #expect(vm.days[0].meals[0].mealType == .lunch)
        #expect(vm.days[0].meals[0].kcal == 500)
    }

    @Test func adapter_clampsWeeklyCoveragePercentages() {
        // Verify clamping prevents UI breaks on bad data
        let root: JSONValue = .object([
            "daily_menus": .array([]),
            "weekly_coverage": .object([
                "protein": .number(-50),  // Should clamp to 0
                "iron": .number(500)      // Should clamp to 300
            ])
        ])

        let dto = WeeklyPlanDTO(root: root)
        let vm = WeeklyPlanAdapter.toVM(dto: dto)

        let protein = vm.weeklyCoverage.first { $0.label == "Protein" }
        let iron = vm.weeklyCoverage.first { $0.label == "Iron" }

        #expect(protein?.percent == 0)
        #expect(iron?.percent == 300)
    }
}
