//
//  UISmokeTests.swift
//  PulsePlateUITests
//
//  Minimal UI smoke test for CI trust.
//  Минимальный UI smoke тест для доверия к CI.
//

import XCTest

final class UISmokeTests: XCTestCase {
  @MainActor
  func testLaunch() throws {
    let app = XCUIApplication()
    app.launch()
    // RU: На CI иногда бывают флейки симулятора/launch. Мы не ассертим "сразу",
    // а ждём, пока приложение перейдёт в foreground.
    // EN: CI simulator/app launch can be flaky. Wait for the app to reach foreground.
    let didReachForeground = app.wait(for: .runningForeground, timeout: 60)
    XCTAssertTrue(didReachForeground, "UI smoke: app did not reach runningForeground. state=\(app.state)")
  }
}
