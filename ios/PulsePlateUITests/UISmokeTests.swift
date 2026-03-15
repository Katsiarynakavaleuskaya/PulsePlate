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
  static let foregroundTimeoutEnvironmentKey = "UI_FOREGROUND_TIMEOUT"
  static let defaultForegroundTimeout: TimeInterval = 10
}

final class UISmokeTests: XCTestCase {
  override func setUpWithError() throws {
    continueAfterFailure = false
  }

  @MainActor
  func testLaunch() throws {
    let app = XCUIApplication()
    let foregroundTimeout = TimeInterval(
      ProcessInfo.processInfo.environment[UISmokeLaunchContract.foregroundTimeoutEnvironmentKey] ?? ""
    ) ?? UISmokeLaunchContract.defaultForegroundTimeout

    app.launchArguments += [
      UISmokeLaunchContract.screenshotModeFlag,
      UISmokeLaunchContract.screenshotScenarioFlag,
      UISmokeLaunchContract.screenshotScenarioPaywall,
    ]
    app.launchEnvironment[UISmokeLaunchContract.screenshotModeEnvironmentKey] = "1"

    // RU: Это намеренно минимальный CI smoke. Он проверяет детерминированный запуск
    // preview-mode и базовое состояние foreground без дополнительных UI-assertion сценариев.
    // EN: This is intentionally a minimal CI smoke. It verifies deterministic preview-mode
    // launch and a basic foreground-running state without extra UI-flow assertions.
    app.launch()
    XCTAssertTrue(app.wait(for: .runningForeground, timeout: foregroundTimeout))
  }
}
