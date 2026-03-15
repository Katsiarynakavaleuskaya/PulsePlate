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
    app.launchArguments += [
      "-appstore-screenshot-mode",
      "-appstore-screenshot-scenario", "paywall",
    ]
    app.launchEnvironment["APPSTORE_SCREENSHOT_MODE"] = "1"

    // RU: Это намеренно минимальный CI smoke. Он проверяет детерминированный запуск
    // preview-mode и базовое состояние foreground без дополнительных UI-assertion сценариев.
    // EN: This is intentionally a minimal CI smoke. It verifies deterministic preview-mode
    // launch and a basic foreground-running state without extra UI-flow assertions.
    app.launch()
    XCTAssertTrue(app.wait(for: .runningForeground, timeout: 10))
  }
}
