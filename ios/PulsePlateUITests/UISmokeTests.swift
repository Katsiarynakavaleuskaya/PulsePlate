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
    app.launch()

    // RU: Smoke test проверяет только то, что приложение стартует в детерминированном preview-mode
    // и не завершается сразу. Мы сознательно не ждём UI idle, чтобы не зависеть от simulator quiescence.
    // EN: The smoke test only verifies that the app launches in deterministic preview mode
    // and does not terminate immediately. We intentionally avoid waiting for UI idleness.
    XCTAssertNotEqual(app.state, .notRunning, "UI smoke: app terminated immediately after launch")
  }
}
