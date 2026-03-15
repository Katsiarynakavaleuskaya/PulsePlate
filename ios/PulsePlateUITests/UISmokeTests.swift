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

    // RU: Минимальный CI smoke — один статичный assertion: app достиг foreground.
    // EN: Minimal CI smoke — single static assertion: app reached foreground.
    // Element-based checks (Window/NavigationBar/etc) flaky on CI; runningForeground is more reliable.
    app.launch()
    defer { app.terminate() }

    let timeoutSeconds = Double(
      ProcessInfo.processInfo.environment["UI_SMOKE_FOREGROUND_TIMEOUT_SECONDS"] ?? "90"
    ) ?? 90
    let didReachForeground = app.wait(for: .runningForeground, timeout: timeoutSeconds)
    XCTAssertTrue(
      didReachForeground,
      "UI smoke: app did not reach runningForeground. state=\(app.state)"
    )
  }
}
