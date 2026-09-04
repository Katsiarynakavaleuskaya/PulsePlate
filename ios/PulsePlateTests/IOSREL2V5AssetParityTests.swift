import CryptoKit
import Foundation
import ImageIO
import UIKit
import XCTest

@testable import PulsePlate

final class IOSREL2V5AssetParityTests: XCTestCase {
    func testDerivedFilesMatchTheApprovedV5Inventory() throws {
        let root = try repositoryRoot()
        let assetDirectory = root.appendingPathComponent("ios/PulsePlate/Resources/Images")

        for asset in Self.assets {
            let url = assetDirectory.appendingPathComponent(asset.filename)
            let data = try Data(contentsOf: url)

            XCTAssertLessThanOrEqual(
                data.count,
                512_000,
                "V5 runtime asset exceeds the frozen 500 KiB ceiling: \(asset.filename)"
            )
            XCTAssertEqual(sha256(data), asset.outputSHA256, asset.filename)

            let source = try XCTUnwrap(CGImageSourceCreateWithURL(url as CFURL, nil))
            let properties = try XCTUnwrap(
                CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
            )
            XCTAssertEqual(properties[kCGImagePropertyPixelWidth] as? Int, asset.width)
            XCTAssertEqual(properties[kCGImagePropertyPixelHeight] as? Int, asset.height)

            let image = try XCTUnwrap(UIImage(contentsOfFile: url.path))
            let cgImage = try XCTUnwrap(image.cgImage)
            XCTAssertFalse(hasAlpha(cgImage.alphaInfo), asset.filename)
            XCTAssertEqual(cgImage.colorSpace?.name, CGColorSpace.sRGB, asset.filename)
        }
    }

    func testEveryV5AssetResolvesAndDecodesFromTheAppBundle() throws {
        for asset in Self.assets {
            let url = try XCTUnwrap(
                Bundle.main.url(
                    forResource: asset.resourceName,
                    withExtension: asset.fileExtension
                ),
                "Missing V5 app-bundle resource: \(asset.filename)"
            )
            let source = try XCTUnwrap(CGImageSourceCreateWithURL(url as CFURL, nil))
            let properties = try XCTUnwrap(
                CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
            )
            XCTAssertEqual(properties[kCGImagePropertyPixelWidth] as? Int, asset.width)
            XCTAssertEqual(properties[kCGImagePropertyPixelHeight] as? Int, asset.height)

            let image = try XCTUnwrap(
                UIImage(named: asset.filename, in: .main, compatibleWith: nil),
                "UIImage could not decode bundled V5 resource: \(asset.filename)"
            )
            let cgImage = try XCTUnwrap(image.cgImage)
            XCTAssertFalse(hasAlpha(cgImage.alphaInfo), asset.filename)
            XCTAssertEqual(cgImage.colorSpace?.name, CGColorSpace.sRGB, asset.filename)
        }
    }

    func testV5SourceAndOutputHashesAreBoundIntoTheCanonicalAssetRecord() throws {
        let canon = try String(
            contentsOf: repositoryRoot()
                .appendingPathComponent("docs/design/FITCHEF_MASCOT_ASSET_CANON.md"),
            encoding: .utf8
        )

        for asset in Self.assets {
            XCTAssertTrue(canon.contains(asset.sourceSHA256), asset.filename)
            XCTAssertTrue(canon.contains(asset.outputSHA256), asset.filename)
            XCTAssertTrue(canon.contains(asset.filename), asset.filename)
        }
        XCTAssertTrue(canon.contains("APPROVE_A"))
        XCTAssertTrue(canon.contains("PENDING NATIVE V1"))
    }

    func testEachApprovedAssetHasOneBoundedViewOwnerAndNeverBecomesATabIcon() throws {
        let root = try repositoryRoot()
        let rootTabs = try source(
            root: root,
            relativePath: "ios/PulsePlate/Views/RootTabs.swift"
        )

        for asset in Self.assets {
            let viewSource = try source(root: root, relativePath: asset.ownerViewPath)
            XCTAssertEqual(
                occurrenceCount(of: "\"\(asset.filename)\"", in: viewSource),
                1,
                "Expected one SwiftUI owner reference for \(asset.filename)"
            )
            XCTAssertFalse(rootTabs.contains(asset.filename), asset.filename)
        }

        let plate = try source(root: root, relativePath: "ios/PulsePlate/Views/PlateView.swift")
        XCTAssertFalse(plate.contains("MascotBubble(textKey: \"mascot.plate.hint\")"))
        XCTAssertFalse(rootTabs.contains("FITCHEF_ACTION_COOKING"))
    }

    func testProfileCopyIsConsumerFacingInEverySupportedLocale() throws {
        let root = try repositoryRoot()

        for (locale, expectedCopy) in Self.profileCopyByLocale {
            let values = try localizationValues(root: root, locale: locale)

            XCTAssertEqual(values["pro.profile.header"], expectedCopy.header)
            XCTAssertEqual(values["pro.profile.footer"], expectedCopy.footer)

            let visibleCopy = [
                values["pro.profile.header"] ?? "",
                values["pro.profile.footer"] ?? "",
            ].joined(separator: " ").lowercased()
            for forbiddenToken in ["/api/", "(pro)", "request", "solicitar", "используется"] {
                XCTAssertFalse(
                    visibleCopy.contains(forbiddenToken),
                    "Profile exposes technical or paid vocabulary for \(locale): \(forbiddenToken)"
                )
            }
        }
    }

    func testPlatePreviewCopyMatchesTheApprovedV5Direction() throws {
        let root = try repositoryRoot()

        for (locale, expectedCopy) in Self.plateCopyByLocale {
            let values = try localizationValues(root: root, locale: locale)
            XCTAssertEqual(values["plate.preview.title"], expectedCopy.title)
            XCTAssertEqual(values["plate.preview.subtitle"], expectedCopy.subtitle)

            let subtitle = (values["plate.preview.subtitle"] ?? "").lowercased()
            for rejectedClaim in [
                "customize",
                "настроить",
                "ajustar",
                "a calm view",
                "спокойный обзор",
                "una vista tranquila",
            ] {
                XCTAssertFalse(
                    subtitle.contains(rejectedClaim),
                    "Plate copy promises unsupported customization for \(locale)"
                )
            }
        }
    }

    func testProgressCopyUsesConsumerNutrientLanguageWithoutInventingMicronutrients() throws {
        let root = try repositoryRoot()

        for (locale, expectedCopy) in Self.progressCopyByLocale {
            let values = try localizationValues(root: root, locale: locale)
            XCTAssertEqual(values["progress.summary.subtitle"], expectedCopy.subtitle)
            XCTAssertEqual(values["progress.nutrient_progress.title"], expectedCopy.chartTitle)
            XCTAssertEqual(
                values["progress.chart.nutrient_category"],
                expectedCopy.axisCategory
            )
            XCTAssertEqual(values["progress.chart.completion"], expectedCopy.axisCompletion)

            let visibleCopy = [
                expectedCopy.subtitle,
                expectedCopy.chartTitle,
                expectedCopy.axisCategory,
                expectedCopy.axisCompletion,
            ]
                .joined(separator: " ")
                .lowercased()
            for rejectedTerm in [
                "segment",
                "сегмент",
                "micronutrient",
                "микронутри",
                "micronutriente",
            ] {
                XCTAssertFalse(
                    visibleCopy.contains(rejectedTerm),
                    "Progress copy exposes internal or unsupported nutrient terms for \(locale)"
                )
            }
        }

        let source = try source(root: root, relativePath: "ios/PulsePlate/Views/ProgressView.swift")
        XCTAssertFalse(source.contains("Segment progress"))
        XCTAssertFalse(source.contains("segment balance"))
        XCTAssertFalse(source.contains(".value(\"Segment\""))
        XCTAssertFalse(source.contains(".value(\"Completion\""))
        XCTAssertTrue(source.contains("progress.chart.nutrient_category"))
        XCTAssertTrue(source.contains("progress.chart.completion"))
    }

    private func source(root: URL, relativePath: String) throws -> String {
        try String(
            contentsOf: root.appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    private func localizationValues(root: URL, locale: String) throws -> [String: String] {
        let url = root
            .appendingPathComponent("ios/PulsePlate")
            .appendingPathComponent("\(locale).lproj")
            .appendingPathComponent("Localizable.strings")
        let data = try Data(contentsOf: url)
        var format = PropertyListSerialization.PropertyListFormat.openStep
        let propertyList = try PropertyListSerialization.propertyList(
            from: data,
            options: [],
            format: &format
        )
        return try XCTUnwrap(propertyList as? [String: String])
    }

    private func sha256(_ data: Data) -> String {
        SHA256.hash(data: data)
            .map { String(format: "%02x", $0) }
            .joined()
    }

    private func hasAlpha(_ alphaInfo: CGImageAlphaInfo) -> Bool {
        switch alphaInfo {
        case .first, .last, .premultipliedFirst, .premultipliedLast, .alphaOnly:
            return true
        case .none, .noneSkipFirst, .noneSkipLast:
            return false
        @unknown default:
            return true
        }
    }

    private func occurrenceCount(of value: String, in source: String) -> Int {
        source.components(separatedBy: value).count - 1
    }

    private func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        while candidate.path != "/" {
            if FileManager.default.fileExists(
                atPath: candidate.appendingPathComponent(".git").path
            ) {
                return candidate
            }
            candidate = candidate.deletingLastPathComponent()
        }
        throw IOSREL2V5AssetParityTestError.repositoryRootNotFound
    }

    // These are public asset-integrity checksums, never credentials or tokens.
    private static let assets: [V5AssetExpectation] = [
        V5AssetExpectation(
            filename: "fitchef-onboarding-welcome-v1.png",
            sourceSHA256: "7e37a0a90772a5423f546948e94d36a876a30877ed8c80b336b2f291dd07eb98", // pragma: allowlist secret
            outputSHA256: "279081197210c7dc66c16234ce0eec6cf7f490a134176af894ab56f0cca67de5", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-action-progress-tracking-v1.png",
            sourceSHA256: "38b9604a3a27f229535c948e0e5e8e22fe2ae185e0b585c965b040b330d4d65f", // pragma: allowlist secret
            outputSHA256: "8d26d8d8464fdaa764abe439694ecf9fd06c9f937d82a4a8d57f3ecaa02cf46a", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/ProgressView.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-action-nutrition-plate-v1.png",
            sourceSHA256: "e73bcbf5fd3f2f9af60e89e93db79570e1be89fac7213bdb39b131adc881955b", // pragma: allowlist secret
            outputSHA256: "da89403f0fec0a3c183cdd7218a1f37996365c6f6c35104ff1a528eb7bceab80", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/PlateView.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-onboarding-profile-setup-v1.png",
            sourceSHA256: "3ae7e0265de31221e6b105b7e0592f1a2b510eebde3e876432cedd33dd853b81", // pragma: allowlist secret
            outputSHA256: "b0e8f856e65c7c78d7f5ae000d30e3c56397d2bcf10ef6b3fda0e692f0d5fbd0", // pragma: allowlist secret
            width: 432,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/ProfileView.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-happy-v1.png",
            sourceSHA256: "3f5cd3a5084f1b8f8e1cdec2e3ca2e492fd14cb03f97e45d0c2e6401c8033697", // pragma: allowlist secret
            outputSHA256: "a84aa312d47edf06316f0d47e60fefb99d12a4c5d6fad18595978a3eabf4c445", // pragma: allowlist secret
            width: 576,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-encouraging-v1.png",
            sourceSHA256: "e61dfecab8d092374d61ddfd535fec76d2d74652a2f3dac6194df44ae47ac9fb", // pragma: allowlist secret
            outputSHA256: "1399e0735f523bd401f6bb96ecd3edf07c377abe3318c1aa06938b58b542c35c", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-thinking-v1.png",
            sourceSHA256: "41f557ccf00663035551e9c0f5c535cd772c47e7c5efb1c81297435d076ff98e", // pragma: allowlist secret
            outputSHA256: "66d8d84e6b309beaba6fdac6c4b008a366c0aef9659c337ae3fabc80e0b1e33c", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Screens/BMICalculatorScreen.swift"
        ),
        V5AssetExpectation(
            filename: "photo-daily-plate-salmon-v1.jpg",
            sourceSHA256: "5bb635cdf4a86359d2763235dd31e7ef8f7d5b8c5776826823c5ff0a63806331", // pragma: allowlist secret
            outputSHA256: "666651b6caf3b2c4b3e3e6eda1243caf773ad97bdb2cb8a3de49251bdf4314e2", // pragma: allowlist secret
            width: 768,
            height: 768,
            ownerViewPath: "ios/PulsePlate/Views/PlateView.swift"
        ),
        V5AssetExpectation(
            filename: "photo-activity-endurance-v1.jpg",
            sourceSHA256: "687a5a49c8fe321990f036cb6efdd1889bd08c5ff38983cf6eda94a3546bcda2", // pragma: allowlist secret
            outputSHA256: "5108de91fce089419785fbb62c3318bb943ce3319b1f4bfd130baf3a99344cc9", // pragma: allowlist secret
            width: 640,
            height: 800,
            ownerViewPath: "ios/PulsePlate/Views/ProgressView.swift"
        ),
        V5AssetExpectation(
            filename: "photo-activity-movement-everyday-fitness-v1.jpg",
            sourceSHA256: "d0b9be1359c0f56c6fd6dfffe849c4f6de2c699c8acfe8fb204f2a890e2ec1d5", // pragma: allowlist secret
            outputSHA256: "27b1c0beabdd428cb3651906ea45064c007562ba8d92f0b973d499a585183a25", // pragma: allowlist secret
            width: 640,
            height: 800,
            ownerViewPath: "ios/PulsePlate/Screens/BMICalculatorScreen.swift"
        ),
    ]

    private static let profileCopyByLocale: [String: (header: String, footer: String)] = [
        "en": (
            header: "Nutrition Profile",
            footer: "These details personalize your daily nutrition view."
        ),
        "ru": (
            header: "Профиль питания",
            footer: "Эти данные помогают персонализировать ваш план питания на день."
        ),
        "es": (
            header: "Perfil nutricional",
            footer: "Estos datos personalizan tu vista diaria de nutrición."
        ),
    ]

    private static let plateCopyByLocale: [String: (title: String, subtitle: String)] = [
        "en": (
            title: "Today's plate",
            subtitle: "Visualize your plate. Log a meal. Explore the breakdown."
        ),
        "ru": (
            title: "Сегодняшняя тарелка",
            subtitle: "Визуализируйте свою тарелку. Добавьте приём пищи. Посмотрите состав."
        ),
        "es": (
            title: "Plato de hoy",
            subtitle: "Visualiza tu plato. Registra una comida. Consulta la composición."
        ),
    ]

    private static let progressCopyByLocale: [
        String: (
            subtitle: String,
            chartTitle: String,
            axisCategory: String,
            axisCompletion: String
        )
    ] = [
        "en": (
            subtitle: "Track daily nutrition completion and nutrient balance.",
            chartTitle: "Nutrient progress",
            axisCategory: "Nutrient category",
            axisCompletion: "Completion"
        ),
        "ru": (
            subtitle: "Отслеживайте дневное питание и баланс питательных веществ.",
            chartTitle: "Прогресс по питательным веществам",
            axisCategory: "Категория питательных веществ",
            axisCompletion: "Выполнение"
        ),
        "es": (
            subtitle: "Sigue tu alimentación diaria y el equilibrio de nutrientes.",
            chartTitle: "Progreso de nutrientes",
            axisCategory: "Categoría de nutrientes",
            axisCompletion: "Progreso"
        ),
    ]
}

private struct V5AssetExpectation {
    let filename: String
    let sourceSHA256: String
    let outputSHA256: String
    let width: Int
    let height: Int
    let ownerViewPath: String

    var resourceName: String {
        URL(fileURLWithPath: filename).deletingPathExtension().lastPathComponent
    }

    var fileExtension: String {
        URL(fileURLWithPath: filename).pathExtension
    }
}

private enum IOSREL2V5AssetParityTestError: Error {
    case repositoryRootNotFound
}
