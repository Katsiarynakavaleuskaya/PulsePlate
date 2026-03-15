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
  static let paywallRootIdentifier = "appstore.paywall.screen"
  static let rootAppearanceTimeout: TimeInterval = 20
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
    // preview-mode и появление корневого paywall preview без полного runtime boot path.
    // EN: This is intentionally a minimal CI smoke. It verifies deterministic preview-mode
    // launch and the appearance of the paywall preview root without full runtime boot assertions.
    app.launch()
    let root = app.descendants(matching: .any)
      .matching(identifier: UISmokeLaunchContract.paywallRootIdentifier)
      .firstMatch
    XCTAssertTrue(root.waitForExistence(timeout: UISmokeLaunchContract.rootAppearanceTimeout))
  }
}
