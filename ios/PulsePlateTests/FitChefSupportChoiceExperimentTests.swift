import Foundation
import XCTest
@testable import PulsePlate

@MainActor
final class FitChefSupportChoiceExperimentTests: XCTestCase {
    private let topLevelFields = [
        "schema_version",
        "scenario",
        "support_need",
        "action",
        "user_confirmation_required",
        "execution_authority",
        "plan_mutation_authority",
        "used_llm",
        "wellness_boundary",
    ]

    private let localizationKeys: Set<String> = [
        "fitchef.support_choice.agency",
        "fitchef.support_choice.confirm",
        "fitchef.support_choice.consequence",
        "fitchef.support_choice.daily.detail",
        "fitchef.support_choice.daily.title",
        "fitchef.support_choice.dismiss",
        "fitchef.support_choice.question",
        "fitchef.support_choice.weekly.detail",
        "fitchef.support_choice.weekly.title",
        "fitchef.support_choice.wellness",
    ]

    func testCanonicalDailyAndWeeklyDescriptorsDecodeExactly() throws {
        let daily = try decodeDescriptor(
            canonicalPayload(
                supportNeed: "daily_structure",
                targetSurface: "pro_daily_plate"
            )
        )
        let weekly = try decodeDescriptor(
            canonicalPayload(
                supportNeed: "weekly_structure",
                targetSurface: "pro_weekly_plan"
            )
        )

        XCTAssertEqual(daily.schemaVersion, .v1)
        XCTAssertEqual(daily.scenario, .supportHandoff)
        XCTAssertEqual(daily.supportNeed, .dailyStructure)
        XCTAssertEqual(daily.action.actionType, .handoffToProductSurface)
        XCTAssertEqual(daily.action.targetSurface, .proDailyPlate)
        XCTAssertTrue(daily.userConfirmationRequired)
        XCTAssertFalse(daily.executionAuthority)
        XCTAssertFalse(daily.planMutationAuthority)
        XCTAssertFalse(daily.usedLlm)
        XCTAssertEqual(daily.wellnessBoundary, .wellnessPlanningOnly)

        XCTAssertEqual(weekly.supportNeed, .weeklyStructure)
        XCTAssertEqual(weekly.action.targetSurface, .proWeeklyPlan)
    }

    func testSupportNeedAndTargetSurfaceTruthTableAcceptsOnlyDiagonalPairs() throws {
        let cases = [
            ("daily_structure", "pro_daily_plate", true),
            ("daily_structure", "pro_weekly_plan", false),
            ("weekly_structure", "pro_daily_plate", false),
            ("weekly_structure", "pro_weekly_plan", true),
        ]

        for (supportNeed, targetSurface, isValid) in cases {
            let payload = canonicalPayload(
                supportNeed: supportNeed,
                targetSurface: targetSurface
            )

            if isValid {
                XCTAssertNoThrow(
                    try decodeDescriptor(payload),
                    "Expected valid pair \(supportNeed) -> \(targetSurface)"
                )
            } else {
                XCTAssertThrowsError(
                    try decodeDescriptor(payload),
                    "Expected invalid pair \(supportNeed) -> \(targetSurface)"
                ) { error in
                    XCTAssertEqual(
                        dataCorruptedDescription(error),
                        "support_need and action.target_surface must form a compatible handoff pair"
                    )
                }
            }
        }
    }

    func testEveryRequiredTopLevelFieldIsRequired() throws {
        for field in topLevelFields {
            var payload = canonicalPayload()
            payload.removeValue(forKey: field)

            XCTAssertThrowsError(
                try decodeDescriptor(payload),
                "Expected missing top-level field to fail: \(field)"
            )
        }
    }

    func testEveryRequiredNestedActionFieldIsRequired() throws {
        for field in ["action_type", "target_surface"] {
            var payload = canonicalPayload()
            var action = try XCTUnwrap(payload["action"] as? [String: Any])
            action.removeValue(forKey: field)
            payload["action"] = action

            XCTAssertThrowsError(
                try decodeDescriptor(payload),
                "Expected missing action field to fail: \(field)"
            )
        }
    }

    func testUnknownRawTopLevelKeysUseStableObjectDiagnosticWithoutRawNames() throws {
        var payload = canonicalPayload()
        payload["z_extra"] = true
        payload["a_extra"] = true

        XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
            let diagnostic = dataCorruptedDescription(error)
            XCTAssertEqual(diagnostic, "FitChefSupportHandoffDescriptor contains unknown key(s)")
            XCTAssertFalse(diagnostic?.contains("a_extra") == true)
            XCTAssertFalse(diagnostic?.contains("z_extra") == true)
        }
    }

    func testUnknownRawActionKeysUseStableObjectDiagnosticWithoutRawNames() throws {
        var payload = canonicalPayload()
        var action = try XCTUnwrap(payload["action"] as? [String: Any])
        action["z_extra"] = true
        action["a_extra"] = true
        payload["action"] = action

        XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
            let diagnostic = dataCorruptedDescription(error)
            XCTAssertEqual(diagnostic, "FitChefSupportHandoffAction contains unknown key(s)")
            XCTAssertFalse(diagnostic?.contains("a_extra") == true)
            XCTAssertFalse(diagnostic?.contains("z_extra") == true)
        }
    }

    func testCamelCaseTopLevelAliasesAreRejectedAsUnknownRawKeys() throws {
        let aliases = [
            ("schema_version", "schemaVersion"),
            ("support_need", "supportNeed"),
            ("user_confirmation_required", "userConfirmationRequired"),
            ("execution_authority", "executionAuthority"),
            ("plan_mutation_authority", "planMutationAuthority"),
            ("used_llm", "usedLlm"),
            ("wellness_boundary", "wellnessBoundary"),
        ]

        for (canonicalKey, aliasKey) in aliases {
            var payload = canonicalPayload()
            payload[aliasKey] = payload.removeValue(forKey: canonicalKey)

            XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
                let diagnostic = dataCorruptedDescription(error)
                XCTAssertEqual(
                    diagnostic,
                    "FitChefSupportHandoffDescriptor contains unknown key(s)"
                )
                XCTAssertFalse(diagnostic?.contains(aliasKey) == true)
            }
        }
    }

    func testCamelCaseActionAliasesAreRejectedAsUnknownRawKeys() throws {
        let aliases = [
            ("action_type", "actionType"),
            ("target_surface", "targetSurface"),
        ]

        for (canonicalKey, aliasKey) in aliases {
            var payload = canonicalPayload()
            var action = try XCTUnwrap(payload["action"] as? [String: Any])
            action[aliasKey] = action.removeValue(forKey: canonicalKey)
            payload["action"] = action

            XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
                let diagnostic = dataCorruptedDescription(error)
                XCTAssertEqual(diagnostic, "FitChefSupportHandoffAction contains unknown key(s)")
                XCTAssertFalse(diagnostic?.contains(aliasKey) == true)
            }
        }
    }

    func testCanonicalAndCamelCaseAliasCollisionsFailAsUnknownKeys() throws {
        var payload = canonicalPayload()
        payload["schemaVersion"] = payload["schema_version"]
        payload["supportNeed"] = payload["support_need"]
        var action = try XCTUnwrap(payload["action"] as? [String: Any])
        action["actionType"] = action["action_type"]
        action["targetSurface"] = action["target_surface"]
        payload["action"] = action

        XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
            let diagnostic = dataCorruptedDescription(error)
            XCTAssertEqual(diagnostic, "FitChefSupportHandoffDescriptor contains unknown key(s)")
            XCTAssertFalse(diagnostic?.contains("schemaVersion") == true)
            XCTAssertFalse(diagnostic?.contains("supportNeed") == true)
        }

        payload.removeValue(forKey: "schemaVersion")
        payload.removeValue(forKey: "supportNeed")
        XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
            let diagnostic = dataCorruptedDescription(error)
            XCTAssertEqual(diagnostic, "FitChefSupportHandoffAction contains unknown key(s)")
            XCTAssertFalse(diagnostic?.contains("actionType") == true)
            XCTAssertFalse(diagnostic?.contains("targetSurface") == true)
        }
    }

    func testHostileTopLevelUnknownKeysAndSensitiveValuesDoNotEnterDiagnostic() throws {
        let hostileEntries = [
            ("password_reset_token", "SENSITIVE_TOP_LEVEL_VALUE_1"),
            ("forged\nlog_line", "SENSITIVE_TOP_LEVEL_VALUE_2"),
        ]
        var payload = canonicalPayload()
        for (key, value) in hostileEntries {
            payload[key] = value
        }

        XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
            let diagnostic = dataCorruptedDescription(error)
            XCTAssertEqual(diagnostic, "FitChefSupportHandoffDescriptor contains unknown key(s)")
            let renderedError = String(describing: error)
            for (key, value) in hostileEntries {
                XCTAssertFalse(diagnostic?.contains(key) == true)
                XCTAssertFalse(diagnostic?.contains(value) == true)
                XCTAssertFalse(renderedError.contains(key))
                XCTAssertFalse(renderedError.contains(value))
            }
        }
    }

    func testHostileNestedUnknownKeysAndSensitiveValuesDoNotEnterDiagnostic() throws {
        let hostileEntries = [
            ("authorization_bearer_secret", "SENSITIVE_NESTED_VALUE_1"),
            ("injected\nheader", "SENSITIVE_NESTED_VALUE_2"),
        ]
        var payload = canonicalPayload()
        var action = try XCTUnwrap(payload["action"] as? [String: Any])
        for (key, value) in hostileEntries {
            action[key] = value
        }
        payload["action"] = action

        XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
            let diagnostic = dataCorruptedDescription(error)
            XCTAssertEqual(diagnostic, "FitChefSupportHandoffAction contains unknown key(s)")
            let renderedError = String(describing: error)
            for (key, value) in hostileEntries {
                XCTAssertFalse(diagnostic?.contains(key) == true)
                XCTAssertFalse(diagnostic?.contains(value) == true)
                XCTAssertFalse(renderedError.contains(key))
                XCTAssertFalse(renderedError.contains(value))
            }
        }
    }

    func testEveryFrozenEnumRejectsUnknownCaseAndWhitespaceVariants() throws {
        let enumFields = [
            (["schema_version"], "fitchef_support_handoff.v1"),
            (["scenario"], "support_handoff"),
            (["support_need"], "daily_structure"),
            (["action", "action_type"], "handoff_to_product_surface"),
            (["action", "target_surface"], "pro_daily_plate"),
            (["wellness_boundary"], "wellness_planning_only"),
        ]

        for (path, canonicalValue) in enumFields {
            let invalidValues = [
                "unsupported_value",
                canonicalValue.uppercased(),
                " \(canonicalValue) ",
            ]

            for invalidValue in invalidValues {
                let payload = replacingValue(
                    in: canonicalPayload(),
                    at: path,
                    with: invalidValue
                )
                XCTAssertThrowsError(
                    try decodeDescriptor(payload),
                    "Expected \(path.joined(separator: "."))=\(invalidValue) to fail"
                )
            }
        }
    }

    func testEveryTypedFieldRejectsWrongTypeAndNull() throws {
        let typedFieldPaths = [
            ["schema_version"],
            ["scenario"],
            ["support_need"],
            ["action"],
            ["action", "action_type"],
            ["action", "target_surface"],
            ["user_confirmation_required"],
            ["execution_authority"],
            ["plan_mutation_authority"],
            ["used_llm"],
            ["wellness_boundary"],
        ]

        for path in typedFieldPaths {
            let wrongType: Any = path == ["action"] ? "not_an_object" : 42
            for invalidValue in [wrongType, NSNull()] {
                let payload = replacingValue(
                    in: canonicalPayload(),
                    at: path,
                    with: invalidValue
                )
                XCTAssertThrowsError(
                    try decodeDescriptor(payload),
                    "Expected \(path.joined(separator: ".")) wrong type/null to fail"
                )
            }
        }
    }

    func testAuthorityBooleansRequireTheirExactFrozenValues() throws {
        let invalidValues: [(String, Bool, String)] = [
            (
                "user_confirmation_required",
                false,
                "user_confirmation_required must be exactly true"
            ),
            ("execution_authority", true, "execution_authority must be exactly false"),
            (
                "plan_mutation_authority",
                true,
                "plan_mutation_authority must be exactly false"
            ),
            ("used_llm", true, "used_llm must be exactly false"),
        ]

        for (field, invalidValue, expectedDescription) in invalidValues {
            let payload = replacingValue(
                in: canonicalPayload(),
                at: [field],
                with: invalidValue
            )

            XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
                XCTAssertEqual(dataCorruptedDescription(error), expectedDescription)
            }
        }
    }

    func testNonObjectRootAndActionAreRejected() throws {
        XCTAssertThrowsError(try decodeDescriptor(fromJSONObject: []))

        let payload = replacingValue(
            in: canonicalPayload(),
            at: ["action"],
            with: ["not", "an", "object"]
        )
        XCTAssertThrowsError(try decodeDescriptor(payload))
    }

    func testKeyOrderDoesNotAffectDecoding() throws {
        let forwardJSON = Data(
            """
            {
              "schema_version": "fitchef_support_handoff.v1",
              "scenario": "support_handoff",
              "support_need": "daily_structure",
              "action": {
                "action_type": "handoff_to_product_surface",
                "target_surface": "pro_daily_plate"
              },
              "user_confirmation_required": true,
              "execution_authority": false,
              "plan_mutation_authority": false,
              "used_llm": false,
              "wellness_boundary": "wellness_planning_only"
            }
            """.utf8
        )
        let reverseJSON = Data(
            """
            {
              "wellness_boundary": "wellness_planning_only",
              "used_llm": false,
              "plan_mutation_authority": false,
              "execution_authority": false,
              "user_confirmation_required": true,
              "action": {
                "target_surface": "pro_daily_plate",
                "action_type": "handoff_to_product_surface"
              },
              "support_need": "daily_structure",
              "scenario": "support_handoff",
              "schema_version": "fitchef_support_handoff.v1"
            }
            """.utf8
        )

        XCTAssertEqual(
            try makeDecoder().decode(FitChefSupportHandoffDescriptor.self, from: forwardJSON),
            try makeDecoder().decode(FitChefSupportHandoffDescriptor.self, from: reverseJSON)
        )
    }

    func testDescriptorIsEquatableAndHashable() throws {
        let daily = try decodeDescriptor(canonicalPayload())
        let equalDaily = try decodeDescriptor(canonicalPayload())
        let weekly = try decodeDescriptor(
            canonicalPayload(
                supportNeed: "weekly_structure",
                targetSurface: "pro_weekly_plan"
            )
        )

        XCTAssertEqual(daily, equalDaily)
        XCTAssertNotEqual(daily, weekly)
        XCTAssertEqual(Set([daily, equalDaily, weekly]).count, 2)
    }

    func testValidatedChoicesAdmitCanonicalSlotsAndPreserveEqualityAndHashing() throws {
        let daily = try decodeDescriptor(canonicalPayload())
        let weekly = try decodeDescriptor(
            canonicalPayload(
                supportNeed: "weekly_structure",
                targetSurface: "pro_weekly_plan"
            )
        )
        let choices = try FitChefSupportHandoffChoices(
            dailyDescriptor: daily,
            weeklyDescriptor: weekly
        )
        let equalChoices = try FitChefSupportHandoffChoices(
            dailyDescriptor: daily,
            weeklyDescriptor: weekly
        )

        XCTAssertEqual(choices.dailyDescriptor, daily)
        XCTAssertEqual(choices.weeklyDescriptor, weekly)
        XCTAssertEqual(choices, equalChoices)
        XCTAssertEqual(Set([choices, equalChoices]).count, 1)
    }

    func testChoicesRejectSwappedRoles() throws {
        let daily = try decodeDescriptor(canonicalPayload())
        let weekly = try decodeDescriptor(
            canonicalPayload(
                supportNeed: "weekly_structure",
                targetSurface: "pro_weekly_plan"
            )
        )

        XCTAssertThrowsError(
            try FitChefSupportHandoffChoices(
                dailyDescriptor: weekly,
                weeklyDescriptor: daily
            )
        ) { error in
            XCTAssertEqual(
                error as? FitChefSupportHandoffChoicesError,
                .invalidSlotAssignment
            )
        }
    }

    func testChoicesRejectDuplicateDailyAndWeeklyDescriptorsDeterministically() throws {
        let daily = try decodeDescriptor(canonicalPayload())
        let weekly = try decodeDescriptor(
            canonicalPayload(
                supportNeed: "weekly_structure",
                targetSurface: "pro_weekly_plan"
            )
        )

        for descriptor in [daily, weekly] {
            XCTAssertThrowsError(
                try FitChefSupportHandoffChoices(
                    dailyDescriptor: descriptor,
                    weeklyDescriptor: descriptor
                )
            ) { error in
                XCTAssertEqual(
                    error as? FitChefSupportHandoffChoicesError,
                    .duplicateDescriptors
                )
            }
        }
    }

    func testSelectionStateStartsEmptySwitchesClearsAndReturnsExactDescriptor() throws {
        let daily = try decodeDescriptor(canonicalPayload())
        let weekly = try decodeDescriptor(
            canonicalPayload(
                supportNeed: "weekly_structure",
                targetSurface: "pro_weekly_plan"
            )
        )
        var state = FitChefSupportChoiceSelectionState()

        XCTAssertNil(state.selectedDescriptor)
        XCTAssertNil(state.confirmationDescriptor)
        XCTAssertFalse(state.canConfirm)

        state.select(daily)
        XCTAssertEqual(state.selectedDescriptor, daily)
        XCTAssertEqual(state.confirmationDescriptor, daily)
        XCTAssertTrue(state.canConfirm)

        state.select(daily)
        XCTAssertEqual(state.confirmationDescriptor, daily)

        state.select(weekly)
        XCTAssertEqual(state.selectedDescriptor, weekly)
        XCTAssertEqual(state.confirmationDescriptor, weekly)
        XCTAssertNotEqual(state.confirmationDescriptor, daily)

        state.clear()
        XCTAssertNil(state.selectedDescriptor)
        XCTAssertNil(state.confirmationDescriptor)
        XCTAssertFalse(state.canConfirm)
    }

    func testSelectionRevalidationPreservesExactMemberOfCurrentChoices() throws {
        let daily = try decodeDescriptor(canonicalPayload())
        let weekly = try decodeDescriptor(
            canonicalPayload(
                supportNeed: "weekly_structure",
                targetSurface: "pro_weekly_plan"
            )
        )
        let choices = try FitChefSupportHandoffChoices(
            dailyDescriptor: daily,
            weeklyDescriptor: weekly
        )
        let equalChoices = try FitChefSupportHandoffChoices(
            dailyDescriptor: try decodeDescriptor(canonicalPayload()),
            weeklyDescriptor: try decodeDescriptor(
                canonicalPayload(
                    supportNeed: "weekly_structure",
                    targetSurface: "pro_weekly_plan"
                )
            )
        )
        var state = FitChefSupportChoiceSelectionState()

        state.select(daily)
        state.revalidate(against: choices)
        XCTAssertEqual(state.confirmationDescriptor, daily)

        state.revalidate(against: equalChoices)
        XCTAssertEqual(state.confirmationDescriptor, daily)

        state.select(weekly)
        state.revalidate(against: equalChoices)
        XCTAssertEqual(state.confirmationDescriptor, weekly)

        state.clear()
        state.revalidate(against: choices)
        XCTAssertNil(state.confirmationDescriptor)
    }

    func testCatalogAndSelectionExposeOnlyClosedConstructionAndSelection() throws {
        let source = try fitChefFoundationSource()
        let catalogStart = try XCTUnwrap(
            source.range(of: "struct FitChefSupportHandoffChoices:")?.lowerBound
        )
        let selectionStart = try XCTUnwrap(
            source.range(of: "struct FitChefSupportChoiceSelectionState:")?.lowerBound
        )
        let codingKeyStart = try XCTUnwrap(
            source.range(of: "private struct FitChefSupportDynamicCodingKey:")?.lowerBound
        )
        let catalogSource = String(source[catalogStart..<selectionStart])
        let selectionSource = String(source[selectionStart..<codingKeyStart])

        XCTAssertEqual(occurrenceCount(of: "init(", in: catalogSource), 1)
        XCTAssertTrue(catalogSource.contains(") throws {"))
        XCTAssertEqual(occurrenceCount(of: "init(", in: selectionSource), 1)
        XCTAssertTrue(selectionSource.contains("init()"))
        XCTAssertTrue(
            selectionSource.contains(
                "mutating func select(_ descriptor: FitChefSupportHandoffDescriptor)"
            )
        )
        XCTAssertTrue(selectionSource.contains("selectedDescriptor = descriptor"))
        XCTAssertTrue(selectionSource.contains("mutating func clear()"))
        XCTAssertTrue(
            selectionSource.contains(
                "mutating func revalidate(against choices: FitChefSupportHandoffChoices)"
            )
        )
        XCTAssertFalse(selectionSource.contains("private let choices"))
        XCTAssertFalse(selectionSource.contains("init(choices:"))
    }

    func testFitChefSupportChoiceLocalizationKeysMatchAndValuesAreFrozen() throws {
        let expectedValues: [String: [String: String]] = [
            "en": [
                "fitchef.support_choice.question":
                    "What kind of structure would help right now?",
                "fitchef.support_choice.daily.title": "Today’s structure",
                "fitchef.support_choice.daily.detail":
                    "A direction for organizing the current day.",
                "fitchef.support_choice.weekly.title": "Week’s structure",
                "fitchef.support_choice.weekly.detail":
                    "A direction for organizing the week.",
                "fitchef.support_choice.agency": "FitChef suggests a direction. You choose.",
                "fitchef.support_choice.consequence":
                    "Confirming only returns your selected direction. Nothing will be opened, saved, or changed.",
                "fitchef.support_choice.wellness":
                    "For wellness planning only — not medical advice.",
                "fitchef.support_choice.confirm": "Confirm direction",
                "fitchef.support_choice.dismiss": "Not now",
            ],
            "ru": [
                "fitchef.support_choice.question": "Какая структура сейчас поможет?",
                "fitchef.support_choice.daily.title": "Структура дня",
                "fitchef.support_choice.daily.detail":
                    "Направление для организации текущего дня.",
                "fitchef.support_choice.weekly.title": "Структура недели",
                "fitchef.support_choice.weekly.detail":
                    "Направление для организации недели.",
                "fitchef.support_choice.agency":
                    "FitChef предлагает направление. Вы выбираете.",
                "fitchef.support_choice.consequence":
                    "Подтверждение только передаст выбранное направление. Ничего не откроется, не сохранится и не изменится.",
                "fitchef.support_choice.wellness":
                    "Только для планирования повседневного благополучия — не медицинская рекомендация.",
                "fitchef.support_choice.confirm": "Подтвердить направление",
                "fitchef.support_choice.dismiss": "Не сейчас",
            ],
            "es": [
                "fitchef.support_choice.question":
                    "¿Qué tipo de estructura te ayudaría ahora?",
                "fitchef.support_choice.daily.title": "Estructura de hoy",
                "fitchef.support_choice.daily.detail":
                    "Una orientación para organizar el día de hoy.",
                "fitchef.support_choice.weekly.title": "Estructura de la semana",
                "fitchef.support_choice.weekly.detail":
                    "Una orientación para organizar la semana.",
                "fitchef.support_choice.agency":
                    "FitChef sugiere una orientación. Tú eliges.",
                "fitchef.support_choice.consequence":
                    "Al confirmar, solo se comunicará la orientación elegida. No se abrirá, guardará ni cambiará nada.",
                "fitchef.support_choice.wellness":
                    "Solo para planificar el bienestar; no es asesoramiento médico.",
                "fitchef.support_choice.confirm": "Confirmar orientación",
                "fitchef.support_choice.dismiss": "Ahora no",
            ],
        ]

        for locale in ["en", "ru", "es"] {
            let localizedValues = try loadFitChefLocalization(locale: locale)
            XCTAssertEqual(Set(localizedValues.keys), localizationKeys)
            XCTAssertTrue(localizedValues.values.allSatisfy { !$0.isEmpty })
            XCTAssertEqual(localizedValues, expectedValues[locale])
        }
    }

    func testFoundationSourceKeepsTheClosedRawWireAndAuthoritySurface() throws {
        let source = try fitChefFoundationSource()

        for rawKey in topLevelFields + ["action_type", "target_surface"] {
            XCTAssertTrue(source.contains("\"\(rawKey)\""), "Missing raw wire key: \(rawKey)")
        }
        XCTAssertFalse(source.contains("Encodable"))
        XCTAssertFalse(source.contains("AnyCodable"))
        XCTAssertFalse(source.contains("URLSession"))
        XCTAssertFalse(source.contains("APIClient"))
        XCTAssertFalse(source.contains("HTTPClient"))
        XCTAssertFalse(source.contains("Navigation"))
        XCTAssertFalse(source.contains("StoreKit"))
        XCTAssertFalse(source.contains("HealthKit"))
        XCTAssertFalse(source.contains("UserDefaults"))
        XCTAssertFalse(source.contains("Keychain"))
        XCTAssertFalse(source.contains("NotificationCenter"))
        XCTAssertFalse(source.contains("Analytics"))
    }

    func testCandidateViewHasNoProductionRegistrationOutsideItsOwnFile() throws {
        let root = try repositoryRoot().appendingPathComponent("ios/PulsePlate")
        let candidatePath = "Views/FitChef/FitChefSupportChoiceExperience.swift"
        let references = try swiftSources(under: root)
            .filter { !$0.path.hasSuffix(candidatePath) }
            .compactMap { url -> String? in
                let source = try String(contentsOf: url, encoding: .utf8)
                return source.contains("FitChefSupportChoiceExperience") ? url.path : nil
            }

        XCTAssertEqual(references, [])
    }

    func testFileSystemSynchronizedTargetsOwnAppAndTestSourcesSeparately() throws {
        let root = try repositoryRoot()
        let projectURL = root.appendingPathComponent(
            "ios/PulsePlate.xcodeproj/project.pbxproj"
        )
        let project = try String(contentsOf: projectURL, encoding: .utf8)

        XCTAssertTrue(
            project.contains(
                "path = PulsePlate; sourceTree = \"<group>\";"
            )
        )
        XCTAssertTrue(
            project.contains(
                "path = PulsePlateTests; sourceTree = \"<group>\";"
            )
        )
        XCTAssertTrue(
            project.contains(
                "fileSystemSynchronizedGroups = (\n\t\t\t\tB6169A352E893CF100B218D8"
            )
        )
        XCTAssertTrue(
            project.contains(
                "fileSystemSynchronizedGroups = (\n\t\t\t\tB6169A892E893CF200B218D8"
            )
        )
        XCTAssertFalse(project.contains("FitChefSupportHandoffDescriptor.swift"))
        XCTAssertFalse(project.contains("FitChefSupportChoiceExperimentTests.swift"))
        XCTAssertFalse(project.contains("FitChefSupportChoiceExperience.swift"))

        let testTargets = try String(
            contentsOf: root.appendingPathComponent("scripts/ios_test_targets.sh"),
            encoding: .utf8
        )
        XCTAssertEqual(
            occurrenceCount(
                of: "PulsePlateTests/FitChefSupportChoiceExperimentTests",
                in: testTargets
            ),
            1
        )
    }

    func testCandidateViewStaticContractWhenCandidateIsPresent() throws {
        guard let source = try fitChefCandidateViewSource() else {
            XCTAssertFalse(
                FileManager.default.fileExists(atPath: try fitChefCandidateViewURL().path)
            )
            return
        }

        let forbiddenFragments = [
            "URLSession",
            "APIClient",
            "HTTPClient",
            "NavigationStack",
            "NavigationLink",
            "openURL",
            "UIApplication.shared",
            "UserDefaults",
            "@AppStorage",
            "Keychain",
            "FileManager",
            "StoreKit",
            "HealthKit",
            "NotificationCenter",
            "Analytics",
            "analytics",
            "provider",
            ".save(",
            ".write(",
        ]
        for fragment in forbiddenFragments {
            XCTAssertFalse(source.contains(fragment), "Forbidden candidate seam: \(fragment)")
        }

        XCTAssertTrue(
            source.contains(
                "FitChefSupportChoiceExperience(choices:onConfirm:onDismiss:)"
            ) || source.contains("struct FitChefSupportChoiceExperience: View")
        )
        XCTAssertTrue(source.contains("@State private var selectionState"))
        XCTAssertTrue(source.contains("FitChefSupportChoiceSelectionState()"))
        XCTAssertTrue(source.contains("selectionState.select(choices.dailyDescriptor)"))
        XCTAssertTrue(source.contains("selectionState.select(choices.weeklyDescriptor)"))
        XCTAssertTrue(source.contains("selectionState.revalidate(against: newChoices)"))
        XCTAssertTrue(source.contains("onConfirm(descriptor)"))
        XCTAssertTrue(source.contains(".disabled(!selectionState.canConfirm)"))
        XCTAssertTrue(source.contains("onDismiss()"))
        XCTAssertTrue(source.contains("PPDesignTokens.Brand.navy"))
        XCTAssertTrue(source.contains("PPCard"))
        XCTAssertTrue(source.contains("PPButton"))
        XCTAssertTrue(source.contains(".frame(maxWidth: 650)"))
        XCTAssertTrue(source.contains("Image(\"FitChef\")"))
        XCTAssertTrue(source.contains(".frame(width: 56, height: 56)"))
        XCTAssertTrue(source.contains(".accessibilityHidden(true)"))
        XCTAssertTrue(source.contains(".accessibilityAddTraits(isSelected ? .isSelected : [])"))
        XCTAssertTrue(source.contains(".accessibilityLabel(Text(\"\\(title). \\(detail)\"))"))
        XCTAssertTrue(source.contains("minHeight: PPAccessibility.minimumTouchTarget"))
        XCTAssertFalse(source.contains("withAnimation"))
        XCTAssertFalse(source.contains(".animation("))

        let scaledMetricDeclarations = [
            "@ScaledMetric(relativeTo: .title2) private var headingFontSize",
            "@ScaledMetric(relativeTo: .body) private var bodyFontSize",
            "@ScaledMetric(relativeTo: .caption) private var captionFontSize",
            "@ScaledMetric(relativeTo: .headline) private var choiceTitleFontSize",
            "@ScaledMetric(relativeTo: .body) private var choiceDetailFontSize",
            "@ScaledMetric(relativeTo: .title3) private var radioSymbolFontSize",
        ]
        XCTAssertEqual(occurrenceCount(of: "@ScaledMetric(", in: source), 6)
        for declaration in scaledMetricDeclarations {
            XCTAssertTrue(source.contains(declaration), "Missing scaled metric: \(declaration)")
        }

        XCTAssertEqual(
            occurrenceCount(
                of: "traits: .fixedLayout(width: 390, height: 844)",
                in: source
            ),
            3
        )
        XCTAssertEqual(
            occurrenceCount(
                of: "traits: .fixedLayout(width: 834, height: 1194)",
                in: source
            ),
            1
        )
        XCTAssertEqual(occurrenceCount(of: ".dynamicTypeSize(.accessibility5)", in: source), 1)
        XCTAssertTrue(source.contains("decoder.keyDecodingStrategy = .useDefaultKeys"))

        let disclosureRegex = try NSRegularExpression(
            pattern: #"if\s+isSelected\s*\{\s*Text\(detail\)"#
        )
        let range = NSRange(source.startIndex..<source.endIndex, in: source)
        XCTAssertLessThanOrEqual(
            disclosureRegex.numberOfMatches(in: source, range: range),
            1
        )
    }

    func testCandidateSemanticDeclarationOrderWhenCandidateIsPresent() throws {
        guard let source = try fitChefCandidateViewSource() else {
            return
        }
        let body = try sourceSlice(
            source,
            from: "var body: some View",
            to: "private var header: some View"
        )
        assertOrdered(
            [
                "header",
                "fitchef.support_choice.daily.title",
                "fitchef.support_choice.weekly.title",
                "boundaryCopy",
                "fitchef.support_choice.confirm",
                "fitchef.support_choice.dismiss",
            ],
            in: body
        )
        let header = try sourceSlice(
            source,
            from: "private var header: some View",
            to: "private var boundaryCopy: some View"
        )
        assertOrdered(
            ["fitchef.support_choice.question", "fitchef.support_choice.agency"],
            in: header
        )
        let boundary = try sourceSlice(
            source,
            from: "private var boundaryCopy: some View",
            to: "private func localized"
        )
        assertOrdered(
            ["fitchef.support_choice.consequence", "fitchef.support_choice.wellness"],
            in: boundary
        )
    }

    private func makeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .useDefaultKeys
        return decoder
    }

    private func canonicalPayload(
        supportNeed: String = "daily_structure",
        targetSurface: String = "pro_daily_plate"
    ) -> [String: Any] {
        [
            "schema_version": "fitchef_support_handoff.v1",
            "scenario": "support_handoff",
            "support_need": supportNeed,
            "action": [
                "action_type": "handoff_to_product_surface",
                "target_surface": targetSurface,
            ],
            "user_confirmation_required": true,
            "execution_authority": false,
            "plan_mutation_authority": false,
            "used_llm": false,
            "wellness_boundary": "wellness_planning_only",
        ]
    }

    private func decodeDescriptor(
        _ payload: [String: Any]
    ) throws -> FitChefSupportHandoffDescriptor {
        try decodeDescriptor(fromJSONObject: payload)
    }

    private func decodeDescriptor(
        fromJSONObject object: Any
    ) throws -> FitChefSupportHandoffDescriptor {
        let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        return try makeDecoder().decode(FitChefSupportHandoffDescriptor.self, from: data)
    }

    private func replacingValue(
        in payload: [String: Any],
        at path: [String],
        with value: Any
    ) -> [String: Any] {
        var result = payload
        if path.count == 1, let field = path.first {
            result[field] = value
            return result
        }

        guard
            path.count == 2,
            let objectField = path.first,
            let nestedField = path.last,
            var object = result[objectField] as? [String: Any]
        else {
            preconditionFailure("Unsupported test fixture path: \(path)")
        }
        object[nestedField] = value
        result[objectField] = object
        return result
    }

    private func dataCorruptedDescription(_ error: Error) -> String? {
        guard case let DecodingError.dataCorrupted(context) = error else {
            return nil
        }
        return context.debugDescription
    }

    private func loadFitChefLocalization(locale: String) throws -> [String: String] {
        let root = try repositoryRoot()
        let url = root
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
            throw FitChefSupportChoiceTestError.invalidLocalizationFile(locale)
        }
        return values.filter { localizationKeys.contains($0.key) }
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

        throw FitChefSupportChoiceTestError.repositoryRootNotFound
    }

    private func fitChefFoundationSource() throws -> String {
        let url = try repositoryRoot()
            .appendingPathComponent(
                "ios/PulsePlate/Models/FitChef/FitChefSupportHandoffDescriptor.swift"
            )
        return try String(contentsOf: url, encoding: .utf8)
    }

    private func fitChefCandidateViewURL() throws -> URL {
        try repositoryRoot().appendingPathComponent(
            "ios/PulsePlate/Views/FitChef/FitChefSupportChoiceExperience.swift"
        )
    }

    private func fitChefCandidateViewSource() throws -> String? {
        let url = try fitChefCandidateViewURL()
        guard FileManager.default.fileExists(atPath: url.path) else {
            return nil
        }
        return try String(contentsOf: url, encoding: .utf8)
    }

    private func swiftSources(under root: URL) throws -> [URL] {
        let resourceKeys: [URLResourceKey] = [.isRegularFileKey]
        guard let enumerator = FileManager.default.enumerator(
            at: root,
            includingPropertiesForKeys: resourceKeys,
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        var sources: [URL] = []
        while let url = enumerator.nextObject() as? URL {
            guard url.pathExtension == "swift" else {
                continue
            }
            let values = try url.resourceValues(forKeys: Set(resourceKeys))
            if values.isRegularFile == true {
                sources.append(url)
            }
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

    private func assertOrdered(
        _ needles: [String],
        in source: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        var searchStart = source.startIndex
        for needle in needles {
            guard let range = source.range(of: needle, range: searchStart..<source.endIndex) else {
                XCTFail("Missing or out-of-order source declaration: \(needle)", file: file, line: line)
                return
            }
            searchStart = range.upperBound
        }
    }

    private func occurrenceCount(of needle: String, in source: String) -> Int {
        source.components(separatedBy: needle).count - 1
    }
}

private enum FitChefSupportChoiceTestError: Error {
    case invalidLocalizationFile(String)
    case repositoryRootNotFound
}
