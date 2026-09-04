import Compression
import CryptoKit
import Foundation
import ImageIO
import UIKit
import XCTest

@testable import PulsePlate

final class IOSREL2V5AssetParityTests: XCTestCase {
    @MainActor
    func testHomeHeroPreservesCompactPortraitSizeOutsideAccessibility() {
        let cases: [(regular: Bool, accessibility: Bool, expected: CGSize)] = [
            (false, false, CGSize(width: 112, height: 148)),
            (false, true, CGSize(width: 148, height: 148)),
            (true, false, CGSize(width: 220, height: 220)),
            (true, true, CGSize(width: 148, height: 148)),
        ]
        for testCase in cases {
            XCTAssertEqual(
                HomeHeroLayout.size(
                    isRegular: testCase.regular,
                    isAccessibility: testCase.accessibility
                ),
                testCase.expected
            )
        }
    }

    func testDerivedFilesMatchTheApprovedV5Inventory() throws {
        let root = try repositoryRoot()
        for asset in Self.assets.flatMap(\.files) {
            let url = root.appendingPathComponent(asset.runtimeCandidatePath)
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
            assertRGBImageIOProperties(properties, filename: asset.filename)

            let image = try XCTUnwrap(UIImage(contentsOfFile: url.path))
            let cgImage = try XCTUnwrap(image.cgImage)
            XCTAssertFalse(hasAlpha(cgImage.alphaInfo), asset.filename)
        }
    }

    func testDerivedFilesMatchTheFrozenMetadataAndEncodingContract() throws {
        let root = try repositoryRoot()
        for asset in Self.assets.flatMap(\.files) {
            let url = root.appendingPathComponent(asset.runtimeCandidatePath)
            let data = try Data(contentsOf: url)
            let source = try XCTUnwrap(CGImageSourceCreateWithURL(url as CFURL, nil))
            let properties = try XCTUnwrap(
                CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
            )

            for forbiddenKey in Self.forbiddenImageIOPropertyKeys {
                XCTAssertNil(
                    properties[forbiddenKey],
                    "Forbidden metadata \(forbiddenKey) in \(asset.filename)"
                )
            }

            let embeddedICCProfile: Data
            switch asset.fileExtension {
            case "png":
                embeddedICCProfile = try assertFrozenPNGContract(
                    data,
                    properties: properties,
                    filename: asset.filename
                )
            case "jpg":
                embeddedICCProfile = try assertFrozenJPEGContract(
                    data,
                    properties: properties,
                    filename: asset.filename
                )
            default:
                XCTFail("Unsupported V5 asset format: \(asset.filename)")
                continue
            }

            XCTAssertEqual(embeddedICCProfile.count, Self.sRGBICCProfileByteCount)
            XCTAssertEqual(
                sha256(embeddedICCProfile),
                Self.sRGBICCProfileSHA256,
                asset.filename
            )
        }
    }

    @MainActor
    func testEveryV5AssetResolvesAndDecodesFromTheAppBundle() throws {
        // Xcode thins the installed catalog to the destination's display scale.
        // Repository tests cover all three source renditions; this proves the
        // rendition actually installed on the current iPhone/iPad destination.
        let scale = UIScreen.main.scale
        for asset in Self.assets {
            if let catalog = asset.catalog {
                for style in [UIUserInterfaceStyle.light, .dark] {
                    let traits = UITraitCollection(traitsFrom: [
                        UITraitCollection(displayScale: CGFloat(scale)),
                        UITraitCollection(userInterfaceStyle: style),
                    ])
                    let image = try XCTUnwrap(
                        UIImage(named: catalog.key, in: .main, compatibleWith: traits),
                        "Missing V5 catalog key: \(catalog.key)"
                    )
                    let cgImage = try XCTUnwrap(image.cgImage)
                    XCTAssertEqual(image.scale, CGFloat(scale), catalog.key)
                    XCTAssertEqual(image.size.width, CGFloat(asset.width) / 3, accuracy: 0.01)
                    XCTAssertEqual(image.size.height, CGFloat(asset.height) / 3, accuracy: 0.01)
                    XCTAssertEqual(cgImage.width, asset.width / 3 * Int(scale), catalog.key)
                    XCTAssertEqual(cgImage.height, asset.height / 3 * Int(scale), catalog.key)
                    XCTAssertEqual(cgImage.colorSpace?.model, .rgb, catalog.key)
                    XCTAssertFalse(hasAlpha(cgImage.alphaInfo), catalog.key)
                }
                continue
            }
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
            assertRGBImageIOProperties(properties, filename: asset.filename)

            let image = try XCTUnwrap(
                UIImage(named: asset.filename, in: .main, compatibleWith: nil),
                "UIImage could not decode bundled V5 resource: \(asset.filename)"
            )
            let cgImage = try XCTUnwrap(image.cgImage)
            XCTAssertFalse(hasAlpha(cgImage.alphaInfo), asset.filename)
        }
    }

    func testPromotedCatalogsHaveExactlyTheApprovedDensityFiles() throws {
        let root = try repositoryRoot()
        let expectedKeys: Set<String> = [
            "FitChefThinking", "FitChefOnboardingWelcome",
            "FitChefActionNutritionPlate", "FitChefActionProgressTracking",
            "FitChefOnboardingProfileSetup", "FitChefPortraitHappy",
            "FitChefPortraitEncouraging",
        ]
        let catalogs = Self.assets.compactMap(\.catalog)
        XCTAssertEqual(catalogs.count, 7)
        XCTAssertEqual(Set(catalogs.map(\.key)), expectedKeys)
        XCTAssertEqual(Self.assets.flatMap(\.files).count, 24)

        for asset in Self.assets {
            guard let catalog = asset.catalog else { continue }
            XCTAssertEqual(catalog.lowerDensitySHA256s.count, 2, catalog.key)
            let directory = root.appendingPathComponent(catalog.directory)
            let metadata = try Data(contentsOf: directory.appendingPathComponent("Contents.json"))
            let actual = try XCTUnwrap(JSONSerialization.jsonObject(with: metadata) as? NSDictionary)
            let expected: NSDictionary = [
                "images": (1...3).map { scale in
                    [
                        "filename": "\(catalog.stem)@\(scale)x.png",
                        "idiom": "universal",
                        "scale": "\(scale)x",
                    ]
                },
                "info": ["author": "xcode", "version": 1],
            ]
            // Array equality rejects repeated slots; dictionary equality rejects
            // extra decoded properties/appearance variants without a custom parser.
            XCTAssertEqual(actual, expected, catalog.key)
            XCTAssertEqual(
                Set(try FileManager.default.contentsOfDirectory(atPath: directory.path)),
                Set(asset.files.map(\.filename) + ["Contents.json"]),
                "Missing or unreferenced catalog file: \(catalog.key)"
            )
            XCTAssertFalse(FileManager.default.fileExists(
                atPath: root.appendingPathComponent(
                    "ios/PulsePlate/Resources/Images/\(asset.filename)"
                ).path
            ), "Loose duplicate mascot: \(asset.filename)")
        }
    }

    func testV5RuntimeOutputHashesAreBoundIntoTheCanonicalAssetRecord() throws {
        let canon = try String(
            contentsOf: repositoryRoot()
                .appendingPathComponent("docs/design/FITCHEF_MASCOT_ASSET_CANON.md"),
            encoding: .utf8
        )

        for asset in Self.assets.flatMap(\.files) {
            let columns = try canonicalAssetRecordColumns(
                for: asset.runtimeCandidatePath,
                in: canon
            )
            guard columns.count == 6 else {
                XCTFail("Expected six canonical columns for \(asset.filename)")
                continue
            }
            XCTAssertEqual(columns[2], "`\(asset.runtimeCandidatePath)`", asset.filename)
            XCTAssertEqual(columns[3], "`\(asset.outputSHA256)`", asset.filename)
        }
        XCTAssertTrue(canon.contains("APPROVE_A"))
        XCTAssertTrue(canon.contains("PENDING NATIVE V1"))
    }

    func testEachApprovedAssetHasOneBoundedViewOwnerAndNeverBecomesATabIcon() throws {
        let root = try repositoryRoot()
        let swiftSourceFiles = try appSwiftSourceFiles(root: root)
        let rootTabs = try source(
            root: root,
            relativePath: "ios/PulsePlate/Views/RootTabs.swift"
        )

        for asset in Self.assets {
            var referencesByPath: [String: Int] = [:]
            for sourceFile in swiftSourceFiles {
                let relativePath = try repositoryRelativePath(sourceFile, root: root)
                let contents = try String(contentsOf: sourceFile, encoding: .utf8)
                let referenceCount = occurrenceCount(
                    of: "\"\(asset.runtimeName)\"",
                    in: contents
                )
                if referenceCount > 0 {
                    referencesByPath[relativePath] = referenceCount
                }
            }

            XCTAssertEqual(
                referencesByPath.values.reduce(0, +),
                1,
                "Expected exactly one app-source reference for \(asset.filename)"
            )
            XCTAssertEqual(
                Set(referencesByPath.keys),
                Set([asset.ownerViewPath]),
                "Unexpected SwiftUI owner for \(asset.filename)"
            )
            XCTAssertFalse(rootTabs.contains(asset.runtimeName), asset.runtimeName)
            if asset.catalog != nil {
                for sourceFile in swiftSourceFiles {
                    let contents = try String(contentsOf: sourceFile, encoding: .utf8)
                    XCTAssertFalse(contents.contains(asset.filename), asset.filename)
                    XCTAssertFalse(
                        contents.contains("Image(\"\(asset.runtimeName)\")"),
                        "Catalog owner bypasses required-image loading: \(asset.runtimeName)"
                    )
                }
            }
        }

        let plate = try source(root: root, relativePath: "ios/PulsePlate/Views/PlateView.swift")
        let home = try source(root: root, relativePath: "ios/PulsePlate/Views/Home/HomeExperience.swift")
        XCTAssertTrue(home.contains("Image(ppRequiredBundleAsset: assetName)"))
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

    func testPlateCanvasAndProgressRingHaveBoundedPresentationContracts() throws {
        let root = try repositoryRoot()
        let plate = try source(root: root, relativePath: "ios/PulsePlate/Views/PlateView.swift")
        XCTAssertTrue(plate.contains(
            ".frame(width: PlateVisualLayout.segmentCanvasSide, height: PlateVisualLayout.segmentCanvasSide)"
        ))
        XCTAssertTrue(plate.contains("static let segmentCanvasSide: CGFloat = 280"))
        XCTAssertTrue(plate.contains(
            ".environment(\\.locale, Locale(identifier: localization.currentLanguage))"
        ))
        for (locale, expected) in [
            "en": ("of daily goal", "Daily nutrition progress"),
            "ru": ("дневной цели", "Прогресс питания за день"),
            "es": ("del objetivo diario", "Progreso de alimentación diario"),
        ] {
            let values = try localizationValues(root: root, locale: locale)
            XCTAssertEqual(values["progress.complete"], expected.0)
            XCTAssertEqual(values["progress.label"], expected.1)
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

    private func assertFrozenPNGContract(
        _ data: Data,
        properties: [CFString: Any],
        filename: String
    ) throws -> Data {
        let chunks = try pngChunks(in: data, filename: filename)
        let chunkTypes = chunks.map(\.type)

        XCTAssertEqual(chunkTypes.first, "IHDR", filename)
        XCTAssertEqual(chunkTypes.last, "IEND", filename)
        XCTAssertEqual(chunkTypes.filter { $0 == "IHDR" }.count, 1, filename)
        XCTAssertEqual(chunkTypes.filter { $0 == "iCCP" }.count, 1, filename)
        XCTAssertEqual(chunkTypes.filter { $0 == "IEND" }.count, 1, filename)
        XCTAssertGreaterThanOrEqual(chunkTypes.filter { $0 == "IDAT" }.count, 1, filename)
        XCTAssertTrue(
            chunkTypes.dropFirst(2).dropLast().allSatisfy { $0 == "IDAT" },
            "PNG contains a non-approved metadata or payload chunk: \(filename)"
        )

        let pngProperties = try XCTUnwrap(
            properties[kCGImagePropertyPNGDictionary] as? NSDictionary,
            "Missing PNG properties: \(filename)"
        )
        XCTAssertEqual(pngProperties.count, 1, filename)
        XCTAssertEqual(
            pngProperties[kCGImagePropertyPNGInterlaceType] as? Int,
            0,
            filename
        )

        let profileChunk = try XCTUnwrap(
            chunks.first { $0.type == "iCCP" },
            "Missing iCCP chunk: \(filename)"
        )
        let nullIndex = try XCTUnwrap(
            profileChunk.payload.firstIndex(of: 0),
            "Malformed iCCP profile name: \(filename)"
        )
        let profileName = String(
            data: profileChunk.payload.prefix(upTo: nullIndex),
            encoding: .isoLatin1
        )
        XCTAssertEqual(profileName, "ICC Profile", filename)

        let compressionMethodIndex = profileChunk.payload.index(after: nullIndex)
        guard compressionMethodIndex < profileChunk.payload.endIndex else {
            throw V5AssetEncodingError.invalidPNG(filename)
        }
        XCTAssertEqual(profileChunk.payload[compressionMethodIndex], 0, filename)
        let compressedProfileStart = profileChunk.payload.index(after: compressionMethodIndex)
        let compressedProfile = Data(profileChunk.payload[compressedProfileStart...])
        return try zlibDecompressedICCProfile(compressedProfile, filename: filename)
    }

    private func assertRGBImageIOProperties(
        _ properties: [CFString: Any],
        filename: String
    ) {
        XCTAssertEqual(properties[kCGImagePropertyColorModel] as? String, "RGB", filename)
        XCTAssertEqual(properties[kCGImagePropertyDepth] as? Int, 8, filename)
    }

    private func assertFrozenJPEGContract(
        _ data: Data,
        properties: [CFString: Any],
        filename: String
    ) throws -> Data {
        let markers = try jpegMarkersBeforeScan(in: data, filename: filename)
        XCTAssertEqual(markers.map(\.code), Self.expectedJPEGMarkerCodes, filename)
        XCTAssertEqual(Data(data.suffix(2)), Data([0xFF, 0xD9]), filename)

        let jfifMarker = try XCTUnwrap(
            markers.first { $0.code == 0xE0 },
            "Missing JFIF marker: \(filename)"
        )
        guard jfifMarker.payload.count >= 14 else {
            throw V5AssetEncodingError.invalidJPEG(filename)
        }
        XCTAssertEqual(Data(jfifMarker.payload.prefix(5)), Data("JFIF\0".utf8), filename)
        XCTAssertEqual(jfifMarker.payload[5], 1, filename)
        XCTAssertEqual(jfifMarker.payload[6], 1, filename)
        XCTAssertEqual(jfifMarker.payload[7], 0, filename)
        XCTAssertEqual(try bigEndianUInt16(jfifMarker.payload, at: 8), 1, filename)
        XCTAssertEqual(try bigEndianUInt16(jfifMarker.payload, at: 10), 1, filename)

        let jfifProperties = try XCTUnwrap(
            properties[kCGImagePropertyJFIFDictionary] as? NSDictionary,
            "Missing JFIF properties: \(filename)"
        )
        XCTAssertEqual(jfifProperties.count, 4, filename)
        XCTAssertEqual(jfifProperties[kCGImagePropertyJFIFDensityUnit] as? Int, 0, filename)
        XCTAssertEqual(jfifProperties[kCGImagePropertyJFIFXDensity] as? Int, 1, filename)
        XCTAssertEqual(jfifProperties[kCGImagePropertyJFIFYDensity] as? Int, 1, filename)

        let iccMarkers = markers.filter { $0.code == 0xE2 }
        XCTAssertEqual(iccMarkers.count, 1, filename)
        let iccMarker = try XCTUnwrap(iccMarkers.first)
        guard iccMarker.payload.count >= 14 else {
            throw V5AssetEncodingError.invalidICC(filename)
        }
        XCTAssertEqual(
            Data(iccMarker.payload.prefix(12)),
            Data("ICC_PROFILE\0".utf8),
            filename
        )
        XCTAssertEqual(iccMarker.payload[12], 1, filename)
        XCTAssertEqual(iccMarker.payload[13], 1, filename)
        return iccMarker.payload.subdata(in: 14 ..< iccMarker.payload.count)
    }

    private func pngChunks(in data: Data, filename: String) throws -> [PNGChunk] {
        let signature = Data([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        guard data.count >= signature.count, data.prefix(signature.count) == signature else {
            throw V5AssetEncodingError.invalidPNG(filename)
        }

        var offset = signature.count
        var chunks: [PNGChunk] = []
        while offset < data.count {
            guard offset <= data.count - 12 else {
                throw V5AssetEncodingError.invalidPNG(filename)
            }
            let payloadLength = try bigEndianUInt32(data, at: offset)
            let typeStart = offset + 4
            let payloadStart = offset + 8
            guard payloadLength <= data.count - payloadStart - 4 else {
                throw V5AssetEncodingError.invalidPNG(filename)
            }
            let payloadEnd = payloadStart + payloadLength
            let typeData = data.subdata(in: typeStart ..< payloadStart)
            guard let type = String(data: typeData, encoding: .ascii) else {
                throw V5AssetEncodingError.invalidPNG(filename)
            }
            chunks.append(
                PNGChunk(
                    type: type,
                    payload: data.subdata(in: payloadStart ..< payloadEnd)
                )
            )
            offset = payloadEnd + 4
            if type == "IEND" {
                break
            }
        }

        guard offset == data.count else {
            throw V5AssetEncodingError.invalidPNG(filename)
        }
        return chunks
    }

    private func jpegMarkersBeforeScan(
        in data: Data,
        filename: String
    ) throws -> [JPEGMarker] {
        guard data.count >= 4, data[0] == 0xFF, data[1] == 0xD8 else {
            throw V5AssetEncodingError.invalidJPEG(filename)
        }

        var offset = 2
        var markers: [JPEGMarker] = []
        while offset < data.count {
            guard data[offset] == 0xFF else {
                throw V5AssetEncodingError.invalidJPEG(filename)
            }
            while offset < data.count, data[offset] == 0xFF {
                offset += 1
            }
            guard offset < data.count else {
                throw V5AssetEncodingError.invalidJPEG(filename)
            }

            let code = data[offset]
            offset += 1
            guard code != 0x00, code != 0xD8, code != 0xD9, !(0xD0 ... 0xD7).contains(code) else {
                throw V5AssetEncodingError.invalidJPEG(filename)
            }

            let markerLength = try bigEndianUInt16(data, at: offset)
            guard markerLength >= 2, markerLength <= data.count - offset else {
                throw V5AssetEncodingError.invalidJPEG(filename)
            }
            let payloadStart = offset + 2
            let payloadEnd = offset + markerLength
            markers.append(
                JPEGMarker(
                    code: code,
                    payload: data.subdata(in: payloadStart ..< payloadEnd)
                )
            )
            offset = payloadEnd
            if code == 0xDA {
                break
            }
        }
        return markers
    }

    private func zlibDecompressedICCProfile(
        _ compressedData: Data,
        filename: String
    ) throws -> Data {
        guard compressedData.count > 6 else {
            throw V5AssetEncodingError.invalidICC(filename)
        }
        let compressionMethodAndFlags =
            (Int(compressedData[0]) << 8) | Int(compressedData[1])
        guard
            compressedData[0] & 0x0F == 8,
            compressionMethodAndFlags.isMultiple(of: 31),
            compressedData[1] & 0x20 == 0
        else {
            throw V5AssetEncodingError.invalidICC(filename)
        }

        let deflateData = compressedData.subdata(in: 2 ..< compressedData.count - 4)
        var output = [UInt8](repeating: 0, count: Self.sRGBICCProfileByteCount + 1)
        let decodedByteCount = output.withUnsafeMutableBytes { outputBuffer in
            deflateData.withUnsafeBytes { inputBuffer in
                guard
                    let outputAddress = outputBuffer.bindMemory(to: UInt8.self).baseAddress,
                    let inputAddress = inputBuffer.bindMemory(to: UInt8.self).baseAddress
                else {
                    return 0
                }
                return compression_decode_buffer(
                    outputAddress,
                    outputBuffer.count,
                    inputAddress,
                    inputBuffer.count,
                    nil,
                    COMPRESSION_ZLIB
                )
            }
        }
        guard decodedByteCount == Self.sRGBICCProfileByteCount else {
            throw V5AssetEncodingError.invalidICC(filename)
        }
        let profile = Data(output.prefix(decodedByteCount))
        let expectedAdler32 = try bigEndianUInt32(
            compressedData,
            at: compressedData.count - 4
        )
        guard adler32(profile) == expectedAdler32 else {
            throw V5AssetEncodingError.invalidICC(filename)
        }
        return profile
    }

    private func adler32(_ data: Data) -> Int {
        let modulus = 65_521
        var a = 1
        var b = 0
        for byte in data {
            a = (a + Int(byte)) % modulus
            b = (b + a) % modulus
        }
        return (b << 16) | a
    }

    private func bigEndianUInt16(_ data: Data, at offset: Int) throws -> Int {
        guard offset >= 0, offset <= data.count - 2 else {
            throw V5AssetEncodingError.truncatedInteger
        }
        return (Int(data[offset]) << 8) | Int(data[offset + 1])
    }

    private func bigEndianUInt32(_ data: Data, at offset: Int) throws -> Int {
        guard offset >= 0, offset <= data.count - 4 else {
            throw V5AssetEncodingError.truncatedInteger
        }
        return (Int(data[offset]) << 24)
            | (Int(data[offset + 1]) << 16)
            | (Int(data[offset + 2]) << 8)
            | Int(data[offset + 3])
    }

    private func canonicalAssetRecordColumns(
        for runtimePath: String,
        in canon: String
    ) throws -> [String] {
        let runtimeCandidate = "`\(runtimePath)`"
        let rows = canon
            .split(whereSeparator: \.isNewline)
            .map(String.init)
            .filter { row in
                row.hasPrefix("|") && row.contains(runtimeCandidate)
            }
        XCTAssertEqual(rows.count, 1, "Expected one canonical row for \(runtimePath)")
        let row = try XCTUnwrap(rows.first)
        return row
            .split(separator: "|", omittingEmptySubsequences: true)
            .map { $0.trimmingCharacters(in: .whitespaces) }
    }

    private func appSwiftSourceFiles(root: URL) throws -> [URL] {
        let appDirectory = root.appendingPathComponent("ios/PulsePlate")
        let keys: Set<URLResourceKey> = [.isRegularFileKey, .isSymbolicLinkKey]
        let enumerator = try XCTUnwrap(
            FileManager.default.enumerator(
                at: appDirectory,
                includingPropertiesForKeys: Array(keys),
                options: [.skipsHiddenFiles, .skipsPackageDescendants]
            )
        )
        var sourceFiles: [URL] = []
        for case let fileURL as URL in enumerator where fileURL.pathExtension == "swift" {
            let values = try fileURL.resourceValues(forKeys: keys)
            if values.isRegularFile == true, values.isSymbolicLink != true {
                sourceFiles.append(fileURL)
            }
        }
        return sourceFiles.sorted { $0.path < $1.path }
    }

    private func repositoryRelativePath(_ fileURL: URL, root: URL) throws -> String {
        let rootPath = root.standardizedFileURL.path + "/"
        let filePath = fileURL.standardizedFileURL.path
        guard filePath.hasPrefix(rootPath) else {
            throw V5AssetEncodingError.outsideRepository(filePath)
        }
        return String(filePath.dropFirst(rootPath.count))
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

    private static let sRGBICCProfileByteCount = 588
    private static let sRGBICCProfileSHA256 = "86453c6e1ee138f0be42c75ab37a6d73422df68e4767da1b1d3ae6c05aa20e39" // pragma: allowlist secret
    private static let expectedJPEGMarkerCodes: [UInt8] = [
        0xE0, 0xE2, 0xDB, 0xDB, 0xC0, 0xC4, 0xC4, 0xC4, 0xC4, 0xDA,
    ]
    private static let forbiddenImageIOPropertyKeys: [CFString] = [
        kCGImagePropertyDPIWidth,
        kCGImagePropertyDPIHeight,
        kCGImagePropertyExifDictionary,
        kCGImagePropertyGPSDictionary,
        kCGImagePropertyIPTCDictionary,
        kCGImagePropertyTIFFDictionary,
    ]

    // These are public runtime-output checksums, never credentials or tokens.
    private static let assets: [V5AssetExpectation] = [
        V5AssetExpectation(
            filename: "fitchef-onboarding-welcome-v1.png",
            outputSHA256: "279081197210c7dc66c16234ce0eec6cf7f490a134176af894ab56f0cca67de5", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift",
            catalog: V5CatalogExpectation(
                key: "FitChefOnboardingWelcome",
                stem: "fitchef-onboarding-welcome",
                lowerDensitySHA256s: [
                    "205cb0d86cbb5b2b2592a5997ea97b832267da637657cd51146f9e171f378813", // pragma: allowlist secret
                    "0cab5104573f747d30aa4e6442662fe5cb08d49df0550fc7f3cacbe8add3bae3", // pragma: allowlist secret
                ]
            )
        ),
        V5AssetExpectation(
            filename: "fitchef-action-progress-tracking-v1.png",
            outputSHA256: "8d26d8d8464fdaa764abe439694ecf9fd06c9f937d82a4a8d57f3ecaa02cf46a", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/ProgressView.swift",
            catalog: V5CatalogExpectation(
                key: "FitChefActionProgressTracking",
                stem: "FitChefActionProgressTracking",
                lowerDensitySHA256s: [
                    "32f1a4f09ed3f29d4b113dc11df586c3ee981c41ba43729f34b45057af5cf2f2", // pragma: allowlist secret
                    "26eb6b2be8023042fecf0b9c0c8ef2f2a594ac8867bb7e624fbb0397c3a08b1f", // pragma: allowlist secret
                ]
            )
        ),
        V5AssetExpectation(
            filename: "fitchef-action-nutrition-plate-v1.png",
            outputSHA256: "da89403f0fec0a3c183cdd7218a1f37996365c6f6c35104ff1a528eb7bceab80", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/PlateView.swift",
            catalog: V5CatalogExpectation(
                key: "FitChefActionNutritionPlate",
                stem: "FitChefActionNutritionPlate",
                lowerDensitySHA256s: [
                    "c3b40ff2117153a9edfd67d017c6e3cb9713fbe3e750cd38c1bedb79f146b5e6", // pragma: allowlist secret
                    "7dd2b312029b4abf87376774903fab95e3da7d839e640148ecc073edbe2b6fee", // pragma: allowlist secret
                ]
            )
        ),
        V5AssetExpectation(
            filename: "fitchef-onboarding-profile-setup-v1.png",
            outputSHA256: "b0e8f856e65c7c78d7f5ae000d30e3c56397d2bcf10ef6b3fda0e692f0d5fbd0", // pragma: allowlist secret
            width: 432,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/ProfileView.swift",
            catalog: V5CatalogExpectation(
                key: "FitChefOnboardingProfileSetup",
                stem: "FitChefOnboardingProfileSetup",
                lowerDensitySHA256s: [
                    "50bbe535174288033c40ccc40d6afc682ade57516df4ed861576830ea5e52810", // pragma: allowlist secret
                    "a7a0f18d110a69e519cf406b91c73ca034ac78741d0cf0aec71b1e21bb0d4278", // pragma: allowlist secret
                ]
            )
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-happy-v1.png",
            outputSHA256: "a84aa312d47edf06316f0d47e60fefb99d12a4c5d6fad18595978a3eabf4c445", // pragma: allowlist secret
            width: 576,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift",
            catalog: V5CatalogExpectation(
                key: "FitChefPortraitHappy",
                stem: "FitChefPortraitHappy",
                lowerDensitySHA256s: [
                    "3c319735caeb647c8cb9ae705f13f7d9fd3804afbcd4065f9a9ce4deef6efe05", // pragma: allowlist secret
                    "e205fef40ce4a9842ae8556dcb7b1a559a299f938917592e676fefbe6bae4eac", // pragma: allowlist secret
                ]
            )
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-encouraging-v1.png",
            outputSHA256: "1399e0735f523bd401f6bb96ecd3edf07c377abe3318c1aa06938b58b542c35c", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift",
            catalog: V5CatalogExpectation(
                key: "FitChefPortraitEncouraging",
                stem: "FitChefPortraitEncouraging",
                lowerDensitySHA256s: [
                    "ab8d924717dce3e23edd87083c81e50c1d21f57fd4330b7130a875e08b6a157d", // pragma: allowlist secret
                    "94da68ed2a9ddd9d30affe276b55c57d6ef82a42bacf944a36067a6f81e734b9", // pragma: allowlist secret
                ]
            )
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-thinking-v1.png",
            outputSHA256: "66d8d84e6b309beaba6fdac6c4b008a366c0aef9659c337ae3fabc80e0b1e33c", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Screens/BMICalculatorScreen.swift",
            catalog: V5CatalogExpectation(
                key: "FitChefThinking",
                stem: "fitchef-thinking",
                lowerDensitySHA256s: [
                    "76356ff16aa6f897ef90bfd5c1454eb1dd2df6d29647edc4bd3c597857bafad8", // pragma: allowlist secret
                    "2481c99f7a2e2258bba95742b39aaddf22d9dcf6f8b5c0cb39cbf57d40e856a1", // pragma: allowlist secret
                ]
            )
        ),
        V5AssetExpectation(
            filename: "photo-daily-plate-salmon-v1.jpg",
            outputSHA256: "666651b6caf3b2c4b3e3e6eda1243caf773ad97bdb2cb8a3de49251bdf4314e2", // pragma: allowlist secret
            width: 768,
            height: 768,
            ownerViewPath: "ios/PulsePlate/Views/PlateView.swift"
        ),
        V5AssetExpectation(
            filename: "photo-activity-endurance-v1.jpg",
            outputSHA256: "5108de91fce089419785fbb62c3318bb943ce3319b1f4bfd130baf3a99344cc9", // pragma: allowlist secret
            width: 640,
            height: 800,
            ownerViewPath: "ios/PulsePlate/Views/ProgressView.swift"
        ),
        V5AssetExpectation(
            filename: "photo-activity-movement-everyday-fitness-v1.jpg",
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
    let outputSHA256: String
    let width: Int
    let height: Int
    let ownerViewPath: String
    var catalog: V5CatalogExpectation? = nil

    var runtimeName: String {
        catalog?.key ?? filename
    }

    var files: [V5AssetFile] {
        guard let catalog else {
            return [V5AssetFile(
                runtimeCandidatePath: "ios/PulsePlate/Resources/Images/\(filename)",
                outputSHA256: outputSHA256,
                width: width,
                height: height
            )]
        }
        return (catalog.lowerDensitySHA256s + [outputSHA256]).enumerated().map { index, hash in
            let scale = index + 1
            return V5AssetFile(
                runtimeCandidatePath: "\(catalog.directory)/\(catalog.stem)@\(scale)x.png",
                outputSHA256: hash,
                width: width / 3 * scale,
                height: height / 3 * scale
            )
        }
    }

    var resourceName: String {
        URL(fileURLWithPath: filename).deletingPathExtension().lastPathComponent
    }

    var fileExtension: String {
        URL(fileURLWithPath: filename).pathExtension
    }

}

private struct V5CatalogExpectation {
    let key: String
    let stem: String
    let lowerDensitySHA256s: [String]

    var directory: String {
        "ios/PulsePlate/Assets.xcassets/\(key).imageset"
    }
}

private struct V5AssetFile {
    let runtimeCandidatePath: String
    let outputSHA256: String
    let width: Int
    let height: Int

    var filename: String {
        URL(fileURLWithPath: runtimeCandidatePath).lastPathComponent
    }

    var fileExtension: String {
        URL(fileURLWithPath: runtimeCandidatePath).pathExtension
    }
}

private struct PNGChunk {
    let type: String
    let payload: Data
}

private struct JPEGMarker {
    let code: UInt8
    let payload: Data
}

private enum IOSREL2V5AssetParityTestError: Error {
    case repositoryRootNotFound
}

private enum V5AssetEncodingError: Error {
    case invalidICC(String)
    case invalidJPEG(String)
    case invalidPNG(String)
    case outsideRepository(String)
    case truncatedInteger
}
