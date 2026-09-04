import Compression
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

    func testDerivedFilesMatchTheFrozenMetadataAndEncodingContract() throws {
        let root = try repositoryRoot()
        let assetDirectory = root.appendingPathComponent("ios/PulsePlate/Resources/Images")

        for asset in Self.assets {
            let url = assetDirectory.appendingPathComponent(asset.filename)
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

    func testV5RuntimeOutputHashesAreBoundIntoTheCanonicalAssetRecord() throws {
        let canon = try String(
            contentsOf: repositoryRoot()
                .appendingPathComponent("docs/design/FITCHEF_MASCOT_ASSET_CANON.md"),
            encoding: .utf8
        )

        for asset in Self.assets {
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
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-action-progress-tracking-v1.png",
            outputSHA256: "8d26d8d8464fdaa764abe439694ecf9fd06c9f937d82a4a8d57f3ecaa02cf46a", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/ProgressView.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-action-nutrition-plate-v1.png",
            outputSHA256: "da89403f0fec0a3c183cdd7218a1f37996365c6f6c35104ff1a528eb7bceab80", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/PlateView.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-onboarding-profile-setup-v1.png",
            outputSHA256: "b0e8f856e65c7c78d7f5ae000d30e3c56397d2bcf10ef6b3fda0e692f0d5fbd0", // pragma: allowlist secret
            width: 432,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/ProfileView.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-happy-v1.png",
            outputSHA256: "a84aa312d47edf06316f0d47e60fefb99d12a4c5d6fad18595978a3eabf4c445", // pragma: allowlist secret
            width: 576,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-encouraging-v1.png",
            outputSHA256: "1399e0735f523bd401f6bb96ecd3edf07c377abe3318c1aa06938b58b542c35c", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Views/Home/HomeExperience.swift"
        ),
        V5AssetExpectation(
            filename: "fitchef-portrait-thinking-v1.png",
            outputSHA256: "66d8d84e6b309beaba6fdac6c4b008a366c0aef9659c337ae3fabc80e0b1e33c", // pragma: allowlist secret
            width: 384,
            height: 576,
            ownerViewPath: "ios/PulsePlate/Screens/BMICalculatorScreen.swift"
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

    var resourceName: String {
        URL(fileURLWithPath: filename).deletingPathExtension().lastPathComponent
    }

    var fileExtension: String {
        URL(fileURLWithPath: filename).pathExtension
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
    case truncatedInteger
}
