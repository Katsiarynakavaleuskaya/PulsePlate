import XCTest
import Foundation


final class ThinClientGuardsTests: XCTestCase {
    func test_noBMILogicInAppSources() throws {
        let root = try repoRoot(from: #filePath)

        // Scan whole app source tree; exclude tests/fixtures/mocks.
        let includeDir = "ios/PulsePlate"
        let excludeSubpaths = [
            "/PulsePlateTests/",
            "/Tests/",
            "/Fixtures/",
            "/Mocks/"
        ]

        let swiftFiles = try collectSwiftFiles(
            root: root,
            includeDirs: [includeDir],
            excludeSubpaths: excludeSubpaths
        )

        XCTAssertFalse(swiftFiles.isEmpty, "Guard scan found 0 Swift files. Check paths.")

        // Hard-forbidden patterns: explicit computation helpers.
        let forbiddenExact = [
            "computeBMI(",
            "categoryForBMI(",
            "riskForBMI(",
            "computeWhtRatio(",
            "computeWHtR("
        ]

        // Suspicious inference patterns (cheap heuristics).
        // Keep them tight to avoid false positives.
        // NOTE: Case-sensitive by design (Swift identifiers are case-sensitive).
        let forbiddenRegex: [(String, NSRegularExpression)] = [
            ("bmi-threshold-18.5", try NSRegularExpression(pattern: #"\bbmi\b.*\b18[.,]5\b"#, options: [])),
            ("bmi-threshold-25", try NSRegularExpression(pattern: #"\bbmi\b.*\b25(\.0)?\b"#, options: [])),
            ("bmi-threshold-30", try NSRegularExpression(pattern: #"\bbmi\b.*\b30(\.0)?\b"#, options: [])),
            ("bmi-branch-if", try NSRegularExpression(pattern: #"\bif\s+.*\bbmi\b"#, options: [])),
            ("bmi-branch-switch", try NSRegularExpression(pattern: #"\bswitch\s+.*\bbmi\b"#, options: []))
        ]

        // WHtR heuristic: only flag if waist/height division pattern appears (regex-based, precise).
        let whtDivisionRegex = try NSRegularExpression(
            pattern: #"\b(waist|wht|wthr|waisttoheight)\b\s*[/÷]\s*\b(height|wht|wthr|waisttoheight)\b"#,
            options: [.caseInsensitive]
        )
        let whtHeuristic: (String) -> Bool = { content in
            let range = NSRange(content.startIndex..<content.endIndex, in: content)
            return whtDivisionRegex.firstMatch(in: content, options: [], range: range) != nil
        }

        var hits: [String] = []

        for file in swiftFiles {
            let content = try String(contentsOf: file, encoding: .utf8)
            let scanContent = content
                .split(separator: "\n", omittingEmptySubsequences: false)
                .filter { !$0.trimmingCharacters(in: .whitespaces).hasPrefix("//") }
                .joined(separator: "\n")

            for pat in forbiddenExact where scanContent.contains(pat) {
                hits.append("\(relativePath(file, root: root)): forbidden '\(pat)'")
            }

            for (name, rx) in forbiddenRegex {
                let range = NSRange(scanContent.startIndex..<scanContent.endIndex, in: scanContent)
                if rx.firstMatch(in: scanContent, options: [], range: range) != nil {
                    hits.append("\(relativePath(file, root: root)): forbidden regex '\(name)'")
                }
            }

            if whtHeuristic(scanContent) {
                hits.append("\(relativePath(file, root: root)): suspicious WHtR inference (waist/height division)")
            }
        }

        XCTAssertTrue(
            hits.isEmpty,
            """
            ThinClientGuards failed: BMI logic or thresholds detected in iOS app sources.

            Fix:
            - Remove thresholds/computation from iOS.
            - Render backend fields only (thin client).
            - If you need new behavior, change backend engine/contract, not iOS logic.

            Hits:
            \(hits.joined(separator: "\n"))
            """
        )
    }

    func test_noPlaceholderApiKeysInAppSources() throws {
        let root = try repoRoot(from: #filePath)

        // Scan whole app source tree; exclude tests/fixtures/mocks.
        let includeDir = "ios/PulsePlate"
        let excludeSubpaths = [
            "/PulsePlateTests/",
            "/Tests/",
            "/Fixtures/",
            "/Mocks/"
        ]

        let textFiles = try collectTextFiles(
            root: root,
            includeDirs: [includeDir],
            excludeSubpaths: excludeSubpaths,
            allowedExtensions: ["swift", "plist"]
        )

        XCTAssertFalse(textFiles.isEmpty, "Guard scan found 0 files. Check paths.")

        // Hard-forbidden placeholder key(s).
        //
        // RU: Запрещаем placeholder-строку в исходниках приложения.
        // EN: Forbid placeholder key strings in app sources (release safety).
        let forbiddenExact = ["test_pro_key"]

        var hits: [String] = []

        for file in textFiles {
            let content = try String(contentsOf: file, encoding: .utf8)
            for pat in forbiddenExact where content.contains(pat) {
                hits.append("\(relativePath(file, root: root)): contains placeholder '\(pat)'")
            }
        }

        XCTAssertTrue(
            hits.isEmpty,
            """
            ThinClientGuards failed: placeholder API key strings detected in iOS app sources.

            Fix:
            - Remove placeholder keys from iOS sources.
            - Provide keys via env (DEBUG) or Keychain storage, never hardcoded.

            Hits:
            \(hits.joined(separator: "\n"))
            """
        )
    }

    func test_fixturesContainBackendThresholds() throws {
        let json = String(data: BMIFixtures.successJSON(), encoding: .utf8) ?? ""
        XCTAssertTrue(json.contains("18.5"))
        XCTAssertTrue(json.contains("25.0") || json.contains("25"))
        XCTAssertTrue(json.contains("30.0") || json.contains("30"))
    }

    private func relativePath(_ url: URL, root: URL) -> String {
        url.path.replacingOccurrences(of: root.path + "/", with: "")
    }
}

// MARK: - Helpers

private func repoRoot(from filePath: String) throws -> URL {
    var url = URL(fileURLWithPath: filePath)
    url.deleteLastPathComponent()

    for _ in 0..<30 {
        let iosDir = url.appendingPathComponent("ios", isDirectory: true)
        if FileManager.default.fileExists(atPath: iosDir.path) {
            return url
        }
        url.deleteLastPathComponent()
    }

    throw NSError(
        domain: "ThinClientGuards",
        code: 1,
        userInfo: [NSLocalizedDescriptionKey: "Cannot find repo root from: \(filePath)"]
    )
}

private func collectSwiftFiles(
    root: URL,
    includeDirs: [String],
    excludeSubpaths: [String]
) throws -> [URL] {
    try collectTextFiles(
        root: root,
        includeDirs: includeDirs,
        excludeSubpaths: excludeSubpaths,
        allowedExtensions: ["swift"]
    )
}

private func collectTextFiles(
    root: URL,
    includeDirs: [String],
    excludeSubpaths: [String],
    allowedExtensions: Set<String>
) throws -> [URL] {
    var results: [URL] = []

    for dir in includeDirs {
        let base = root.appendingPathComponent(dir, isDirectory: true)
        guard FileManager.default.fileExists(atPath: base.path) else { continue }

        let enumerator = FileManager.default.enumerator(
            at: base,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        )

        while let item = enumerator?.nextObject() as? URL {
            let ext = item.pathExtension.lowercased()
            guard allowedExtensions.contains(ext) else { continue }
            guard !excludeSubpaths.contains(where: { item.path.contains($0) }) else { continue }
            results.append(item)
        }
    }

    return results
}
