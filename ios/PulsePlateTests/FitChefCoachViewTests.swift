import Foundation
import SwiftUI
import XCTest
@testable import PulsePlate

@MainActor
final class FitChefCoachViewTests: XCTestCase {
    private let frozenCapabilityCaseNames = [
        "aiGuidance",
        "planningDirection",
    ]

    private let localizationKeys: Set<String> = [
        "fitchef.coach_hub.ai_guidance.accessibility_hint",
        "fitchef.coach_hub.ai_guidance.detail",
        "fitchef.coach_hub.ai_guidance.title",
        "fitchef.coach_hub.header.description",
        "fitchef.coach_hub.header.title",
        "fitchef.coach_hub.navigation.title",
        "fitchef.coach_hub.planning_direction.accessibility_hint",
        "fitchef.coach_hub.planning_direction.detail",
        "fitchef.coach_hub.planning_direction.title",
    ]

    func testCapabilityCaseInventoryIsExactlyTheTwoFrozenCases() throws {
        let runtimeCases: [FitChefCoachCapability] = [
            .aiGuidance,
            .planningDirection,
        ]
        XCTAssertEqual(runtimeCases, [.aiGuidance, .planningDirection])

        let source = try fitChefCoachSource()
        let capabilitySource = try sourceSlice(
            source,
            from: "enum FitChefCoachCapability: Equatable",
            to: "struct FitChefCoachAvailability: Equatable"
        )

        XCTAssertEqual(enumCaseNames(in: capabilitySource), frozenCapabilityCaseNames)
    }

    func testAvailabilityPreservesEveryFrozenOrderedInventory() {
        let inventories: [[FitChefCoachCapability]] = [
            [],
            [.aiGuidance],
            [.planningDirection],
            [.aiGuidance, .planningDirection],
        ]

        for inventory in inventories {
            XCTAssertEqual(
                FitChefCoachAvailability(capabilities: inventory).capabilities,
                inventory
            )
        }

        let reversedBoth: [FitChefCoachCapability] = [
            .planningDirection,
            .aiGuidance,
        ]
        XCTAssertEqual(
            FitChefCoachAvailability(capabilities: reversedBoth).capabilities,
            reversedBoth
        )
    }

    func testAvailabilityNormalizesDuplicatesWhilePreservingFirstOccurrenceOrder() {
        let cases: [(
            input: [FitChefCoachCapability],
            expected: [FitChefCoachCapability]
        )] = [
            (
                input: [.aiGuidance, .aiGuidance],
                expected: [.aiGuidance]
            ),
            (
                input: [.planningDirection, .planningDirection],
                expected: [.planningDirection]
            ),
            (
                input: [
                    .aiGuidance,
                    .planningDirection,
                    .aiGuidance,
                    .planningDirection,
                ],
                expected: [.aiGuidance, .planningDirection]
            ),
            (
                input: [
                    .planningDirection,
                    .aiGuidance,
                    .planningDirection,
                    .aiGuidance,
                ],
                expected: [.planningDirection, .aiGuidance]
            ),
        ]

        for testCase in cases {
            XCTAssertEqual(
                FitChefCoachAvailability(capabilities: testCase.input).capabilities,
                testCase.expected
            )
        }
    }

    func testGenericTextDestinationsCompileWithoutEvaluatingBuilders() {
        let probe = FitChefCoachDestinationBuildProbe()
        let availability = FitChefCoachAvailability(capabilities: [.aiGuidance])
        let view: FitChefCoachView<Text, Text> = makeCoachView(
            availability: availability,
            probe: probe
        )

        XCTAssertEqual(view.availability, availability)
        XCTAssertEqual(probe.aiGuidanceBuildCount, 0)
        XCTAssertEqual(probe.planningDirectionBuildCount, 0)
    }

    func testConcreteExistingDestinationsTypeCheckWithoutEagerBuilderEvaluation() async throws {
        let aiService = FitChefCoachNoCallAIService()
        let supportService = FitChefCoachNoCallSupportService()
        let destinationProbe = FitChefCoachConcreteDestinationProbe(
            aiService: aiService,
            consentProvider: FitChefCoachNoCallAIConsentProvider(),
            supportService: supportService
        )
        let availability = FitChefCoachAvailability(
            capabilities: [.aiGuidance, .planningDirection]
        )

        let hub: FitChefCoachView<AIInsightView, FitChefSupportFlowScreen> =
            FitChefCoachView(
                availability: availability,
                aiGuidanceDestination: {
                    destinationProbe.makeAIInsightDestination()
                },
                planningDirectionDestination: {
                    destinationProbe.makePlanningDirectionDestination()
                }
            )

        XCTAssertEqual(hub.availability, availability)
        XCTAssertEqual(destinationProbe.aiGuidanceBuildCount, 0)
        XCTAssertEqual(destinationProbe.planningDirectionBuildCount, 0)
        let aiServiceCallCount = await aiService.recordedCallCount()
        let supportServiceCallCount = await supportService.recordedCallCount()
        XCTAssertEqual(aiServiceCallCount, 0)
        XCTAssertEqual(supportServiceCallCount, 0)
    }

    func testFrozenInventoryRenderMatrixDoesNotEvaluateDestinationBuilders() throws {
        let inventories: [[FitChefCoachCapability]] = [
            [],
            [.aiGuidance],
            [.planningDirection],
            [.aiGuidance, .planningDirection],
        ]

        for inventory in inventories {
            let probe = FitChefCoachDestinationBuildProbe()
            let view = makeCoachView(
                availability: FitChefCoachAvailability(capabilities: inventory),
                probe: probe
            )
            .environment(\.locale, Locale(identifier: "en"))

            XCTAssertEqual(probe.aiGuidanceBuildCount, 0)
            XCTAssertEqual(probe.planningDirectionBuildCount, 0)

            let renderer = ImageRenderer(
                content: view.frame(width: 390, height: 844)
            )
            renderer.scale = 1
            renderer.proposedSize = ProposedViewSize(width: 390, height: 844)

            let renderedSize = try XCTUnwrap(
                renderer.uiImage,
                "The Hub inventory must render for \(inventory)."
            ).size
            XCTAssertGreaterThan(renderedSize.width, 0)
            XCTAssertGreaterThan(renderedSize.height, 0)
            XCTAssertEqual(probe.aiGuidanceBuildCount, 0)
            XCTAssertEqual(probe.planningDirectionBuildCount, 0)
        }
    }

    func testMissingCapabilitiesAreOmittedWithoutPlaceholderOrDisabledPromises() throws {
        let source = try fitChefCoachSource()
        let availabilitySource = try sourceSlice(
            source,
            from: "struct FitChefCoachAvailability: Equatable",
            to: "struct FitChefCoachView<"
        )

        XCTAssertTrue(
            source.contains("ForEach(availability.capabilities.indices, id: \\.self)")
        )
        XCTAssertTrue(
            source.contains("capabilityLink(for: availability.capabilities[index])")
        )
        XCTAssertEqual(
            occurrenceCount(of: "let capabilities: [FitChefCoachCapability]", in: availabilitySource),
            1
        )
        XCTAssertFalse(source.contains("FitChefCoachCapability.allCases"))
        XCTAssertFalse(source.contains(".disabled("))
        XCTAssertFalse(source.contains("default:"))

        let lowercaseSource = source.lowercased()
        for promise in [
            "coming soon",
            "coming_soon",
            "future capability",
            "future-capability",
            "placeholder",
            "unavailable capability",
        ] {
            XCTAssertFalse(
                lowercaseSource.contains(promise),
                "The Hub must omit missing capabilities instead of rendering: \(promise)"
            )
        }
    }

    func testCapabilityBranchesBindOnlyTheirOwnBuilderCopyAndAccessibilityIdentity() throws {
        let source = try fitChefCoachSource()
        let aiGuidanceBranch = try sourceSlice(
            source,
            from: "case .aiGuidance:",
            to: "case .planningDirection:"
        )
        let planningDirectionBranch = try sourceSlice(
            source,
            from: "case .planningDirection:",
            to: "private func capabilityCard("
        )

        XCTAssertEqual(
            occurrenceCount(of: "makeAIGuidanceDestination", in: aiGuidanceBranch),
            1
        )
        XCTAssertFalse(aiGuidanceBranch.contains("makePlanningDirectionDestination"))
        XCTAssertEqual(
            fitChefCoachStringLiterals(in: aiGuidanceBranch),
            [
                "fitchef.coach_hub.ai_guidance.title",
                "fitchef.coach_hub.ai_guidance.detail",
                "fitchef.coach_hub.ai_guidance.accessibility_hint",
                "fitchef.coach_hub.card.ai_guidance",
            ]
        )

        XCTAssertEqual(
            occurrenceCount(
                of: "makePlanningDirectionDestination",
                in: planningDirectionBranch
            ),
            1
        )
        XCTAssertFalse(planningDirectionBranch.contains("makeAIGuidanceDestination"))
        XCTAssertEqual(
            fitChefCoachStringLiterals(in: planningDirectionBranch),
            [
                "fitchef.coach_hub.planning_direction.title",
                "fitchef.coach_hub.planning_direction.detail",
                "fitchef.coach_hub.planning_direction.accessibility_hint",
                "fitchef.coach_hub.card.planning_direction",
            ]
        )
    }

    func testStaticSourceUsesLazyGenericNavigationAndStableAccessibilityIdentifiers() throws {
        let source = try fitChefCoachSource()
        let requiredFragments = [
            "struct FitChefCoachView<AIGuidanceDestination: View, "
                + "PlanningDirectionDestination: View>: View",
            "private let makeAIGuidanceDestination: () -> AIGuidanceDestination",
            "private let makePlanningDirectionDestination: () -> PlanningDirectionDestination",
            "@ViewBuilder aiGuidanceDestination: @escaping () -> AIGuidanceDestination",
            "@ViewBuilder planningDirectionDestination: @escaping () "
                + "-> PlanningDirectionDestination",
            "FitChefCoachLazyDestination(build: makeAIGuidanceDestination)",
            "FitChefCoachLazyDestination(build: makePlanningDirectionDestination)",
            "private struct FitChefCoachLazyDestination<Destination: View>: View",
            "var body: some View {\n        build()\n    }",
            "ScrollView {",
            "PPCard {",
            "Image(\"FitChef\")",
            ".frame(maxWidth: 650)",
            "PPAccessibility.minimumTouchTarget",
            "@Environment(\\.dynamicTypeSize) private var dynamicTypeSize",
            "dynamicTypeSize.isAccessibilitySize",
        ]
        for fragment in requiredFragments {
            XCTAssertTrue(source.contains(fragment), "Missing source contract: \(fragment)")
        }

        XCTAssertEqual(occurrenceCount(of: "NavigationLink {", in: source), 2)
        XCTAssertEqual(
            occurrenceCount(of: ".accessibilityElement(children: .ignore)", in: source),
            2
        )
        XCTAssertEqual(occurrenceCount(of: ".accessibilityHint(", in: source), 2)
        XCTAssertEqual(
            occurrenceCount(
                of: ".accessibilityIdentifier(\"fitchef.coach_hub.screen\")",
                in: source
            ),
            1
        )
        XCTAssertEqual(
            occurrenceCount(
                of: ".accessibilityIdentifier(\"fitchef.coach_hub.card.ai_guidance\")",
                in: source
            ),
            1
        )
        XCTAssertEqual(
            occurrenceCount(
                of: ".accessibilityIdentifier(\"fitchef.coach_hub.card.planning_direction\")",
                in: source
            ),
            1
        )
    }

    func testSourceContractRejectsAuthorityNetworkingAndChildFlowOwnership() throws {
        let source = try fitChefCoachSource()
        let forbiddenExactFragments = [
            "AnyView",
            "NavigationStack",
            ".navigationDestination",
            "APIClient",
            "HTTPClient",
            "URLSession",
            "ProKeyProvider",
            "SubscriptionManager",
            "StoreKit",
            "ObservableObject",
            "@StateObject",
            "@ObservedObject",
            "@EnvironmentObject",
        ]
        for fragment in forbiddenExactFragments {
            XCTAssertFalse(source.contains(fragment), "Forbidden Hub authority: \(fragment)")
        }

        let lowercaseSource = source.lowercased()
        let forbiddenLowercaseFragments = [
            "service",
            "viewmodel",
            "view model",
            "consent",
            "submit",
            "descriptor",
            "outcome",
            "analytics",
            "logger",
            "logging",
            "os_log",
            ".log(",
            "print(",
            "deeplink",
            "deep_link",
            "openurl",
            "open_url",
            "tier",
            "quota",
            "rawerror",
            "raw_error",
            "raw error",
            "sourcepreview",
            "source_preview",
            "source preview",
            "previewsource",
            "preview_source",
            "preview source",
        ]
        for fragment in forbiddenLowercaseFragments {
            XCTAssertFalse(
                lowercaseSource.contains(fragment),
                "Forbidden Hub authority term: \(fragment)"
            )
        }
    }

    func testHubHasExactlyOneProductionRegistrationThroughHomeLazyDestination() throws {
        let root = try repositoryRoot()
        let productionRoot = root.appendingPathComponent("ios/PulsePlate")
        let candidateURL = try fitChefCoachSourceURL().standardizedFileURL
        let constructionReferences = try swiftSources(under: productionRoot)
            .filter { $0.standardizedFileURL != candidateURL }
            .compactMap { url -> String? in
                let source = try String(contentsOf: url, encoding: .utf8)
                return source.contains("FitChefCoachView(") ? url.path : nil
            }

        XCTAssertEqual(
            constructionReferences,
            [root.appendingPathComponent("ios/PulsePlate/Views/HomeView.swift").path]
        )

        let home = try String(
            contentsOf: root.appendingPathComponent("ios/PulsePlate/Views/HomeView.swift"),
            encoding: .utf8
        )
        XCTAssertEqual(occurrenceCount(of: "FitChefCoachView(", in: home), 1)
        let homeExperience = try String(
            contentsOf: root.appendingPathComponent(
                "ios/PulsePlate/Views/Home/HomeExperience.swift"
            ),
            encoding: .utf8
        )
        let homeActionLink = try sourceSlice(
            homeExperience,
            from: "private func actionLink(",
            to: "@ViewBuilder\n    private func actionCard("
        )
        let lazyDestinationInvocation = "NavigationLink {\n            HomeLazyDestination {\n"
            + "                makeDestination(action)\n            }\n        } label: {"
        XCTAssertTrue(homeActionLink.contains(lazyDestinationInvocation))

        for relativePath in [
            "ios/PulsePlate/Views/RootTabs.swift",
            "ios/PulsePlate/PulsePlateApp.swift",
        ] {
            let source = try String(
                contentsOf: root.appendingPathComponent(relativePath),
                encoding: .utf8
            )
            XCTAssertFalse(source.contains("FitChefCoachView("), relativePath)
        }
    }

    func testLocalizationContractHasExactNineKeyParityAndFrozenCopy() throws {
        let expectedValues = frozenLocalizationValues

        XCTAssertEqual(localizationKeys.count, 9)
        XCTAssertEqual(Set(expectedValues.keys), ["en", "ru", "es"])

        for locale in ["en", "ru", "es"] {
            let localizedValues = try loadFitChefCoachLocalization(locale: locale)
            let rawLocalization = try rawFitChefCoachLocalization(locale: locale)
            let expectedLocaleValues = try XCTUnwrap(expectedValues[locale])

            XCTAssertEqual(Set(localizedValues.keys), localizationKeys)
            XCTAssertEqual(localizedValues.count, 9)
            XCTAssertEqual(
                occurrenceCount(of: "\"fitchef.coach_hub.", in: rawLocalization),
                9
            )
            XCTAssertEqual(localizedValues, expectedLocaleValues)

            for key in localizationKeys {
                let value = try XCTUnwrap(localizedValues[key])
                let trimmedValue = value.trimmingCharacters(in: .whitespacesAndNewlines)
                let lowercaseValue = value.lowercased()

                XCTAssertFalse(trimmedValue.isEmpty, "Empty \(locale) value for \(key)")
                XCTAssertNotEqual(value, key, "Unresolved \(locale) value for \(key)")
                XCTAssertFalse(value.contains("fitchef.coach_hub."))
                XCTAssertFalse(value.contains("%"), "Format placeholder in \(locale) \(key)")
                XCTAssertFalse(value.contains("{"), "Interpolation marker in \(locale) \(key)")
                XCTAssertFalse(value.contains("}"), "Interpolation marker in \(locale) \(key)")
                XCTAssertFalse(value.contains("\\("), "Swift interpolation in \(locale) \(key)")
                XCTAssertFalse(value.contains("://"), "URL in \(locale) \(key)")
                XCTAssertFalse(lowercaseValue.contains("www."), "URL in \(locale) \(key)")
            }
        }
    }

    func testLocalizationCopyContainsNoFutureOrDisabledCapabilityPromise() throws {
        let forbiddenCopyFragments = [
            "coming soon",
            "unavailable",
            "disabled",
            "future capability",
            "later release",
            "скоро",
            "недоступ",
            "отключ",
            "в будущем",
            "позже",
            "próximamente",
            "no disponible",
            "deshabilitad",
            "en el futuro",
            "más tarde",
        ]

        for locale in ["en", "ru", "es"] {
            let localizedValues = try loadFitChefCoachLocalization(locale: locale)
            for (key, value) in localizedValues {
                let lowercaseValue = value.lowercased()
                for fragment in forbiddenCopyFragments {
                    XCTAssertFalse(
                        lowercaseValue.contains(fragment),
                        "Future or disabled promise in \(locale) \(key): \(fragment)"
                    )
                }
            }
        }
    }

    func testFileSystemSynchronizedMembershipRemainsAutomaticAndSuiteIsTargetedOnce() throws {
        let root = try repositoryRoot()
        let project = try String(
            contentsOf: root.appendingPathComponent(
                "ios/PulsePlate.xcodeproj/project.pbxproj"
            ),
            encoding: .utf8
        )

        XCTAssertTrue(project.contains("fileSystemSynchronizedGroups = ("))
        XCTAssertTrue(project.contains("path = PulsePlate; sourceTree = \"<group>\";"))
        XCTAssertTrue(project.contains("path = PulsePlateTests; sourceTree = \"<group>\";"))
        XCTAssertFalse(project.contains("FitChefCoachView.swift"))
        XCTAssertFalse(project.contains("FitChefCoachViewTests.swift"))

        let testSelectorSource = try String(
            contentsOf: root.appendingPathComponent("scripts/ios_test_targets.sh"),
            encoding: .utf8
        )
        let outputCommands = testSelectorSource.components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { $0.hasPrefix("printf ") }
        XCTAssertEqual(outputCommands, ["printf '%s' 'PulsePlateTests'"])
        XCTAssertFalse(testSelectorSource.contains("PulsePlateTests/"))
        XCTAssertFalse(testSelectorSource.contains("TESTS=("))
        XCTAssertFalse(testSelectorSource.contains("IFS=','"))
    }

    private var frozenLocalizationValues: [String: [String: String]] {
        [
            "en": [
                "fitchef.coach_hub.navigation.title": "FitChef Coach",
                "fitchef.coach_hub.header.title": "How would you like to continue?",
                "fitchef.coach_hub.header.description":
                    "You stay in control of what happens next.",
                "fitchef.coach_hub.ai_guidance.title": "Ask FitChef",
                "fitchef.coach_hub.ai_guidance.detail":
                    "Ask a wellness question and receive AI-generated guidance.",
                "fitchef.coach_hub.ai_guidance.accessibility_hint":
                    "Opens Ask FitChef.",
                "fitchef.coach_hub.planning_direction.title": "Where to start?",
                "fitchef.coach_hub.planning_direction.detail":
                    "You choose: Today or This week.",
                "fitchef.coach_hub.planning_direction.accessibility_hint":
                    "Opens choices for Today or This week.",
            ],
            "ru": [
                "fitchef.coach_hub.navigation.title": "FitChef Coach",
                "fitchef.coach_hub.header.title": "Как вы хотите продолжить?",
                "fitchef.coach_hub.header.description":
                    "Вы сами решаете, что делать дальше.",
                "fitchef.coach_hub.ai_guidance.title": "Спросить FitChef",
                "fitchef.coach_hub.ai_guidance.detail":
                    "Задайте вопрос о благополучии и получите AI-подсказку.",
                "fitchef.coach_hub.ai_guidance.accessibility_hint":
                    "Открывает экран «Спросить FitChef».",
                "fitchef.coach_hub.planning_direction.title": "С чего начать?",
                "fitchef.coach_hub.planning_direction.detail":
                    "Вы сами выбираете: «Сегодня» или «Неделя».",
                "fitchef.coach_hub.planning_direction.accessibility_hint":
                    "Открывает выбор «Сегодня» или «Неделя».",
            ],
            "es": [
                "fitchef.coach_hub.navigation.title": "FitChef Coach",
                "fitchef.coach_hub.header.title": "¿Cómo quieres continuar?",
                "fitchef.coach_hub.header.description":
                    "Tú decides qué hacer a continuación.",
                "fitchef.coach_hub.ai_guidance.title": "Preguntar a FitChef",
                "fitchef.coach_hub.ai_guidance.detail":
                    "Haz una pregunta de bienestar y recibe orientación generada por AI.",
                "fitchef.coach_hub.ai_guidance.accessibility_hint":
                    "Abre «Preguntar a FitChef».",
                "fitchef.coach_hub.planning_direction.title":
                    "¿Por dónde quieres empezar?",
                "fitchef.coach_hub.planning_direction.detail":
                    "Tú eliges: «Hoy» o «Esta semana».",
                "fitchef.coach_hub.planning_direction.accessibility_hint":
                    "Abre las opciones «Hoy» o «Esta semana».",
            ],
        ]
    }

    private func makeCoachView(
        availability: FitChefCoachAvailability,
        probe: FitChefCoachDestinationBuildProbe
    ) -> FitChefCoachView<Text, Text> {
        FitChefCoachView(
            availability: availability,
            aiGuidanceDestination: { probe.makeAIGuidanceDestination() },
            planningDirectionDestination: { probe.makePlanningDirectionDestination() }
        )
    }

    private func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        let fileManager = FileManager.default

        while candidate.path != "/" {
            if fileManager.fileExists(
                atPath: candidate.appendingPathComponent(".git").path
            ) {
                return candidate
            }
            candidate = candidate.deletingLastPathComponent()
        }

        throw FitChefCoachViewTestError.repositoryRootNotFound
    }

    private func fitChefCoachSourceURL() throws -> URL {
        try repositoryRoot().appendingPathComponent(
            "ios/PulsePlate/Views/FitChef/FitChefCoachView.swift"
        )
    }

    private func fitChefCoachSource() throws -> String {
        try String(contentsOf: fitChefCoachSourceURL(), encoding: .utf8)
    }

    private func rawFitChefCoachLocalization(locale: String) throws -> String {
        try String(contentsOf: localizationURL(locale: locale), encoding: .utf8)
    }

    private func loadFitChefCoachLocalization(locale: String) throws -> [String: String] {
        let data = try Data(contentsOf: localizationURL(locale: locale))
        let propertyList = try PropertyListSerialization.propertyList(
            from: data,
            options: [],
            format: nil
        )
        guard let values = propertyList as? [String: String] else {
            throw FitChefCoachViewTestError.invalidLocalizationFile(locale)
        }
        return values.filter { $0.key.hasPrefix("fitchef.coach_hub.") }
    }

    private func localizationURL(locale: String) throws -> URL {
        try repositoryRoot()
            .appendingPathComponent("ios/PulsePlate")
            .appendingPathComponent("\(locale).lproj")
            .appendingPathComponent("Localizable.strings")
    }

    private func swiftSources(under root: URL) throws -> [URL] {
        let rootValues = try root.resourceValues(forKeys: [.isDirectoryKey])
        guard rootValues.isDirectory == true else {
            throw FitChefCoachViewTestError.sourceRootNotDirectory
        }

        let resourceKeys: Set<URLResourceKey> = [.isRegularFileKey]
        var traversalError: Error?
        guard let enumerator = FileManager.default.enumerator(
            at: root,
            includingPropertiesForKeys: Array(resourceKeys),
            options: [.skipsHiddenFiles],
            errorHandler: { _, error in
                traversalError = error
                return false
            }
        ) else {
            throw FitChefCoachViewTestError.sourceEnumerationUnavailable
        }

        var sources: [URL] = []
        while let url = enumerator.nextObject() as? URL {
            guard url.pathExtension == "swift" else {
                continue
            }
            let values = try url.resourceValues(forKeys: resourceKeys)
            if values.isRegularFile == true {
                sources.append(url)
            }
        }

        if let traversalError {
            throw traversalError
        }
        return sources.sorted { $0.path < $1.path }
    }

    private func sourceSlice(
        _ source: String,
        from startAnchor: String,
        to endAnchor: String
    ) throws -> String {
        let start = try XCTUnwrap(source.range(of: startAnchor)?.lowerBound)
        let remainder = source[start...]
        let end = try XCTUnwrap(remainder.range(of: endAnchor)?.lowerBound)
        return String(source[start..<end])
    }

    private func enumCaseNames(in source: String) -> [String] {
        source.split(separator: "\n").flatMap { line -> [String] in
            let trimmedLine = String(line).trimmingCharacters(in: .whitespaces)
            guard trimmedLine.hasPrefix("case ") else {
                return []
            }
            return trimmedLine.dropFirst("case ".count).split(separator: ",").compactMap {
                declaration in
                let name = String(declaration).trimmingCharacters(in: .whitespaces)
                return name.split(whereSeparator: { character in
                    character == " " || character == "(" || character == ":"
                }).first.map(String.init)
            }
        }
    }

    private func fitChefCoachStringLiterals(in source: String) -> Set<String> {
        Set(
            source.components(separatedBy: "\"").filter {
                $0.hasPrefix("fitchef.coach_hub.")
            }
        )
    }

    private func occurrenceCount(of needle: String, in source: String) -> Int {
        source.components(separatedBy: needle).count - 1
    }
}

@MainActor
private final class FitChefCoachDestinationBuildProbe {
    private(set) var aiGuidanceBuildCount = 0
    private(set) var planningDirectionBuildCount = 0

    func makeAIGuidanceDestination() -> Text {
        aiGuidanceBuildCount += 1
        return Text("AI guidance destination")
    }

    func makePlanningDirectionDestination() -> Text {
        planningDirectionBuildCount += 1
        return Text("Planning direction destination")
    }
}

@MainActor
private final class FitChefCoachConcreteDestinationProbe {
    private let aiService: FitChefCoachNoCallAIService
    private let consentProvider: FitChefCoachNoCallAIConsentProvider
    private let supportService: FitChefCoachNoCallSupportService

    private(set) var aiGuidanceBuildCount = 0
    private(set) var planningDirectionBuildCount = 0

    init(
        aiService: FitChefCoachNoCallAIService,
        consentProvider: FitChefCoachNoCallAIConsentProvider,
        supportService: FitChefCoachNoCallSupportService
    ) {
        self.aiService = aiService
        self.consentProvider = consentProvider
        self.supportService = supportService
    }

    func makeAIInsightDestination() -> AIInsightView {
        aiGuidanceBuildCount += 1
        return AIInsightView(
            vm: AIInsightViewModel(
                service: aiService,
                apiKeyProvider: { nil },
                consentProvider: consentProvider
            )
        )
    }

    func makePlanningDirectionDestination() -> FitChefSupportFlowScreen {
        planningDirectionBuildCount += 1
        return FitChefSupportFlowScreen(
            viewModel: FitChefSupportFlowViewModel(
                service: supportService,
                apiKeyProvider: { nil },
                makeClientEventID: { UUID() }
            )
        )
    }
}

private actor FitChefCoachNoCallAIService: CBTInsightServicing {
    private var callCount = 0

    func fetchInsight(query: String, apiKey: String) async throws -> CBTInsightResponseDTO {
        callCount += 1
        throw FitChefCoachViewTestError.unexpectedAIServiceCall
    }

    func recordedCallCount() -> Int {
        callCount
    }
}

private actor FitChefCoachNoCallSupportService: FitChefSupportServicing {
    private var callCount = 0

    func requestHandoff(
        for supportNeed: FitChefSupportNeed,
        apiKey: String
    ) async throws -> FitChefSupportHandoffDescriptor {
        callCount += 1
        throw FitChefCoachViewTestError.unexpectedSupportServiceCall
    }

    func recordOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        apiKey: String
    ) async throws -> FitChefSupportOutcomeReceipt {
        callCount += 1
        throw FitChefCoachViewTestError.unexpectedSupportServiceCall
    }

    func recordedCallCount() -> Int {
        callCount
    }
}

private struct FitChefCoachNoCallAIConsentProvider: AIWellnessConsentProviding {
    func hasAccepted() -> Bool {
        preconditionFailure("Concrete Hub construction must not query AI consent.")
    }

    func markAccepted() {
        preconditionFailure("Concrete Hub construction must not mutate AI consent.")
    }
}

private enum FitChefCoachViewTestError: Error {
    case invalidLocalizationFile(String)
    case repositoryRootNotFound
    case sourceRootNotDirectory
    case sourceEnumerationUnavailable
    case unexpectedAIServiceCall
    case unexpectedSupportServiceCall
}
