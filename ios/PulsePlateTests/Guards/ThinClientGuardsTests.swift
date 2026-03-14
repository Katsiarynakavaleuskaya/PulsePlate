import XCTest
import Foundation


final class ThinClientGuardsTests: XCTestCase {
    func test_noBMILogicInAppSources() throws {
        let root = try repoRoot(from: #filePath)

        // Scan whole app source tree; exclude tests/fixtures/mocks.
        let includeDir = "ios/PulsePlate"
        let excludeSubpaths = guardedSourceExcludeSubpaths()

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
            // RU: Убираем комментарии, чтобы guard сканировал только исполняемый код.
            // EN: Strip comments so the guard scans executable code only.
            let scanContent = stripSwiftComments(from: content)

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
        let excludeSubpaths = guardedSourceExcludeSubpaths()

        let textFiles = try collectTextFiles(
            root: root,
            includeDirs: [includeDir],
            excludeSubpaths: excludeSubpaths,
            allowedExtensions: Set(["swift", "plist"])
        )

        XCTAssertFalse(textFiles.isEmpty, "Guard scan found 0 files. Check paths.")

        // Hard-forbidden placeholder key(s).
        //
        // RU: Запрещаем placeholder-строку в исходниках приложения.
        // EN: Forbid placeholder key strings in app sources (release safety).
        let forbiddenExact = ["test_pro_key"]

        var hits: [String] = []

        for file in textFiles {
            let ext = file.pathExtension.lowercased()
            let data = try Data(contentsOf: file)

            guard let content =
                String(data: data, encoding: .utf8)
                ?? String(data: data, encoding: .utf16)
            else {
                hits.append("\(relativePath(file, root: root)): unreadable text (non-UTF8/UTF-16)")
                continue
            }

            // RU: Игнорируем закомментированные placeholder-строки, чтобы не ловить false positives.
            // EN: Ignore commented-out placeholders to avoid guard false positives in Swift sources.
            let scanContent = ext == "swift" ? stripSwiftComments(from: content) : content

            for pat in forbiddenExact where scanContent.contains(pat) {
                hits.append("\(relativePath(file, root: root)): contains placeholder '\(pat)'")
            }
        }

        XCTAssertTrue(
            hits.isEmpty,
            """
            ThinClientGuards failed: placeholder API key strings detected in iOS app sources.

            Fix:
            - Remove placeholder keys from iOS sources.
            - Use Keychain-backed providers or explicit test injection seams, never hardcoded values.

            Hits:
            \(hits.joined(separator: "\n"))
            """
        )
    }

    func test_noSensitiveSecretsPersistedOutsideKeychain() throws {
        let root = try repoRoot(from: #filePath)

        let includeDir = "ios/PulsePlate"
        let excludeSubpaths = guardedSourceExcludeSubpaths()

        let swiftFiles = try collectTextFiles(
            root: root,
            includeDirs: [includeDir],
            excludeSubpaths: excludeSubpaths,
            allowedExtensions: Set(["swift"])
        ).sorted { $0.path < $1.path }

        XCTAssertFalse(swiftFiles.isEmpty, "Guard scan found 0 Swift files. Check paths.")

        var hits: [String] = []

        for file in swiftFiles {
            let content = try String(contentsOf: file, encoding: .utf8)
            hits.append(contentsOf: try secretStorageGuardHits(
                in: content,
                sourceLabel: relativePath(file, root: root)
            ))
        }

        hits.sort()

        XCTAssertTrue(
            hits.isEmpty,
            """
            ThinClientGuards failed: sensitive keys are persisted outside Keychain.

            Fix:
            - Store secrets only via Keychain-backed helpers.
            - Do not persist API keys/tokens/secrets/passwords with AppStorage or UserDefaults.

            Hits:
            \(hits.joined(separator: "\n"))
            """
        )
    }

    func test_noRuntimeSecretEnvFallbackInAppSources() throws {
        let root = try repoRoot(from: #filePath)

        let swiftFiles = try collectTextFiles(
            root: root,
            includeDirs: ["ios/PulsePlate"],
            excludeSubpaths: guardedSourceExcludeSubpaths(),
            allowedExtensions: Set(["swift"])
        )

        XCTAssertFalse(swiftFiles.isEmpty, "Guard scan found 0 Swift files. Check paths.")

        var hits: [String] = []

        for file in swiftFiles {
            let content = try String(contentsOf: file, encoding: .utf8)
            hits.append(contentsOf: try secretEnvFallbackHits(
                in: content,
                sourceLabel: relativePath(file, root: root)
            ))
        }

        hits.sort()

        XCTAssertTrue(
            hits.isEmpty,
            """
            ThinClientGuards failed: runtime secret env fallback detected in iOS app sources.

            Fix:
            - Use Keychain-backed providers for runtime secrets.
            - Keep dev/test injection explicit at call sites, not via ProcessInfo env fallback.

            Hits:
            \(hits.joined(separator: "\n"))
            """
        )
    }

    func test_secretEnvFallbackGuardMatchesProcessInfoSecretLookup() throws {
        let snippet = """
        if let key = ProcessInfo.processInfo.environment["PRO_API_KEY"], !key.isEmpty {
            return key
        }
        """

        let hits = try secretEnvFallbackHits(
            in: snippet,
            sourceLabel: "snippet.swift"
        )

        XCTAssertFalse(hits.isEmpty)
    }

    func test_secretEnvFallbackGuardMatchesAliasedProcessInfoEnvironment() throws {
        let snippet = """
        let env = ProcessInfo.processInfo.environment
        if let key = env["PRO_API_KEY"], !key.isEmpty {
            return key
        }
        """

        let hits = try secretEnvFallbackHits(
            in: snippet,
            sourceLabel: "snippet.swift"
        )

        XCTAssertFalse(hits.isEmpty)
    }

    func test_secretEnvFallbackGuardMatchesPrivateAliasedProcessInfoEnvironment() throws {
        let snippet = """
        final class SecretHolder {
            private let env = ProcessInfo.processInfo.environment

            func key() -> String? {
                self.env["PRO_API_KEY"]
            }
        }
        """

        let hits = try secretEnvFallbackHits(
            in: snippet,
            sourceLabel: "snippet.swift"
        )

        XCTAssertFalse(hits.isEmpty)
    }

    func test_secretEnvFallbackGuardDoesNotMatchNonSecretEnvLookups() throws {
        let snippet = """
        let baseURL = ProcessInfo.processInfo.environment["API_BASE_URL"]
        let lang = ProcessInfo.processInfo.environment["APP_LANGUAGE"]
        """

        let hits = try secretEnvFallbackHits(
            in: snippet,
            sourceLabel: "snippet.swift"
        )

        XCTAssertTrue(hits.isEmpty)
    }

    func test_secretStorageGuardMatchesIndirectKeyForms() throws {
        let forbiddenRegex = try secretStorageForbiddenRegexes(userDefaultsAliases: ["defaults", "cache"])

        let appStorageSnippet = """
        @AppStorage(StorageKeys.proToken) private var cachedToken: String = ""
        """
        let userDefaultsSnippet = """
        let defaults = UserDefaults(suiteName: "group.dev")
        defaults?.set(token, forKey: StorageKeys.pro.secretKey)
        """

        let appStorageHits = try secretStorageGuardHits(
            in: appStorageSnippet,
            sourceLabel: "snippet.swift",
            forbiddenRegex: forbiddenRegex
        )
        let userDefaultsHits = try secretStorageGuardHits(
            in: userDefaultsSnippet,
            sourceLabel: "snippet.swift",
            forbiddenRegex: forbiddenRegex
        )

        XCTAssertFalse(appStorageHits.isEmpty)
        XCTAssertFalse(userDefaultsHits.isEmpty)
    }

    func test_secretStorageGuardMatchesAliasedUserDefaultsVariables() throws {
        let snippet = """
        private let store: UserDefaults

        func cache(_ token: String) {
            store.set(token, forKey: StorageKeys.pro.secretKey)
        }
        """

        let hits = try secretStorageGuardHits(
            in: snippet,
            sourceLabel: "snippet.swift"
        )

        XCTAssertFalse(hits.isEmpty)
    }

    func test_secretStorageGuardMatchesUserDefaultsParameters() throws {
        let snippet = """
        func cache(token: String, using store: UserDefaults) {
            store.set(token, forKey: StorageKeys.pro.secretKey)
        }

        func clear(_ store: UserDefaults) {
            store.set("", forKey: StorageKeys.pro.secretKey)
        }

        func update(token: String, inout store: UserDefaults) {
            store.set(token, forKey: StorageKeys.pro.secretKey)
        }
        """

        let hits = try secretStorageGuardHits(
            in: snippet,
            sourceLabel: "snippet.swift"
        )

        XCTAssertFalse(hits.isEmpty)
    }

    func test_secretStorageGuardDoesNotMatchNonUserDefaultsStorage() throws {
        let forbiddenRegex = try secretStorageForbiddenRegexes()

        let nonUserDefaultsSnippet = """
        let secureStore = SomeOtherStore()
        secureStore.set(token, forKey: StorageKeys.pro.secretKey)
        """

        let hits = try secretStorageGuardHits(
            in: nonUserDefaultsSnippet,
            sourceLabel: "snippet.swift",
            forbiddenRegex: forbiddenRegex
        )

        XCTAssertTrue(hits.isEmpty)
    }

    func test_subscriptionFlowFilesDoNotUseDirectURLSession() throws {
        let root = try repoRoot(from: #filePath)
        let guardedFiles = [
            "ios/PulsePlate/Services/SubscriptionManager.swift",
            "ios/PulsePlate/Services/SubscriptionBillingService.swift",
            "ios/PulsePlate/Screens/PaywallScreen.swift"
        ]

        var hits: [String] = []
        for relativeFile in guardedFiles {
            let fileURL = root.appendingPathComponent(relativeFile)
            guard FileManager.default.fileExists(atPath: fileURL.path) else {
                hits.append("\(relativeFile): missing guarded file")
                continue
            }
            let content = try String(contentsOf: fileURL, encoding: .utf8)
            let scanContent = stripSwiftComments(from: content)
            if scanContent.contains("URLSession") {
                hits.append(relativeFile)
            }
        }

        XCTAssertTrue(
            hits.isEmpty,
            """
            ThinClientGuards failed: direct URLSession usage or missing guarded files detected in subscription flow files.

            Fix:
            - Route billing transport through APIClient / HTTPClient only.

            Hits:
            \(hits.joined(separator: "\n"))
            """
        )
    }

    func test_subscriptionFlowFilesDoNotReintroduceLocalPaidTruthFlags() throws {
        let root = try repoRoot(from: #filePath)
        let guardedFiles = [
            "ios/PulsePlate/Models/StoreKitManager.swift",
            "ios/PulsePlate/Services/SubscriptionManager.swift",
            "ios/PulsePlate/Screens/PaywallScreen.swift"
        ]
        let forbiddenFlags = ["isPremium", "isPro", "isVip", "hasPaidAccess"]

        var hits: [String] = []
        for relativeFile in guardedFiles {
            let fileURL = root.appendingPathComponent(relativeFile)
            guard FileManager.default.fileExists(atPath: fileURL.path) else {
                hits.append("\(relativeFile): missing guarded file")
                continue
            }
            let content = try String(contentsOf: fileURL, encoding: .utf8)
            let scanContent = stripSwiftComments(from: content)
            for forbiddenFlag in forbiddenFlags where containsToken(forbiddenFlag, in: scanContent) {
                hits.append("\(relativeFile): \(forbiddenFlag)")
            }
        }

        XCTAssertTrue(
            hits.isEmpty,
            """
            ThinClientGuards failed: local paid-truth flags detected in subscription flow files.

            Fix:
            - Publish backend entitlement state instead of local tier booleans.

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

private func containsToken(_ token: String, in content: String) -> Bool {
    let pattern = "(?<![A-Za-z0-9_])\(NSRegularExpression.escapedPattern(for: token))(?![A-Za-z0-9_])"
    guard let regex = try? NSRegularExpression(pattern: pattern) else {
        return false
    }

    let range = NSRange(content.startIndex..<content.endIndex, in: content)
    return regex.firstMatch(in: content, range: range) != nil
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
        allowedExtensions: Set(["swift"])
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
            if (try? item.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile) != true {
                continue
            }
            let ext = item.pathExtension.lowercased()
            guard allowedExtensions.contains(ext) else { continue }
            guard !excludeSubpaths.contains(where: { item.path.contains($0) }) else { continue }
            results.append(item)
        }
    }

    return results.sorted { $0.path < $1.path }
}

private func guardedSourceExcludeSubpaths() -> [String] {
    [
        "/PulsePlateTests/",
        "/Tests/",
        "/Fixtures/",
        "/Mocks/",
    ]
}

private func secretStorageForbiddenRegexes(
    userDefaultsAliases: Set<String> = []
) throws -> [(String, NSRegularExpression)] {
    let aliasAlternation = userDefaultsAliasAlternation(userDefaultsAliases)

    return [
        (
            "appstorage-secret-key",
            try NSRegularExpression(
                pattern: #"@AppStorage\(\s*(?:"[^"]*(api[_-]?key|token|secret|password)[^"]*"|[A-Za-z_][A-Za-z0-9_\.]*(?:api[_-]?key|token|secret|password)[A-Za-z0-9_\.]*)\s*\)"#,
                options: [.caseInsensitive]
            )
        ),
        (
            "userdefaults-secret-key",
            try NSRegularExpression(
                pattern: #"\b(?:UserDefaults(?:\s*\([^)]*\)|(?:\.\w+)*)"# + aliasAlternation + #")\b[\s\S]{0,120}?forKey:\s*(?:"[^"]*(api[_-]?key|token|secret|password)[^"]*"|[A-Za-z_][A-Za-z0-9_\.]*(?:api[_-]?key|token|secret|password)[A-Za-z0-9_\.]*)"#,
                options: [.caseInsensitive]
            )
        ),
    ]
}

private func secretStorageGuardHits(
    in content: String,
    sourceLabel: String,
    forbiddenRegex: [(String, NSRegularExpression)]? = nil
) throws -> [String] {
    let scanContent = stripSwiftComments(from: content)
    let regexes = try forbiddenRegex ?? secretStorageForbiddenRegexes(
        userDefaultsAliases: extractUserDefaultsAliases(from: scanContent)
    )
    let range = NSRange(scanContent.startIndex..<scanContent.endIndex, in: scanContent)
    var hits: [String] = []

    for (name, regex) in regexes {
        let matches = regex.matches(in: scanContent, options: [], range: range)
        for match in matches {
            let location = lineAndSnippet(for: match.range, in: scanContent)
            hits.append(
                "\(sourceLabel):\(location.line): forbidden regex '\(name)' -> \(location.snippet)"
            )
        }
    }

    return hits
}

private func secretEnvFallbackHits(
    in content: String,
    sourceLabel: String,
    forbiddenRegex: [(String, NSRegularExpression)]? = nil
) throws -> [String] {
    let scanContent = stripSwiftComments(from: content)
    let regexes = try forbiddenRegex ?? secretEnvFallbackRegexes(
        environmentAliases: extractProcessInfoEnvironmentAliases(from: scanContent)
    )
    let range = NSRange(scanContent.startIndex..<scanContent.endIndex, in: scanContent)
    var hits: [String] = []

    for (name, regex) in regexes {
        let matches = regex.matches(in: scanContent, options: [], range: range)
        for match in matches {
            let location = lineAndSnippet(for: match.range, in: scanContent)
            hits.append(
                "\(sourceLabel):\(location.line): forbidden regex '\(name)' -> \(location.snippet)"
            )
        }
    }

    return hits
}

private func extractProcessInfoEnvironmentAliases(from content: String) -> Set<String> {
    let patterns = [
        #"\b(?:private|fileprivate|internal|public|open)?\s*(?:lazy\s+)?(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*\[[^\]]+\])?\s*=\s*ProcessInfo\.processInfo\.environment\b"#,
    ]
    var aliases: Set<String> = []
    let searchRange = NSRange(content.startIndex..<content.endIndex, in: content)

    for pattern in patterns {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else {
            continue
        }
        for match in regex.matches(in: content, options: [], range: searchRange) {
            guard
                match.numberOfRanges > 1,
                let aliasRange = Range(match.range(at: 1), in: content)
            else {
                continue
            }
            aliases.insert(String(content[aliasRange]))
        }
    }

    return aliases
}

private func secretEnvFallbackRegexes(
    environmentAliases: Set<String> = []
) throws -> [(String, NSRegularExpression)] {
    let aliasAlternation = environmentAliasAlternation(environmentAliases)

    return [
        (
            "processinfo-secret-env",
            try NSRegularExpression(
                pattern: #"\b(?:ProcessInfo\.processInfo\.environment"# + aliasAlternation + #")\s*\[\s*(?:"[^"]*(api[_-]?key|token|secret|password)[^"]*"|[A-Za-z_][A-Za-z0-9_\.]*(?:api[_-]?key|token|secret|password)[A-Za-z0-9_\.]*)\s*\]"#,
                options: [.caseInsensitive]
            )
        ),
    ]
}

private func extractUserDefaultsAliases(from content: String) -> Set<String> {
    let patterns = [
        #"\b(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*UserDefaults(?:\?)?)?(?:\s*=\s*UserDefaults(?:\s*\([^)]*\)|(?:\.\w+)*))"#,
        #"\b(?:private|fileprivate|internal|public|open)?\s*(?:lazy\s+)?(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*UserDefaults(?:\?)?\b"#,
        #"(?:\(|,)\s*(?:(?:[A-Za-z_][A-Za-z0-9_]*|_)\s+)?(?:inout\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*UserDefaults(?:\?)?\b"#,
    ]
    var aliases: Set<String> = []
    let searchRange = NSRange(content.startIndex..<content.endIndex, in: content)

    for pattern in patterns {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else {
            continue
        }
        for match in regex.matches(in: content, options: [], range: searchRange) {
            guard
                match.numberOfRanges > 1,
                let aliasRange = Range(match.range(at: 1), in: content)
            else {
                continue
            }
            aliases.insert(String(content[aliasRange]))
        }
    }

    return aliases
}

private func environmentAliasAlternation(_ aliases: Set<String>) -> String {
    guard !aliases.isEmpty else {
        return ""
    }

    let escapedAliases = aliases
        .sorted()
        .map(NSRegularExpression.escapedPattern(for:))
        .joined(separator: "|")

    return "|(?:(?:self\\.)?(?:\(escapedAliases)))"
}

private func userDefaultsAliasAlternation(_ aliases: Set<String>) -> String {
    guard !aliases.isEmpty else {
        return ""
    }

    let escapedAliases = aliases
        .sorted()
        .map(NSRegularExpression.escapedPattern(for:))
        .joined(separator: "|")

    return "|(?:\(escapedAliases))"
}

private func lineAndSnippet(for range: NSRange, in content: String) -> (line: Int, snippet: String) {
    guard
        let swiftRange = Range(range, in: content)
    else {
        return (line: 1, snippet: "<unavailable>")
    }

    let prefix = content[..<swiftRange.lowerBound]
    let line = prefix.reduce(into: 1) { partial, character in
        if character == "\n" {
            partial += 1
        }
    }

    let snippet = content[swiftRange]
        .replacingOccurrences(of: "\n", with: " ")
        .trimmingCharacters(in: .whitespacesAndNewlines)

    return (line: line, snippet: snippet)
}

private func stripSwiftComments(from source: String) -> String {
    // RU: Удаляет // и /* */ комментарии из Swift исходника, сохраняя строковые литералы.
    // EN: Strips // and /* */ comments from Swift source while preserving string literals.
    let bytes = Array(source.utf8)

    var out: [UInt8] = []
    out.reserveCapacity(bytes.count)

    var index = 0
    var inLineComment = false
    var blockCommentDepth = 0

    var inString = false
    var inMultilineString = false
    var stringDelimiterHashes = 0

    func isNewline(_ byte: UInt8) -> Bool {
        byte == 0x0A || byte == 0x0D
    }

    while index < bytes.count {
        let byte = bytes[index]

        if inLineComment {
            if isNewline(byte) {
                out.append(byte)
                inLineComment = false
            }
            index += 1
            continue
        }

        if blockCommentDepth > 0 {
            if isNewline(byte) {
                out.append(byte)
                index += 1
                continue
            }
            if byte == 0x2F, index + 1 < bytes.count, bytes[index + 1] == 0x2A { // /*
                blockCommentDepth += 1
                index += 2
                continue
            }
            if byte == 0x2A, index + 1 < bytes.count, bytes[index + 1] == 0x2F { // */
                blockCommentDepth -= 1
                index += 2
                continue
            }
            index += 1
            continue
        }

        if inString {
            if inMultilineString {
                if byte == 0x22, index + 2 < bytes.count,
                   bytes[index + 1] == 0x22, bytes[index + 2] == 0x22 {
                    let hashStart = index + 3
                    let hashEnd = hashStart + stringDelimiterHashes
                    if hashEnd <= bytes.count,
                       bytes[hashStart..<hashEnd].allSatisfy({ $0 == 0x23 }) {
                        out.append(0x22)
                        out.append(0x22)
                        out.append(0x22)
                        out.append(contentsOf: bytes[hashStart..<hashEnd])
                        index = hashEnd
                        inString = false
                        inMultilineString = false
                        stringDelimiterHashes = 0
                        continue
                    }
                }

                out.append(byte)
                index += 1
                continue
            }

            if stringDelimiterHashes > 0 {
                if byte == 0x22 {
                    let hashStart = index + 1
                    let hashEnd = hashStart + stringDelimiterHashes
                    if hashEnd <= bytes.count,
                       bytes[hashStart..<hashEnd].allSatisfy({ $0 == 0x23 }) {
                        out.append(0x22)
                        out.append(contentsOf: bytes[hashStart..<hashEnd])
                        index = hashEnd
                        inString = false
                        stringDelimiterHashes = 0
                        continue
                    }
                }

                out.append(byte)
                index += 1
                continue
            }

            if byte == 0x22 {
                var backslashCount = 0
                var scan = index
                while scan > 0, bytes[scan - 1] == 0x5C { // '\'
                    backslashCount += 1
                    scan -= 1
                }

                out.append(byte)
                index += 1
                if backslashCount % 2 == 0 {
                    inString = false
                }
                continue
            }

            out.append(byte)
            index += 1
            continue
        }

        // Raw string start: #"... "#, ##"... "##, including multiline #""" ... """#
        if byte == 0x23 { // '#'
            let start = index
            var hashCount = 0
            while index < bytes.count, bytes[index] == 0x23 {
                hashCount += 1
                index += 1
            }

            if index < bytes.count, bytes[index] == 0x22 { // '"'
                let quoteCount = (index + 2 < bytes.count && bytes[index + 1] == 0x22 && bytes[index + 2] == 0x22)
                    ? 3
                    : 1

                out.append(contentsOf: bytes[start..<(index + quoteCount)])
                index += quoteCount

                inString = true
                inMultilineString = quoteCount == 3
                stringDelimiterHashes = hashCount
                continue
            }

            out.append(contentsOf: bytes[start..<index])
            continue
        }

        // Normal string start: "..." or multiline """ ... """
        if byte == 0x22 { // '"'
            let quoteCount = (index + 2 < bytes.count && bytes[index + 1] == 0x22 && bytes[index + 2] == 0x22)
                ? 3
                : 1

            out.append(contentsOf: bytes[index..<(index + quoteCount)])
            index += quoteCount

            inString = true
            inMultilineString = quoteCount == 3
            stringDelimiterHashes = 0
            continue
        }

        // Comment start (only outside strings).
        if byte == 0x2F, index + 1 < bytes.count {
            let next = bytes[index + 1]
            if next == 0x2F { // //
                inLineComment = true
                index += 2
                continue
            }
            if next == 0x2A { // /*
                if out.last != 0x20, out.last != 0x09, out.last != 0x0A, out.last != 0x0D {
                    out.append(0x20)
                }
                blockCommentDepth = 1
                index += 2
                continue
            }
        }

        out.append(byte)
        index += 1
    }

    return String(decoding: out, as: UTF8.self)
}
