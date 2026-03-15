//
//  UISmokeTests.swift
//  PulsePlateUITests
//
//  Minimal UI smoke test for CI trust.
//  Минимальный UI smoke тест для доверия к CI.
//

import XCTest

final class UISmokeTests: XCTestCase {
  override func setUpWithError() throws {
    continueAfterFailure = false
  }

  @MainActor
  func testLaunch() throws {
    let app = XCUIApplication()
    setupSnapshot(app, waitForAnimations: false)
    app.launchArguments += [
      "-appstore-screenshot-mode",
      "-appstore-screenshot-scenario", "welcome",
    ]
    app.launchEnvironment["APPSTORE_SCREENSHOT_MODE"] = "1"

    // RU: Это намеренно минимальный CI smoke. Он проверяет, что UI test runner способен
    // поднять приложение в детерминированном preview-mode без дополнительных idle/assertion wait'ов.
    // EN: This is intentionally a minimal CI smoke. It verifies that the UI test runner can
    // launch the app in deterministic preview mode without extra idle/assertion waits.
    app.launch()
  }
}
