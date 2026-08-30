import Foundation

enum FitChefSupportHandoffSchemaVersion: String, Decodable, Equatable, Hashable, Sendable {
    case v1 = "fitchef_support_handoff.v1"
}

enum FitChefSupportHandoffScenario: String, Decodable, Equatable, Hashable, Sendable {
    case supportHandoff = "support_handoff"
}

enum FitChefSupportNeed: String, Decodable, Equatable, Hashable, Sendable {
    case dailyStructure = "daily_structure"
    case weeklyStructure = "weekly_structure"
}

enum FitChefSupportHandoffActionType: String, Decodable, Equatable, Hashable, Sendable {
    case handoffToProductSurface = "handoff_to_product_surface"
}

enum FitChefSupportTargetSurface: String, Decodable, Equatable, Hashable, Sendable {
    case proDailyPlate = "pro_daily_plate"
    case proWeeklyPlan = "pro_weekly_plan"
}

enum FitChefSupportHandoffWellnessBoundary: String, Decodable, Equatable, Hashable, Sendable {
    case wellnessPlanningOnly = "wellness_planning_only"
}

struct FitChefSupportHandoffAction: Decodable, Equatable, Hashable, Sendable {
    let actionType: FitChefSupportHandoffActionType
    let targetSurface: FitChefSupportTargetSurface

    private static let allowedKeys: Set<String> = [
        "action_type",
        "target_surface",
    ]

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: FitChefSupportDynamicCodingKey.self)
        try rejectUnknownFitChefSupportKeys(
            in: container,
            allowedKeys: Self.allowedKeys,
            objectName: "FitChefSupportHandoffAction"
        )

        actionType = try container.decode(
            FitChefSupportHandoffActionType.self,
            forKey: FitChefSupportDynamicCodingKey("action_type")
        )
        targetSurface = try container.decode(
            FitChefSupportTargetSurface.self,
            forKey: FitChefSupportDynamicCodingKey("target_surface")
        )
    }
}

struct FitChefSupportHandoffDescriptor: Decodable, Equatable, Hashable, Sendable {
    let schemaVersion: FitChefSupportHandoffSchemaVersion
    let scenario: FitChefSupportHandoffScenario
    let supportNeed: FitChefSupportNeed
    let action: FitChefSupportHandoffAction
    let userConfirmationRequired: Bool
    let executionAuthority: Bool
    let planMutationAuthority: Bool
    let usedLlm: Bool
    let wellnessBoundary: FitChefSupportHandoffWellnessBoundary

    private static let allowedKeys: Set<String> = [
        "action",
        "execution_authority",
        "plan_mutation_authority",
        "scenario",
        "schema_version",
        "support_need",
        "used_llm",
        "user_confirmation_required",
        "wellness_boundary",
    ]

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: FitChefSupportDynamicCodingKey.self)
        try rejectUnknownFitChefSupportKeys(
            in: container,
            allowedKeys: Self.allowedKeys,
            objectName: "FitChefSupportHandoffDescriptor"
        )

        schemaVersion = try container.decode(
            FitChefSupportHandoffSchemaVersion.self,
            forKey: FitChefSupportDynamicCodingKey("schema_version")
        )
        scenario = try container.decode(
            FitChefSupportHandoffScenario.self,
            forKey: FitChefSupportDynamicCodingKey("scenario")
        )
        supportNeed = try container.decode(
            FitChefSupportNeed.self,
            forKey: FitChefSupportDynamicCodingKey("support_need")
        )
        action = try container.decode(
            FitChefSupportHandoffAction.self,
            forKey: FitChefSupportDynamicCodingKey("action")
        )
        userConfirmationRequired = try container.decode(
            Bool.self,
            forKey: FitChefSupportDynamicCodingKey("user_confirmation_required")
        )
        executionAuthority = try container.decode(
            Bool.self,
            forKey: FitChefSupportDynamicCodingKey("execution_authority")
        )
        planMutationAuthority = try container.decode(
            Bool.self,
            forKey: FitChefSupportDynamicCodingKey("plan_mutation_authority")
        )
        usedLlm = try container.decode(
            Bool.self,
            forKey: FitChefSupportDynamicCodingKey("used_llm")
        )
        wellnessBoundary = try container.decode(
            FitChefSupportHandoffWellnessBoundary.self,
            forKey: FitChefSupportDynamicCodingKey("wellness_boundary")
        )

        guard userConfirmationRequired else {
            throw fitChefSupportDataCorrupted(
                "user_confirmation_required must be exactly true",
                codingPath: container.codingPath
                    + [FitChefSupportDynamicCodingKey("user_confirmation_required")]
            )
        }
        guard !executionAuthority else {
            throw fitChefSupportDataCorrupted(
                "execution_authority must be exactly false",
                codingPath: container.codingPath
                    + [FitChefSupportDynamicCodingKey("execution_authority")]
            )
        }
        guard !planMutationAuthority else {
            throw fitChefSupportDataCorrupted(
                "plan_mutation_authority must be exactly false",
                codingPath: container.codingPath
                    + [FitChefSupportDynamicCodingKey("plan_mutation_authority")]
            )
        }
        guard !usedLlm else {
            throw fitChefSupportDataCorrupted(
                "used_llm must be exactly false",
                codingPath: container.codingPath + [FitChefSupportDynamicCodingKey("used_llm")]
            )
        }

        let pair = (supportNeed, action.targetSurface)
        let isCompatible = pair == (.dailyStructure, .proDailyPlate)
            || pair == (.weeklyStructure, .proWeeklyPlan)
        guard isCompatible else {
            throw fitChefSupportDataCorrupted(
                "support_need and action.target_surface must form a compatible handoff pair",
                codingPath: container.codingPath
            )
        }
    }
}

struct FitChefSupportChoiceSelectionState: Equatable, Sendable {
    private(set) var selectedNeed: FitChefSupportNeed?

    init() {
        selectedNeed = nil
    }

    mutating func select(_ need: FitChefSupportNeed) {
        selectedNeed = need
    }

    mutating func clear() {
        selectedNeed = nil
    }

    var canConfirm: Bool {
        selectedNeed != nil
    }

    var confirmationNeed: FitChefSupportNeed? {
        selectedNeed
    }
}

private struct FitChefSupportDynamicCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int? = nil

    init(_ stringValue: String) {
        self.stringValue = stringValue
    }

    init?(stringValue: String) {
        self.init(stringValue)
    }

    init?(intValue: Int) {
        return nil
    }
}

private func rejectUnknownFitChefSupportKeys(
    in container: KeyedDecodingContainer<FitChefSupportDynamicCodingKey>,
    allowedKeys: Set<String>,
    objectName: String
) throws {
    let containsUnknownKey = container.allKeys.contains {
        !allowedKeys.contains($0.stringValue)
    }

    guard !containsUnknownKey else {
        throw fitChefSupportDataCorrupted(
            "\(objectName) contains unknown key(s)",
            codingPath: container.codingPath
        )
    }
}

private func fitChefSupportDataCorrupted(
    _ description: String,
    codingPath: [any CodingKey]
) -> DecodingError {
    .dataCorrupted(
        DecodingError.Context(
            codingPath: codingPath,
            debugDescription: description
        )
    )
}

enum FitChefSupportOutcome: String, Equatable, Hashable, Sendable {
    case acknowledged
    case dismissed
}

enum FitChefSupportOutcomeState: String, Decodable, Equatable, Hashable, Sendable {
    case recorded
    case replayed
}

struct FitChefSupportOutcomeAttempt: Equatable, Hashable, Sendable {
    let supportNeed: FitChefSupportNeed
    let outcome: FitChefSupportOutcome
    let clientEventID: String
}

struct FitChefSupportOutcomeReceipt: Decodable, Equatable, Hashable, Sendable {
    let state: FitChefSupportOutcomeState

    private static let allowedKeys: Set<String> = [
        "schema_version",
        "state",
    ]

    init(state: FitChefSupportOutcomeState) {
        self.state = state
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: FitChefSupportDynamicCodingKey.self)
        try rejectUnknownFitChefSupportKeys(
            in: container,
            allowedKeys: Self.allowedKeys,
            objectName: "FitChefSupportOutcomeReceipt"
        )

        let schemaVersion = try container.decode(
            String.self,
            forKey: FitChefSupportDynamicCodingKey("schema_version")
        )
        guard schemaVersion == "fitchef_support_outcome_v1" else {
            throw fitChefSupportDataCorrupted(
                "schema_version must be exactly fitchef_support_outcome_v1",
                codingPath: container.codingPath
                    + [FitChefSupportDynamicCodingKey("schema_version")]
            )
        }
        state = try container.decode(
            FitChefSupportOutcomeState.self,
            forKey: FitChefSupportDynamicCodingKey("state")
        )
    }
}
