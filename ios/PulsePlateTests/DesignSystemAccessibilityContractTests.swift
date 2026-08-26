import Foundation
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

    @MainActor
    func testPPButtonRenderedMatrixScalesAtAccessibilityFiveWithoutBreakingBounds() throws {
        let compactWidth: CGFloat = 220

        for sizeCase in buttonSizes {
            for variantCase in buttonVariants {
                let shortControl = try renderedButtonSize(
                    title: "OK",
                    localeIdentifier: "en",
                    variant: variantCase.value,
                    size: sizeCase.value,
                    isLoading: false,
                    dynamicTypeSize: .accessibility5,
                    proposedWidth: compactWidth
                )
                assertRenderedButtonBounds(
                    shortControl,
                    size: sizeCase.value,
                    proposedWidth: compactWidth,
                    caseName: "\(sizeCase.name)/\(variantCase.name)/short-control"
                )

                for label in longLabels {
                    let caseName =
                        "\(sizeCase.name)/\(variantCase.name)/\(label.locale)"
                    let large = try renderedButtonSize(
                        title: label.title,
                        localeIdentifier: label.locale,
                        variant: variantCase.value,
                        size: sizeCase.value,
                        isLoading: false,
                        dynamicTypeSize: .large,
                        proposedWidth: compactWidth
                    )
                    let accessibility = try renderedButtonSize(
                        title: label.title,
                        localeIdentifier: label.locale,
                        variant: variantCase.value,
                        size: sizeCase.value,
                        isLoading: false,
                        dynamicTypeSize: .accessibility5,
                        proposedWidth: compactWidth
                    )

                    assertRenderedButtonBounds(
                        large,
                        size: sizeCase.value,
                        proposedWidth: compactWidth,
                        caseName: "\(caseName)/large"
                    )
                    assertRenderedButtonBounds(
                        accessibility,
                        size: sizeCase.value,
                        proposedWidth: compactWidth,
                        caseName: "\(caseName)/accessibility5"
                    )
                    XCTAssertGreaterThan(
                        accessibility.height,
                        large.height,
                        "Expected Dynamic Type height growth for \(caseName)"
                    )
                    XCTAssertGreaterThan(
                        accessibility.height,
                        shortControl.height,
                        "Expected multiline long-label growth for \(caseName)"
                    )
                }
            }
        }
    }

    @MainActor
    func testPPButtonLoadingRenderPreservesAccessibleBoundsAcrossFiniteMatrix() throws {
        let compactWidth: CGFloat = 220

        for sizeCase in buttonSizes {
            for variantCase in buttonVariants {
                for label in longLabels {
                    let caseName =
                        "\(sizeCase.name)/\(variantCase.name)/\(label.locale)"
                    let idle = try renderedButtonSize(
                        title: label.title,
                        localeIdentifier: label.locale,
                        variant: variantCase.value,
                        size: sizeCase.value,
                        isLoading: false,
                        dynamicTypeSize: .accessibility5,
                        proposedWidth: compactWidth
                    )
                    let loading = try renderedButtonSize(
                        title: label.title,
                        localeIdentifier: label.locale,
                        variant: variantCase.value,
                        size: sizeCase.value,
                        isLoading: true,
                        dynamicTypeSize: .accessibility5,
                        proposedWidth: compactWidth
                    )

                    assertRenderedButtonBounds(
                        idle,
                        size: sizeCase.value,
                        proposedWidth: compactWidth,
                        caseName: "\(caseName)/idle"
                    )
                    assertRenderedButtonBounds(
                        loading,
                        size: sizeCase.value,
                        proposedWidth: compactWidth,
                        caseName: "\(caseName)/loading"
                    )
                    XCTAssertGreaterThanOrEqual(
                        loading.height,
                        idle.height,
                        "Loading state must not reduce accessible height for \(caseName)"
                    )
                }
            }
        }
    }

    func testPPButtonScaledTitleKeepsDefaultsAndLegacySizeFontSurfaceExplicit() throws {
        let defaultButton = PPButton("Continue", action: {})
        if case .primary = defaultButton.variant {} else {
            XCTFail("PPButton default variant must remain primary")
        }
        if case .md = defaultButton.size {} else {
            XCTFail("PPButton default size must remain md")
        }
        XCTAssertFalse(defaultButton.fullWidth)
        XCTAssertFalse(defaultButton.isLoading)

        _ = PPButtonSize.sm.font
        _ = PPButtonSize.md.font
        _ = PPButtonSize.lg.font
        XCTAssertEqual(
            PPDesignTokens.Typography.sizeBase,
            GeneratedDesignTokens.Typography.sizeBase
        )

        let buttonSource = try designSystemSource(named: "PPButton.swift")
        let tokenSource = try designSystemSource(named: "DesignTokens.swift")
        let buttonStart = try XCTUnwrap(buttonSource.range(of: "struct PPButton: View"))
        let styleStart = try XCTUnwrap(buttonSource.range(of: "struct PPButtonStyle: ButtonStyle"))
        let buttonBody = String(buttonSource[buttonStart.lowerBound..<styleStart.lowerBound])

        XCTAssertTrue(buttonSource.contains("case .sm: return PPDesignTokens.Typography.body"))
        XCTAssertTrue(buttonSource.contains("case .md: return PPDesignTokens.Typography.body"))
        XCTAssertTrue(
            buttonSource.contains("case .lg: return PPDesignTokens.Typography.bodyStrong")
        )
        XCTAssertTrue(
            tokenSource.contains(
                "static let body = Font.system(size: sizeBase, weight: .regular)"
            )
        )
        XCTAssertTrue(
            tokenSource.contains(
                "static let bodyStrong = Font.system(size: sizeBase, weight: .semibold)"
            )
        )
        XCTAssertTrue(buttonBody.contains("@ScaledMetric(relativeTo: .body)"))
        XCTAssertTrue(
            buttonBody.contains(
                "private var scaledTitleFontSize =\n        PPDesignTokens.Typography.sizeBase"
            )
        )
        XCTAssertTrue(buttonBody.contains(".font(.system(size: scaledTitleFontSize))"))
        XCTAssertTrue(buttonBody.contains(".fontWeight(.semibold)"))
        XCTAssertFalse(buttonBody.contains(".font(size.font)"))
    }

    @MainActor
    private func renderedButtonSize(
        title: String,
        localeIdentifier: String,
        variant: PPButtonVariant,
        size: PPButtonSize,
        isLoading: Bool,
        dynamicTypeSize: DynamicTypeSize,
        proposedWidth: CGFloat
    ) throws -> CGSize {
        let content = PPButton(
            title,
            variant: variant,
            size: size,
            fullWidth: true,
            isLoading: isLoading,
            action: {}
        )
        .environment(\.locale, Locale(identifier: localeIdentifier))
        .dynamicTypeSize(dynamicTypeSize)

        let renderer = ImageRenderer(content: content)
        renderer.scale = 1
        renderer.proposedSize = ProposedViewSize(width: proposedWidth, height: nil)

        return try XCTUnwrap(
            renderer.uiImage,
            "ImageRenderer must produce an image for \(localeIdentifier)"
        ).size
    }

    private func assertRenderedButtonBounds(
        _ renderedSize: CGSize,
        size: PPButtonSize,
        proposedWidth: CGFloat,
        caseName: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertGreaterThan(renderedSize.width, 0, caseName, file: file, line: line)
        XCTAssertLessThanOrEqual(
            renderedSize.width,
            proposedWidth + 0.5,
            caseName,
            file: file,
            line: line
        )
        XCTAssertGreaterThanOrEqual(
            renderedSize.height,
            size.minHeight,
            caseName,
            file: file,
            line: line
        )
    }

    private var buttonSizes: [(name: String, value: PPButtonSize)] {
        [
            ("sm", .sm),
            ("md", .md),
            ("lg", .lg),
        ]
    }

    private var buttonVariants: [(name: String, value: PPButtonVariant)] {
        [
            ("primary", .primary),
            ("secondary", .secondary),
            ("ghost", .ghost),
        ]
    }

    private var longLabels: [(locale: String, title: String)] {
        [
            ("en", "Confirm direction"),
            ("ru", "Подтвердить направление"),
            ("es", "Confirmar orientación"),
        ]
    }

    private func designSystemSource(named fileName: String) throws -> String {
        let iosRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let sourceURL = iosRoot
            .appendingPathComponent("PulsePlate")
            .appendingPathComponent("DesignSystem")
            .appendingPathComponent(fileName)
        return try String(contentsOf: sourceURL, encoding: .utf8)
    }
}
