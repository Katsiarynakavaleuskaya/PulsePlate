import XCTest

final class AppStoreScreenshotTests: XCTestCase {
    private enum Scenario: String, CaseIterable {
        case coreValue = "core_value"
        case nutritionAnalysis = "nutrition_analysis"
        case mealPlanner = "meal_planner"
        case groceryList = "grocery_list"
        case healthProgress = "health_progress"
        case personalization = "personalization"
        case aiAssistant = "ai_assistant"

        var screenshotName: String {
            switch self {
            case .coreValue:
                return "01_core-value"
            case .nutritionAnalysis:
                return "02_nutrition-analysis"
            case .mealPlanner:
                return "03_meal-planner"
            case .groceryList:
                return "04_grocery-list"
            case .healthProgress:
                return "05_health-progress"
            case .personalization:
                return "06_personalization"
            case .aiAssistant:
                return "07_ai-assistant"
            }
        }

        var accessibilityIdentifier: String {
            switch self {
            case .coreValue:
                return "appstore.core_value.screen"
            case .nutritionAnalysis:
                return "appstore.nutrition_analysis.screen"
            case .mealPlanner:
                return "appstore.meal_planner.screen"
            case .groceryList:
                return "appstore.grocery_list.screen"
            case .healthProgress:
                return "appstore.health_progress.screen"
            case .personalization:
                return "appstore.personalization.screen"
            case .aiAssistant:
                return "appstore.ai_assistant.screen"
            }
        }
    }

    override func setUpWithError() throws {
        continueAfterFailure = false
    }

    @MainActor
    func testCoreValueScreenshot() {
        captureScreenshot(for: .coreValue)
    }

    @MainActor
    func testNutritionAnalysisScreenshot() {
        captureScreenshot(for: .nutritionAnalysis)
    }

    @MainActor
    func testMealPlannerScreenshot() {
        captureScreenshot(for: .mealPlanner)
    }

    @MainActor
    func testGroceryListScreenshot() {
        captureScreenshot(for: .groceryList)
    }

    @MainActor
    func testHealthProgressScreenshot() {
        captureScreenshot(for: .healthProgress)
    }

    @MainActor
    func testPersonalizationScreenshot() {
        captureScreenshot(for: .personalization)
    }

    @MainActor
    func testAiAssistantScreenshot() {
        captureScreenshot(for: .aiAssistant)
    }

    @MainActor
    private func captureScreenshot(for scenario: Scenario) {
        let app = XCUIApplication()
        setupSnapshot(app, waitForAnimations: false)
        app.launchArguments += [
            "-appstore-screenshot-mode",
            "-appstore-screenshot-scenario", scenario.rawValue
        ]
        app.launchEnvironment["APPSTORE_SCREENSHOT_MODE"] = "1"
        app.launch()

        let root = app.descendants(matching: .any)
            .matching(identifier: scenario.accessibilityIdentifier)
            .firstMatch
        XCTAssertTrue(
            root.waitForExistence(timeout: 20),
            "App Store screenshot root did not appear for \(scenario.rawValue)"
        )

        snapshot(scenario.screenshotName, timeWaitingForIdle: 0.3)
        app.terminate()
    }
}
