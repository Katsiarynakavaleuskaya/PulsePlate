import Foundation
import XCTest
@testable import PulsePlate

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
                        "supportNeed and action.targetSurface must form a compatible handoff pair"
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

    func testUnknownSemanticTopLevelKeysAreRejectedInStableSortedOrder() throws {
        var payload = canonicalPayload()
        payload["z_extra"] = true
        payload["a_extra"] = true

        XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
            XCTAssertEqual(
                dataCorruptedDescription(error),
                "FitChefSupportHandoffDescriptor contains unknown keys: aExtra, zExtra"
            )
        }
    }

    func testUnknownSemanticActionKeysAreRejectedInStableSortedOrder() throws {
        var payload = canonicalPayload()
        var action = try XCTUnwrap(payload["action"] as? [String: Any])
        action["z_extra"] = true
        action["a_extra"] = true
        payload["action"] = action

        XCTAssertThrowsError(try decodeDescriptor(payload)) { error in
            XCTAssertEqual(
                dataCorruptedDescription(error),
                "FitChefSupportHandoffAction contains unknown keys: aExtra, zExtra"
            )
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
                "userConfirmationRequired must be exactly true"
            ),
            ("execution_authority", true, "executionAuthority must be exactly false"),
            (
                "plan_mutation_authority",
                true,
                "planMutationAuthority must be exactly false"
            ),
            ("used_llm", true, "usedLlm must be exactly false"),
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

    func testSelectionStateStartsEmptyAndReturnsTheExactSelectedDescriptor() throws {
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

    private func makeDecoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
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
}

private enum FitChefSupportChoiceTestError: Error {
    case invalidLocalizationFile(String)
    case repositoryRootNotFound
}
