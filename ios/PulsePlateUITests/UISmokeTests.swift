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
  static let screenshotScenarioPaywall = "paywall"
  static let screenshotModeEnvironmentKey = "APPSTORE_SCREENSHOT_MODE"
  static let postLaunchSettleSeconds: UInt32 = 1
}

final class UISmokeTests: XCTestCase {
  override func setUpWithError() throws {
    continueAfterFailure = false
  }

  @MainActor
  func testLaunch() throws {
    let app = XCUIApplication()

    app.launchArguments += [
      UISmokeLaunchContract.screenshotModeFlag,
      UISmokeLaunchContract.screenshotScenarioFlag,
      UISmokeLaunchContract.screenshotScenarioPaywall,
    ]
    app.launchEnvironment[UISmokeLaunchContract.screenshotModeEnvironmentKey] = "1"

    // RU: Это намеренно минимальный CI smoke. Он проверяет детерминированный запуск
    // screenshot-mode и что приложение не завершилось сразу после старта.
    // EN: This is intentionally a minimal CI smoke. It verifies deterministic screenshot-mode
    // launch and that the app stays alive immediately after startup.
    app.launch()
    sleep(UISmokeLaunchContract.postLaunchSettleSeconds)
    XCTAssertNotEqual(app.state, .notRunning)
  }
}
