import SwiftUI
import XCTest
@testable import PulsePlate

final class DesignSystemAccessibilityContractTests: XCTestCase {
    func testMinimumTouchTargetNeverFallsBelowGeneratedToken() {
        XCTAssertEqual(PPAccessibility.minimumTouchTarget, PPDesignTokens.Spacing.touchTarget)
        XCTAssertEqual(
            PPAccessibility.minimumTouchTarget(for: 32),
            PPDesignTokens.Spacing.touchTarget
        )
        XCTAssertEqual(PPAccessibility.minimumTouchTarget(for: 56), 56)
    }

    func testPressScaleRespectsReduceMotion() {
        XCTAssertEqual(PPAccessibility.pressScale(isPressed: true, reduceMotion: true), 1.0)
        XCTAssertEqual(PPAccessibility.pressScale(isPressed: false, reduceMotion: true), 1.0)
        XCTAssertEqual(PPAccessibility.pressScale(isPressed: true, reduceMotion: false), 0.95)
        XCTAssertEqual(PPAccessibility.pressScale(isPressed: false, reduceMotion: false), 1.0)
    }

    func testAnimationIsDisabledWhenReduceMotionIsEnabled() {
        XCTAssertNil(PPAccessibility.animation(.easeInOut(duration: 0.2), reduceMotion: true))
        XCTAssertNotNil(PPAccessibility.animation(.easeInOut(duration: 0.2), reduceMotion: false))
    }

    func testCompactButtonKeepsFortyFourPointMinimumTarget() {
        XCTAssertEqual(PPButtonSize.sm.minHeight, PPDesignTokens.Spacing.touchTarget)
        XCTAssertEqual(PPButtonSize.md.minHeight, PPDesignTokens.Spacing.touchTarget)
        XCTAssertEqual(PPButtonSize.lg.minHeight, 48)
    }

    func testShapeStyleThemeUsesDesignTokenFacade() {
        XCTAssertEqual(Color.surface, PPDesignTokens.ColorToken.surface)
        XCTAssertEqual(
            Color.surfaceElevated,
            PPDesignTokens.ColorToken.surfaceElevated
        )
        XCTAssertEqual(
            Color.liquidGlass,
            PPDesignTokens.ColorToken.liquidGlass
        )
    }
}
