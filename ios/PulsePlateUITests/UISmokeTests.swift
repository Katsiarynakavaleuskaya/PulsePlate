//
//  UISmokeTests.swift
//  PulsePlateUITests
//
//  Minimal UI smoke test for CI trust.
//  Минимальный UI smoke тест для доверия к CI.
//

import XCTest

private enum UISmokeLaunchContract {
  static let screenshotModeFlag = "-appstore-screenshot-mode"
  static let screenshotScenarioFlag = "-appstore-screenshot-scenario"
  static let screenshotScenarioHealthPermission = "health_permission"
  static let screenshotModeEnvironmentKey = "APPSTORE_SCREENSHOT_MODE"
  static let primaryLaunchTimeout: TimeInterval = 20
  static let fallbackLaunchTimeout: TimeInterval = 3
}

final class UISmokeTests: XCTestCase {
  override func setUpWithError() throws {
    continueAfterFailure = false
  }

  @MainActor
  func testLaunch() throws {
    let app = XCUIApplication()
    setupSnapshot(app, waitForAnimations: false)

    app.launchArguments += [
      UISmokeLaunchContract.screenshotModeFlag,
      UISmokeLaunchContract.screenshotScenarioFlag,
      UISmokeLaunchContract.screenshotScenarioHealthPermission,
    ]
    app.launchEnvironment[UISmokeLaunchContract.screenshotModeEnvironmentKey] = "1"

    // RU: Это намеренно минимальный CI smoke. Он проверяет детерминированный запуск
    // screenshot-mode на статичном preview scenario по generic UI-container signal без привязки к preview-root.
    // EN: This is intentionally a minimal CI smoke. It verifies deterministic screenshot-mode
    // launch through a stable screenshot scenario and a generic UI-container signal.
    app.launch()
    defer { app.terminate() }

    let launchSanitySatisfied =
      app.windows.firstMatch.waitForExistence(timeout: UISmokeLaunchContract.primaryLaunchTimeout)
      || app.navigationBars.firstMatch.waitForExistence(timeout: UISmokeLaunchContract.fallbackLaunchTimeout)
      || app.tables.firstMatch.waitForExistence(timeout: UISmokeLaunchContract.fallbackLaunchTimeout)
      || app.collectionViews.firstMatch.waitForExistence(timeout: UISmokeLaunchContract.fallbackLaunchTimeout)
      || app.scrollViews.firstMatch.waitForExistence(timeout: UISmokeLaunchContract.fallbackLaunchTimeout)

    XCTAssertTrue(
      launchSanitySatisfied,
      "Screenshot-mode launch did not present any stable UI container"
    )
  }
}
