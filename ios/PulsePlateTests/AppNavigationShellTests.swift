import Foundation
import SwiftUI
import XCTest
@testable import PulsePlate

@MainActor
final class AppNavigationShellTests: XCTestCase {
    private let approvedSections: [AppSection] = [
        .home,
        .bmi,
        .today,
        .progress,
        .profile,
    ]

    private let navigationKeys: Set<String> = [
        "navigation.tab.home",
        "navigation.tab.bmi",
        "navigation.tab.today",
        "navigation.tab.progress",
        "navigation.tab.profile",
        "navigation.progress.weekly",
    ]

    func testApprovedProductionSectionsHaveExactStableOrder() {
        XCTAssertEqual(AppSection.productionSections, approvedSections)
        XCTAssertEqual(AppSection.allCases, approvedSections)
        XCTAssertEqual(approvedSections.map(\.id), ["home", "bmi", "today", "progress", "profile"])
    }

    func testSectionIdentityLocalizationKeysAndSymbolsAreUniqueAndStable() {
        XCTAssertEqual(
            approvedSections.map(\.localizationKey),
            [
                "navigation.tab.home",
                "navigation.tab.bmi",
                "navigation.tab.today",
                "navigation.tab.progress",
                "navigation.tab.profile",
            ]
        )
        XCTAssertEqual(
            approvedSections.map(\.systemImage),
            ["house", "scalemass", "fork.knife", "chart.line.uptrend.xyaxis", "person"]
        )
        XCTAssertEqual(Set(approvedSections.map(\.id)).count, approvedSections.count)
        XCTAssertEqual(Set(approvedSections.map(\.localizationKey)).count, approvedSections.count)
        XCTAssertEqual(Set(approvedSections.map(\.systemImage)).count, approvedSections.count)
    }

    func testProductionInventoryIsOneFixedInputlessDeclaration() throws {
        let appSectionSource = try source(at: "ios/PulsePlate/Models/AppSection.swift")
        let rootTabsSource = try source(at: "ios/PulsePlate/Views/RootTabs.swift")
        let fixedDeclaration =
            #"static\s+let\s+productionSections\s*:\s*\[AppSection\]\s*=\s*\["#
            + #"\s*\.home\s*,\s*\.bmi\s*,\s*\.today\s*,\s*\.progress\s*,"#
            + #"\s*\.profile\s*,?\s*\]"#

        XCTAssertEqual(
            try regexMatchCount(#"\bstatic\s+let\s+productionSections\b"#, in: appSectionSource),
            1
        )
        XCTAssertEqual(try regexMatchCount(fixedDeclaration, in: appSectionSource), 1)
        XCTAssertFalse(appSectionSource.contains("#if"))

        let compactInventorySources = removingWhitespace(
            from: appSectionSource + "\n" + rootTabsSource
        ).lowercased()
        for forbiddenDependency in [
            "subscriptionmanager",
            "featureflag",
            "userdefaults",
            "@appstorage",
            "entitlement",
            "tabviewcustomization",
            "customization",
            ".filter(",
            ".sorted(",
            ".sort(",
            ".append(",
            ".insert(",
            ".remove(",
            ".removeall(",
        ] {
            XCTAssertFalse(
                compactInventorySources.contains(forbiddenDependency),
                "Inventory acquired a runtime dependency: \(forbiddenDependency)"
            )
        }
    }

    func testTopLevelLabelsContainNoTechnicalOrPaidVocabulary() throws {
        let forbiddenWords: Set<String> = [
            "debug",
            "premium",
            "pro",
            "test",
            "vip",
            "week",
            "weekly",
            "неделя",
            "semana",
            "semanal",
        ]

        for locale in ["en", "ru", "es"] {
            let values = try navigationLocalization(locale: locale)
            for section in approvedSections {
                let value = try XCTUnwrap(values[section.localizationKey])
                let words = Set(
                    value.lowercased().split(whereSeparator: { !$0.isLetter }).map(String.init)
                )
                XCTAssertTrue(
                    words.isDisjoint(with: forbiddenWords),
                    "Technical or paid tab label for \(locale): \(value)"
                )
            }
        }
    }

    func testRootTabsUsesOneStableSystemInventoryAtIOS18Boundary() throws {
        let source = try source(at: "ios/PulsePlate/Views/RootTabs.swift")
        let normalized = normalizedWhitespace(source)

        XCTAssertEqual(
            try regexMatchCount(#"TabView\s*\(\s*selection:\s*\$selection\s*\)"#, in: source),
            1
        )
        XCTAssertEqual(
            try regexMatchCount(
                #"ForEach\s*\(\s*AppSection\.productionSections\s*\)"#,
                in: source
            ),
            1
        )
        XCTAssertEqual(try regexMatchCount(#"\.tag\s*\(\s*section\s*\)"#, in: source), 1)
        XCTAssertEqual(
            try regexMatchCount(#"if\s+#available\s*\(\s*iOS\s+18\.0\s*,\s*\*\s*\)"#, in: source),
            1
        )
        XCTAssertEqual(
            try regexMatchCount(#"\.tabViewStyle\s*\(\s*\.sidebarAdaptable\s*\)"#, in: source),
            1
        )
        XCTAssertTrue(
            normalized.contains(
                "if #available(iOS 18.0, *) { systemTabs "
                    + ".tabViewStyle(.sidebarAdaptable) } else { systemTabs }"
            )
        )
        XCTAssertTrue(
            removingWhitespace(from: source).contains(
                ".environment(\\.locale,Locale(identifier:localization.currentLanguage))"
            )
        )
    }

    func testAllFiveDestinationsAreReachableWithExistingStackOwnership() throws {
        let source = try source(at: "ios/PulsePlate/Views/RootTabs.swift")
        let normalized = normalizedWhitespace(source)

        for ownershipFragment in [
            "case .home: NavigationStack { HomeView() }",
            "case .bmi: NavigationStack { BMICalculatorScreen() }",
            "case .today: PlateViewPP()",
            "case .progress: ProgressViewPP()",
            "case .profile: ProfileView()",
        ] {
            XCTAssertTrue(normalized.contains(ownershipFragment), ownershipFragment)
        }
    }

    func testWeeklyProgressIsExactlyOneNavigationNeutralProgressChild() throws {
        let root = try repositoryRoot()
        let progressSource = try source(at: "ios/PulsePlate/Views/ProgressView.swift")
        let weeklySource = try source(at: "ios/PulsePlate/Views/WeeklyProgressView.swift")
        let constructionPaths = try swiftSources(
            under: root.appendingPathComponent("ios/PulsePlate")
        ).compactMap { url -> String? in
            let candidate = try String(contentsOf: url, encoding: .utf8)
            return candidate.contains("WeeklyProgressView()") ? url.path : nil
        }

        XCTAssertEqual(
            constructionPaths,
            [root.appendingPathComponent("ios/PulsePlate/Views/ProgressView.swift").path]
        )
        XCTAssertEqual(
            try regexMatchCount(
                #"NavigationLink\s*\{\s*WeeklyProgressView\(\)\s*\}\s*label:"#,
                in: progressSource
            ),
            1
        )
        XCTAssertTrue(progressSource.contains("navigation.progress.weekly"))

        let introOffset = try XCTUnwrap(progressSource.range(of: "GlassCard {")?.lowerBound)
        let weeklyOffset = try XCTUnwrap(progressSource.range(of: "WeeklyProgressView()")?.lowerBound)
        let loadingOffset = try XCTUnwrap(
            progressSource.range(of: "if nutritionService.isLoading")?.lowerBound
        )
        XCTAssertLessThan(introOffset, weeklyOffset)
        XCTAssertLessThan(weeklyOffset, loadingOffset)

        XCTAssertFalse(weeklySource.contains("NavigationView"))
        XCTAssertFalse(weeklySource.contains("NavigationStack"))
        let normalizedWeeklySource = normalizedWhitespace(weeklySource)
        for healthKitContract in [
            "@StateObject private var hk = HealthKitManager()",
            "hk.requestAuthorization()",
            "hk.fetchWeekTotals(weekOf: Date())",
            "hk.fetchLatestBodyMass()",
            ".task {",
            ".alert(",
            ".onChange(of: hk.error?.localizedDescription)",
        ] {
            XCTAssertTrue(
                normalizedWeeklySource.contains(normalizedWhitespace(healthKitContract)),
                healthKitContract
            )
        }
    }

    func testTechnicalProfileUIIsCompileTimeDebugOnlyAndNeverATab() throws {
        let rootSource = try source(at: "ios/PulsePlate/Views/RootTabs.swift")
        let progressSource = try source(at: "ios/PulsePlate/Views/ProgressView.swift")
        let profileSource = try source(at: "ios/PulsePlate/Views/ProfileView.swift")
        let releaseSource = try releaseProjection(from: profileSource)

        XCTAssertFalse(rootSource.contains("DebugToolsScreen"))
        XCTAssertFalse(rootSource.contains("case .debug"))
        XCTAssertFalse(rootSource.contains("case .weekly"))
        XCTAssertFalse(progressSource.contains("DebugToolsScreen"))
        XCTAssertEqual(
            try regexMatchCount(
                #"NavigationLink\s*\(\s*"Debug Tools"\s*\)\s*\{\s*DebugToolsScreen\(\)\s*\}"#,
                in: profileSource
            ),
            1
        )

        for debugOnlyFragment in [
            "showAnimationTest",
            "showBundleTest",
            "isAppStoreScreenshotMode",
            "Animation Test",
            "SimpleVideoTest",
            "BundleTestView",
            "LottieTestView",
            "DebugToolsScreen",
        ] {
            XCTAssertTrue(profileSource.contains(debugOnlyFragment), debugOnlyFragment)
            XCTAssertFalse(releaseSource.contains(debugOnlyFragment), debugOnlyFragment)
        }
    }

    func testReleaseProjectionPreservesTechnicalUIFromElseBranch() throws {
        let fixture = """
        #if DEBUG
        #if DEBUG
        Text("Nested debug-only")
        #else
        Text("Nested debug else still excluded")
        #endif
        #else
        DebugToolsScreen()
        #if DEBUG
        Text("Release branch debug-only")
        #else
        Text("Release nested else")
        #endif
        #endif
        """

        let releaseSource = try releaseProjection(from: fixture)
        XCTAssertTrue(releaseSource.contains("DebugToolsScreen()"))
        XCTAssertTrue(releaseSource.contains("Release nested else"))
        XCTAssertFalse(releaseSource.contains("Nested debug-only"))
        XCTAssertFalse(releaseSource.contains("Nested debug else still excluded"))
        XCTAssertFalse(releaseSource.contains("Release branch debug-only"))
    }

    func testReleaseProjectionFailsClosedForUnsupportedOrUnbalancedDirectives() {
        let invalidFixtures = [
            "#if RELEASE\nDebugToolsScreen()\n#endif",
            "#if DEBUG\n#elseif RELEASE\nDebugToolsScreen()\n#endif",
            "#if DEBUG\n#else\n#else\n#endif",
            "#endif",
            "#if DEBUG\nDebugToolsScreen()",
        ]

        for fixture in invalidFixtures {
            XCTAssertThrowsError(try releaseProjection(from: fixture), fixture)
        }
    }

    func testProgressSetupDestinationAlwaysUsesProfile() throws {
        let source = try source(at: "ios/PulsePlate/Views/ProgressView.swift")

        XCTAssertEqual(
            try regexMatchCount(
                #"\.navigationDestination\s*\(\s*isPresented:\s*\$showProSetup\s*\)\s*\{\s*ProfileView\(\)\s*\}"#,
                in: source
            ),
            1
        )
        XCTAssertFalse(source.contains("DebugToolsScreen"))
    }

    func testNavigationLocalizationHasExactKeyParityAndApprovedCopy() throws {
        let expected: [String: [String: String]] = [
            "en": [
                "navigation.tab.home": "Home",
                "navigation.tab.bmi": "BMI",
                "navigation.tab.today": "Today",
                "navigation.tab.progress": "Progress",
                "navigation.tab.profile": "Profile",
                "navigation.progress.weekly": "Weekly progress",
            ],
            "ru": [
                "navigation.tab.home": "Главная",
                "navigation.tab.bmi": "ИМТ",
                "navigation.tab.today": "Сегодня",
                "navigation.tab.progress": "Прогресс",
                "navigation.tab.profile": "Профиль",
                "navigation.progress.weekly": "Недельный прогресс",
            ],
            "es": [
                "navigation.tab.home": "Inicio",
                "navigation.tab.bmi": "IMC",
                "navigation.tab.today": "Hoy",
                "navigation.tab.progress": "Progreso",
                "navigation.tab.profile": "Perfil",
                "navigation.progress.weekly": "Progreso semanal",
            ],
        ]

        for locale in ["en", "ru", "es"] {
            let values = try navigationLocalization(locale: locale)
            XCTAssertEqual(Set(values.keys), navigationKeys)
            XCTAssertEqual(values, try XCTUnwrap(expected[locale]))
            for key in navigationKeys {
                let value = try XCTUnwrap(values[key])
                XCTAssertFalse(value.isEmpty, "Empty \(locale) value for \(key)")
                XCTAssertNotEqual(value, key, "Unresolved \(locale) value for \(key)")
            }
        }
    }

    func testAppSelectedLocaleOverridesOuterDeviceLocale() throws {
        let localization = LocalizationManager.shared
        let originalLanguage = localization.currentLanguage
        defer { localization.currentLanguage = originalLanguage }
        let outerDeviceLocale = Locale(identifier: "en")
        XCTAssertEqual(outerDeviceLocale.language.languageCode?.identifier, "en")

        let expectedTitles: [String: [String]] = [
            "en": ["Home", "BMI", "Today", "Progress", "Profile"],
            "ru": ["Главная", "ИМТ", "Сегодня", "Прогресс", "Профиль"],
            "es": ["Inicio", "IMC", "Hoy", "Progreso", "Perfil"],
        ]

        for locale in ["en", "ru", "es"] {
            localization.currentLanguage = locale
            XCTAssertEqual(
                approvedSections.map { $0.localizedTitle(using: localization) },
                try XCTUnwrap(expectedTitles[locale])
            )
        }
    }

    func testCompactRussianAndSpanishCopyIsExactAndBoundedForV1Review() throws {
        let expectedCompactCopy = [
            "ru": ["Главная", "ИМТ", "Сегодня", "Прогресс", "Профиль"],
            "es": ["Inicio", "IMC", "Hoy", "Progreso", "Perfil"],
        ]

        for locale in ["ru", "es"] {
            let values = try navigationLocalization(locale: locale)
            let titles = try approvedSections.map { section in
                try XCTUnwrap(values[section.localizationKey])
            }
            XCTAssertEqual(titles, try XCTUnwrap(expectedCompactCopy[locale]))
            XCTAssertTrue(titles.allSatisfy { !$0.contains("\n") && $0.count <= 8 })
        }
    }

    func testWeeklyProgressNavigationLabelGrowsAtAccessibilityFive() throws {
        let russianValues = try navigationLocalization(locale: "ru")
        let title = try XCTUnwrap(russianValues["navigation.progress.weekly"])
        XCTAssertEqual(title, "Недельный прогресс")

        let compactWidth: CGFloat = 220
        let largeSize = try renderedWeeklyLabelSize(
            title: title,
            width: compactWidth,
            dynamicTypeSize: .large
        )
        let accessibilitySize = try renderedWeeklyLabelSize(
            title: title,
            width: compactWidth,
            dynamicTypeSize: .accessibility5
        )

        XCTAssertEqual(largeSize.width, compactWidth, accuracy: 1)
        XCTAssertEqual(accessibilitySize.width, compactWidth, accuracy: 1)
        XCTAssertGreaterThan(
            accessibilitySize.height,
            largeSize.height,
            "The real Weekly link label must grow vertically at Accessibility 5"
        )
    }

    func testWeeklyProgressNavigationLabelUsesScaledTypographyContract() throws {
        let source = try source(at: "ios/PulsePlate/Views/ProgressView.swift")
        let marker = try XCTUnwrap(
            source.range(of: "struct WeeklyProgressNavigationLabel: View")?.lowerBound
        )
        let componentSource = String(source[marker...])
        let normalizedComponent = normalizedWhitespace(componentSource)
        let scaledMetricPattern =
            #"@ScaledMetric\s*\(\s*relativeTo:\s*\.headline\s*\)"#
            + #"\s*private\s+var\s+titleSize\s*="#
            + #"\s*PPDesignTokens\.Typography\.sizeLG"#

        XCTAssertEqual(
            try regexMatchCount(scaledMetricPattern, in: componentSource),
            1
        )
        XCTAssertFalse(componentSource.contains("PPDesignTokens.Typography.title"))
        XCTAssertTrue(
            normalizedComponent.contains(
                "Text(title) .font(.system(size: titleSize, weight: .semibold))"
            )
        )
        XCTAssertTrue(normalizedComponent.contains(".lineLimit(nil)"))
        XCTAssertTrue(normalizedComponent.contains(".multilineTextAlignment(.leading)"))
        XCTAssertTrue(
            normalizedComponent.contains(".fixedSize(horizontal: false, vertical: true)")
        )
        XCTAssertEqual(
            try regexMatchCount(
                #"Image\s*\(\s*systemName:\s*"chevron\.forward"\s*\).*?\.accessibilityHidden\s*\(\s*true\s*\)"#,
                in: componentSource
            ),
            1
        )
        for forbiddenWork in ["APIClient", "Consent", "Task {", "UUID("] {
            XCTAssertFalse(componentSource.contains(forbiddenWork), forbiddenWork)
        }
    }

    func testRootTabsIntroducesNoEagerCoachNetworkConsentOrUUIDWork() throws {
        let source = try source(at: "ios/PulsePlate/Views/RootTabs.swift")
        for forbiddenFragment in [
            "FitChefCoachView(",
            "APIClient(",
            "AIWellnessDisclosureSheet(",
            "Consent",
            "UUID(",
            ".task {",
            ".onAppear",
        ] {
            XCTAssertFalse(source.contains(forbiddenFragment), forbiddenFragment)
        }
    }

    private func navigationLocalization(locale: String) throws -> [String: String] {
        let url = try repositoryRoot()
            .appendingPathComponent("ios/PulsePlate")
            .appendingPathComponent("\(locale).lproj")
            .appendingPathComponent("Localizable.strings")
        let data = try Data(contentsOf: url)
        let propertyList = try PropertyListSerialization.propertyList(
            from: data,
            options: [],
            format: nil
        )
        guard let values = propertyList as? [String: String] else {
            throw AppNavigationShellTestError.invalidLocalizationFile(locale)
        }
        return values.filter { navigationKeys.contains($0.key) }
    }

    private func renderedWeeklyLabelSize(
        title: String,
        width: CGFloat,
        dynamicTypeSize: DynamicTypeSize
    ) throws -> CGSize {
        let content = WeeklyProgressNavigationLabel(title: title)
            .dynamicTypeSize(dynamicTypeSize)
            .frame(width: width, alignment: .leading)
        let renderer = ImageRenderer(content: content)
        renderer.scale = 1
        renderer.proposedSize = ProposedViewSize(width: width, height: nil)

        return try XCTUnwrap(
            renderer.uiImage,
            "WeeklyProgressNavigationLabel did not render at \(dynamicTypeSize)"
        ).size
    }

    private func source(at relativePath: String) throws -> String {
        try String(
            contentsOf: repositoryRoot().appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    private func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        let fileManager = FileManager.default

        while candidate.path != "/" {
            if fileManager.fileExists(atPath: candidate.appendingPathComponent(".git").path) {
                return candidate
            }
            candidate = candidate.deletingLastPathComponent()
        }

        throw AppNavigationShellTestError.repositoryRootNotFound
    }

    private func swiftSources(under root: URL) throws -> [URL] {
        let keys: [URLResourceKey] = [.isRegularFileKey]
        guard let enumerator = FileManager.default.enumerator(
            at: root,
            includingPropertiesForKeys: keys,
            options: [.skipsHiddenFiles]
        ) else {
            throw AppNavigationShellTestError.sourceEnumerationFailed
        }

        return try enumerator.compactMap { item -> URL? in
            guard let url = item as? URL, url.pathExtension == "swift" else { return nil }
            let values = try url.resourceValues(forKeys: Set(keys))
            return values.isRegularFile == true ? url : nil
        }.sorted { $0.path < $1.path }
    }

    private func releaseProjection(from source: String) throws -> String {
        var frames: [DebugCompilationFrame] = []
        var includesCurrentLine = true
        var lines: [String] = []

        for line in source.split(separator: "\n", omittingEmptySubsequences: false) {
            let text = String(line)
            let trimmed = text.trimmingCharacters(in: .whitespaces)

            if trimmed.hasPrefix("#elseif") {
                throw AppNavigationShellTestError.unsupportedCompilationDirective(trimmed)
            }
            if trimmed.hasPrefix("#if") {
                guard trimmed == "#if DEBUG" else {
                    throw AppNavigationShellTestError.unsupportedCompilationDirective(trimmed)
                }
                frames.append(
                    DebugCompilationFrame(
                        parentIncluded: includesCurrentLine,
                        sawElse: false
                    )
                )
                includesCurrentLine = false
                continue
            }
            if trimmed.hasPrefix("#else") {
                guard trimmed == "#else" else {
                    throw AppNavigationShellTestError.unsupportedCompilationDirective(trimmed)
                }
                guard var frame = frames.popLast() else {
                    throw AppNavigationShellTestError.unexpectedElseDirective
                }
                guard !frame.sawElse else {
                    throw AppNavigationShellTestError.duplicateElseDirective
                }
                frame.sawElse = true
                frames.append(frame)
                includesCurrentLine = frame.parentIncluded
                continue
            }
            if trimmed.hasPrefix("#endif") {
                guard trimmed == "#endif" else {
                    throw AppNavigationShellTestError.unsupportedCompilationDirective(trimmed)
                }
                guard let frame = frames.popLast() else {
                    throw AppNavigationShellTestError.unexpectedEndifDirective
                }
                includesCurrentLine = frame.parentIncluded
                continue
            }

            if includesCurrentLine {
                lines.append(text)
            }
        }

        guard frames.isEmpty else {
            throw AppNavigationShellTestError.unterminatedCompilationDirective
        }
        return lines.joined(separator: "\n")
    }

    private func regexMatchCount(_ pattern: String, in source: String) throws -> Int {
        let expression = try NSRegularExpression(
            pattern: pattern,
            options: [.dotMatchesLineSeparators]
        )
        return expression.numberOfMatches(
            in: source,
            range: NSRange(source.startIndex ..< source.endIndex, in: source)
        )
    }

    private func normalizedWhitespace(_ source: String) -> String {
        source.split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
    }

    private func removingWhitespace(from source: String) -> String {
        String(source.filter { !$0.isWhitespace })
    }
}

private struct DebugCompilationFrame {
    let parentIncluded: Bool
    var sawElse: Bool
}

private enum AppNavigationShellTestError: Error {
    case duplicateElseDirective
    case invalidLocalizationFile(String)
    case repositoryRootNotFound
    case sourceEnumerationFailed
    case unexpectedElseDirective
    case unexpectedEndifDirective
    case unsupportedCompilationDirective(String)
    case unterminatedCompilationDirective
}
