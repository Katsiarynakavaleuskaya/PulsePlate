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

    // RU: Для CI используем детерминированный App Store preview path, но критерий smoke остаётся
    // минимальным: приложение должно выйти в foreground без падения и без долгого boot timeout.
    // EN: In CI we use the deterministic App Store preview path, while keeping the smoke criterion
    // minimal: the app must reach foreground without crashing or hanging during boot.
    let timeoutSeconds = Int(
      ProcessInfo.processInfo.environment["UI_SMOKE_FOREGROUND_TIMEOUT_SECONDS"] ?? "60"
    ) ?? 60
    let didReachForeground = app.wait(for: .runningForeground, timeout: TimeInterval(timeoutSeconds))
    XCTAssertTrue(didReachForeground, "UI smoke: app did not reach runningForeground. state=\(app.state)")
  }
}
