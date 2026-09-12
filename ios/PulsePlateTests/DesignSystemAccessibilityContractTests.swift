import Foundation
import SwiftUI
import UIKit
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
    func testPrimaryButtonRasterMeetsAAAcrossAppearanceTypeAndLoading() throws {
        for scheme in [ColorScheme.light, .dark] {
            let foreground = try primaryButtonRGB(named: GeneratedDesignTokens.BrandAsset.navy, scheme: scheme)
            let fill = try primaryButtonRGB(named: GeneratedDesignTokens.BrandAsset.blue, scheme: scheme)
            XCTAssertGreaterThanOrEqual(buttonContrast(foreground, fill), 4.5)

            for loading in [false, true] {
                var largeHeight: CGFloat = 0
                for typeSize in [DynamicTypeSize.large, .accessibility5] {
                    let image = try primaryButtonImage(
                        title: "Confirm direction",
                        scheme: scheme,
                        typeSize: typeSize,
                        loading: loading
                    )
                    let name = "\(scheme)/\(typeSize)/loading=\(loading)"
                    XCTContext.runActivity(named: name) { activity in
                        let attachment = XCTAttachment(image: image)
                        attachment.lifetime = .keepAlways
                        activity.add(attachment)
                    }
                    assertRenderedButtonBounds(
                        image.size, size: .md, proposedWidth: 220, caseName: name
                    )
                    XCTAssertGreaterThan(
                        try buttonPixelCount(image, matching: fill), 100, "Missing fill: \(name)"
                    )
                    XCTAssertGreaterThan(
                        try buttonPixelCount(image, matching: foreground), 10,
                        "Missing accessible foreground: \(name)"
                    )
                    if typeSize == .large {
                        largeHeight = image.size.height
                    } else {
                        XCTAssertGreaterThan(image.size.height, largeHeight, name)
                    }
                }
            }
        }
    }

    @MainActor
    func testPrimaryLoadingSpinnerHasAccessibleNativeForeground() async throws {
        for scheme in [ColorScheme.light, .dark] {
            let foreground = try primaryButtonRGB(named: GeneratedDesignTokens.BrandAsset.navy, scheme: scheme)
            let fill = try primaryButtonRGB(named: GeneratedDesignTokens.BrandAsset.blue, scheme: scheme)
            let actual = try await hostedLoadingSpinnerRGB(scheme: scheme)
            for channel in 0..<3 {
                XCTAssertEqual(actual[channel], foreground[channel], accuracy: 1.0 / 255,
                               "Native spinner must receive Navy in \(scheme)")
            }
            XCTAssertGreaterThanOrEqual(buttonContrast(actual, fill), 4.5,
                                        "Native spinner color must meet AA in \(scheme)")
        }
    }

    @MainActor
    private func primaryButtonImage(
        title: String, scheme: ColorScheme, typeSize: DynamicTypeSize, loading: Bool
    ) throws -> UIImage {
        let renderer = ImageRenderer(content:
            PPButton(title, variant: .primary, fullWidth: true, isLoading: loading, action: {})
                .environment(\.colorScheme, scheme)
                .dynamicTypeSize(typeSize)
        )
        renderer.scale = 3
        renderer.proposedSize = ProposedViewSize(width: 220, height: nil)
        return try XCTUnwrap(renderer.uiImage)
    }

    @MainActor
    private func hostedLoadingSpinnerRGB(scheme: ColorScheme) async throws -> [Double] {
        let scene = try XCTUnwrap(
            UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
        )
        let previousKeyWindow = scene.windows.first(where: \.isKeyWindow)
        let controller = UIHostingController(rootView:
            PPButton("", variant: .primary, fullWidth: true, isLoading: true, action: {})
                .environment(\.colorScheme, scheme)
                .dynamicTypeSize(.large)
                .ignoresSafeArea()
        )
        let window = UIWindow(windowScene: scene)
        window.frame = CGRect(x: 0, y: 0, width: 220, height: 100)
        window.overrideUserInterfaceStyle = scheme == .dark ? .dark : .light
        window.rootViewController = controller
        window.makeKeyAndVisible()
        defer {
            window.isHidden = true
            window.rootViewController = nil
            previousKeyWindow?.makeKey()
        }
        await Task.yield()
        let hostedView = try XCTUnwrap(controller.view)
        hostedView.layoutIfNeeded()
        var remaining = [hostedView]
        var indicators: [UIActivityIndicatorView] = []
        while let view = remaining.popLast() {
            if let indicator = view as? UIActivityIndicatorView {
                indicators.append(indicator)
            }
            remaining.append(contentsOf: view.subviews)
        }
        XCTAssertEqual(indicators.count, 1, "The actual loading PPButton must host one native spinner")
        let indicator = try XCTUnwrap(indicators.first)
        XCTAssertTrue(indicator.isAnimating)
        let color = try XCTUnwrap(indicator.color, "The configured spinner tint must be explicit")
        let traits = UITraitCollection(userInterfaceStyle: scheme == .dark ? .dark : .light)
        return buttonRGB(color.resolvedColor(with: traits))
    }

    @MainActor
    private func primaryButtonRGB(named assetName: String, scheme: ColorScheme) throws -> [Double] {
        let traits = UITraitCollection(userInterfaceStyle: scheme == .dark ? .dark : .light)
        let resolved = try XCTUnwrap(UIColor(named: assetName, in: .main, compatibleWith: traits))
            .resolvedColor(with: traits)
        return buttonRGB(resolved)
    }

    @MainActor
    private func buttonRGB(_ resolved: UIColor) -> [Double] {
        var red: CGFloat = 0
        var green: CGFloat = 0
        var blue: CGFloat = 0
        var alpha: CGFloat = 0
        XCTAssertTrue(resolved.getRed(&red, green: &green, blue: &blue, alpha: &alpha))
        XCTAssertEqual(alpha, 1, accuracy: 0.001)
        return [Double(red), Double(green), Double(blue)]
    }

    private func buttonContrast(_ first: [Double], _ second: [Double]) -> Double {
        func luminance(_ rgb: [Double]) -> Double {
            let linear = rgb.map { $0 <= 0.04045 ? $0 / 12.92 : pow(($0 + 0.055) / 1.055, 2.4) }
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
        }
        let values = [luminance(first), luminance(second)].sorted()
        return (values[1] + 0.05) / (values[0] + 0.05)
    }

    private func buttonPixelCount(_ image: UIImage, matching rgb: [Double]) throws -> Int {
        let cgImage = try XCTUnwrap(image.cgImage)
        let width = cgImage.width
        let height = cgImage.height
        var pixels = [UInt8](repeating: 0, count: width * height * 4)
        let space = try XCTUnwrap(CGColorSpace(name: CGColorSpace.sRGB))
        try pixels.withUnsafeMutableBytes { bytes in
            let context = try XCTUnwrap(CGContext(
                data: bytes.baseAddress, width: width, height: height,
                bitsPerComponent: 8, bytesPerRow: width * 4, space: space,
                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
                    | CGBitmapInfo.byteOrder32Big.rawValue
            ))
            context.draw(cgImage, in: CGRect(x: 0, y: 0, width: width, height: height))
        }
        let expected = rgb.map { Int(($0 * 255).rounded()) }
        var count = 0
        for y in 0..<height {
            for x in 0..<width {
                let offset = (y * width + x) * 4
                if pixels[offset + 3] >= 250 && (0..<3).allSatisfy({
                    abs(Int(pixels[offset + $0]) - expected[$0]) <= 3
                }) {
                    count += 1
                }
            }
        }
        return count
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
