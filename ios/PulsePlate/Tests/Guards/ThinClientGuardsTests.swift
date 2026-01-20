import Testing
import Foundation

/// Guard tests to prevent BMI logic duplication in iOS thin client.
///
/// Enforces:
/// - No BMI thresholds in app Swift sources (18.5/25/30, waist thresholds 0.5/0.6).
/// - No BMI computation helpers / category inference patterns.
/// - Fixtures are exempt: they can contain thresholds because they mirror backend contract.
///
/// NOTE:
/// This is a source scan guard. It must fail if forbidden patterns appear in app code.
struct ThinClientGuardsTests {
    private static let forbiddenLiterals: [String] = [
        // BMI category thresholds
        "18.5", "18,5",
        "25.0", "25",
        "30.0", "30",
        // Waist risk thresholds (WHtR/Waist-to-height; your docs mention 0.5/0.6)
        "0.5", "0.6"
    ]

    private static let forbiddenPatterns: [String] = [
        // Computation helpers (should not exist on iOS)
        // NOTE: "calculateBMI" is allowed (HTTP method), only "computeBMI(" is forbidden
        "computeBMI(",
        "categoryForBMI(",
        "riskForBMI(",
        "groupForAge(",
        "computeWhtRatio(",
        "computeWHtR(",
        // classic inference smell (catches "if bmi >", "if res.bmi <", etc.)
        // NOTE: "if let category = res.category" is allowed (optional binding, not computation)
        "if bmi",
        "switch bmi",
        "if age <",
        "if age<"
    ]

    @Test("Thin client guard: no BMI thresholds/computation in iOS app sources")
    func noBMILogicInAppSources() throws {
        let root = try repoRoot(from: #filePath)

        // Adjust include dirs to your actual app code layout.
        // Keep these pointed at SOURCE, not tests.
        let includeDirs = [
            "ios/PulsePlate/Models",
            "ios/PulsePlate/Services",
            "ios/PulsePlate/Screens",
            "ios/PulsePlate/ViewModels",
            "ios/PulsePlate/Views",
            "ios/PulsePlate/Components"
        ]

        // Exclude tests & fixtures to allow backend-truth thresholds in fixtures.
        let excludeSubpaths = [
            "/PulsePlateTests/",
            "/Tests/",
            "/Fixtures/",
            "/Mocks/"
        ]

        let swiftFiles = try collectSwiftFiles(
            root: root,
            includeDirs: includeDirs,
            excludeSubpaths: excludeSubpaths
        )

        #expect(!swiftFiles.isEmpty, "Guard scan found 0 Swift files. Check includeDirs paths.")

        var hits: [String] = []

        for file in swiftFiles {
            let content = try String(contentsOf: file, encoding: .utf8)

            for lit in Self.forbiddenLiterals where content.contains(lit) {
                hits.append("\(file.lastPathComponent): forbidden literal '\(lit)'")
            }
            for pat in Self.forbiddenPatterns where content.contains(pat) {
                hits.append("\(file.lastPathComponent): forbidden pattern '\(pat)'")
            }
        }

        #expect(
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

    @Test("Fixtures are allowed to contain thresholds (backend contract truth)")
    func fixturesContainThresholdsAsBackendTruth() throws {
        // This is a sanity check: fixtures may contain thresholds and that's OK.
        // If this ever fails, fixtures were changed and may no longer represent backend examples.
        let json = String(data: BMIFixtures.successJSON(), encoding: .utf8) ?? ""
        #expect(json.contains("18.5"))
        #expect(json.contains("25.0") || json.contains("25"))
        #expect(json.contains("30.0") || json.contains("30"))
    }
}

// MARK: - Helpers

private func repoRoot(from filePath: String) throws -> URL {
    var url = URL(fileURLWithPath: filePath)
    url.deleteLastPathComponent()

    // Walk up until we find "ios" directory (matches your repo layout).
    for _ in 0..<25 {
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
            guard item.pathExtension == "swift" else { continue }
            guard !excludeSubpaths.contains(where: { item.path.contains($0) }) else { continue }
            results.append(item)
        }
    }

    return results
}
