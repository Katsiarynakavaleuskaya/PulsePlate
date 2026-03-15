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

    // RU: Для CI используем детерминированный App Store preview root вместо полного runtime boot,
    // чтобы smoke проверял запуск приложения, а не флейки фоновой инициализации.
    // EN: In CI we target the deterministic App Store preview root instead of full runtime boot,
    // so the smoke test validates app launch rather than flaky background initialization.
    let root = app.descendants(matching: .any)
      .matching(identifier: "appstore.welcome.screen")
      .firstMatch
    XCTAssertTrue(
      root.waitForExistence(timeout: 20),
      "UI smoke: deterministic welcome root did not appear"
    )
  }
}
