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
        "actionType",
        "targetSurface",
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
            forKey: FitChefSupportDynamicCodingKey("actionType")
        )
        targetSurface = try container.decode(
            FitChefSupportTargetSurface.self,
            forKey: FitChefSupportDynamicCodingKey("targetSurface")
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
        "executionAuthority",
        "planMutationAuthority",
        "scenario",
        "schemaVersion",
        "supportNeed",
        "usedLlm",
        "userConfirmationRequired",
        "wellnessBoundary",
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
            forKey: FitChefSupportDynamicCodingKey("schemaVersion")
        )
        scenario = try container.decode(
            FitChefSupportHandoffScenario.self,
            forKey: FitChefSupportDynamicCodingKey("scenario")
        )
        supportNeed = try container.decode(
            FitChefSupportNeed.self,
            forKey: FitChefSupportDynamicCodingKey("supportNeed")
        )
        action = try container.decode(
            FitChefSupportHandoffAction.self,
            forKey: FitChefSupportDynamicCodingKey("action")
        )
        userConfirmationRequired = try container.decode(
            Bool.self,
            forKey: FitChefSupportDynamicCodingKey("userConfirmationRequired")
        )
        executionAuthority = try container.decode(
            Bool.self,
            forKey: FitChefSupportDynamicCodingKey("executionAuthority")
        )
        planMutationAuthority = try container.decode(
            Bool.self,
            forKey: FitChefSupportDynamicCodingKey("planMutationAuthority")
        )
        usedLlm = try container.decode(
            Bool.self,
            forKey: FitChefSupportDynamicCodingKey("usedLlm")
        )
        wellnessBoundary = try container.decode(
            FitChefSupportHandoffWellnessBoundary.self,
            forKey: FitChefSupportDynamicCodingKey("wellnessBoundary")
        )

        guard userConfirmationRequired else {
            throw fitChefSupportDataCorrupted(
                "userConfirmationRequired must be exactly true",
                codingPath: container.codingPath
                    + [FitChefSupportDynamicCodingKey("userConfirmationRequired")]
            )
        }
        guard !executionAuthority else {
            throw fitChefSupportDataCorrupted(
                "executionAuthority must be exactly false",
                codingPath: container.codingPath
                    + [FitChefSupportDynamicCodingKey("executionAuthority")]
            )
        }
        guard !planMutationAuthority else {
            throw fitChefSupportDataCorrupted(
                "planMutationAuthority must be exactly false",
                codingPath: container.codingPath
                    + [FitChefSupportDynamicCodingKey("planMutationAuthority")]
            )
        }
        guard !usedLlm else {
            throw fitChefSupportDataCorrupted(
                "usedLlm must be exactly false",
                codingPath: container.codingPath + [FitChefSupportDynamicCodingKey("usedLlm")]
            )
        }

        let pair = (supportNeed, action.targetSurface)
        let isCompatible = pair == (.dailyStructure, .proDailyPlate)
            || pair == (.weeklyStructure, .proWeeklyPlan)
        guard isCompatible else {
            throw fitChefSupportDataCorrupted(
                "supportNeed and action.targetSurface must form a compatible handoff pair",
                codingPath: container.codingPath
            )
        }
    }
}

enum FitChefSupportHandoffChoicesError: Error, Equatable, Sendable {
    case duplicateDescriptors
    case invalidSlotAssignment
}

struct FitChefSupportHandoffChoices: Equatable, Hashable, Sendable {
    let dailyDescriptor: FitChefSupportHandoffDescriptor
    let weeklyDescriptor: FitChefSupportHandoffDescriptor

    init(
        dailyDescriptor: FitChefSupportHandoffDescriptor,
        weeklyDescriptor: FitChefSupportHandoffDescriptor
    ) throws {
        guard dailyDescriptor != weeklyDescriptor else {
            throw FitChefSupportHandoffChoicesError.duplicateDescriptors
        }

        let dailySlotIsValid = dailyDescriptor.supportNeed == .dailyStructure
            && dailyDescriptor.action.targetSurface == .proDailyPlate
        let weeklySlotIsValid = weeklyDescriptor.supportNeed == .weeklyStructure
            && weeklyDescriptor.action.targetSurface == .proWeeklyPlan
        guard dailySlotIsValid, weeklySlotIsValid else {
            throw FitChefSupportHandoffChoicesError.invalidSlotAssignment
        }

        self.dailyDescriptor = dailyDescriptor
        self.weeklyDescriptor = weeklyDescriptor
    }

    func descriptor(for supportNeed: FitChefSupportNeed) -> FitChefSupportHandoffDescriptor {
        switch supportNeed {
        case .dailyStructure:
            return dailyDescriptor
        case .weeklyStructure:
            return weeklyDescriptor
        }
    }
}

struct FitChefSupportChoiceSelectionState: Equatable, Sendable {
    private let choices: FitChefSupportHandoffChoices
    private(set) var selectedDescriptor: FitChefSupportHandoffDescriptor?

    init(choices: FitChefSupportHandoffChoices) {
        self.choices = choices
        selectedDescriptor = nil
    }

    mutating func select(_ supportNeed: FitChefSupportNeed) {
        selectedDescriptor = choices.descriptor(for: supportNeed)
    }

    var canConfirm: Bool {
        selectedDescriptor != nil
    }

    var confirmationDescriptor: FitChefSupportHandoffDescriptor? {
        selectedDescriptor
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
    let unknownKeys = container.allKeys
        .map(\.stringValue)
        .filter { !allowedKeys.contains($0) }
        .sorted()

    guard unknownKeys.isEmpty else {
        throw fitChefSupportDataCorrupted(
            "\(objectName) contains unknown keys: \(unknownKeys.joined(separator: ", "))",
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
