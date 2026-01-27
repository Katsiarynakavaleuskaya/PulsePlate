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
    XCTAssertTrue(true)
  }
}
