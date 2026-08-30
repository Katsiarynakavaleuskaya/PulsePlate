import Foundation

protocol FitChefSupportServicing: Sendable {
    func requestHandoff(
        for supportNeed: FitChefSupportNeed,
        apiKey: String
    ) async throws -> FitChefSupportHandoffDescriptor

    func recordOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        apiKey: String
    ) async throws -> FitChefSupportOutcomeReceipt
}

enum FitChefSupportContractError: Error, Equatable, Sendable {
    case invalidHandoffDescriptor
    case responseNeedMismatch
    case invalidOutcomeReceipt
}

final class DefaultFitChefSupportService: FitChefSupportServicing, Sendable {
    private let apiClient: APIClientProtocol

    init(apiClient: APIClientProtocol) {
        self.apiClient = apiClient
    }

    func requestHandoff(
        for supportNeed: FitChefSupportNeed,
        apiKey: String
    ) async throws -> FitChefSupportHandoffDescriptor {
        let response: JSONValue = try await apiClient.post(
            path: "/api/v1/pro/fitchef/recommend",
            body: FitChefSupportHandoffRequest(supportNeed: supportNeed.rawValue),
            headers: ["X-API-Key": apiKey]
        )
        try Task.checkCancellation()

        let descriptor: FitChefSupportHandoffDescriptor
        do {
            descriptor = try Self.recognize(
                response,
                as: FitChefSupportHandoffDescriptor.self
            )
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw FitChefSupportContractError.invalidHandoffDescriptor
        }

        guard descriptor.supportNeed == supportNeed else {
            throw FitChefSupportContractError.responseNeedMismatch
        }
        return descriptor
    }

    func recordOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        apiKey: String
    ) async throws -> FitChefSupportOutcomeReceipt {
        let response: JSONValue = try await apiClient.post(
            path: "/api/v1/pro/fitchef/recommend/outcome",
            body: FitChefSupportOutcomeRequest(
                schemaVersion: "fitchef_support_outcome_v1",
                supportNeed: attempt.supportNeed.rawValue,
                outcome: attempt.outcome.rawValue,
                clientEventID: attempt.clientEventID
            ),
            headers: ["X-API-Key": apiKey]
        )
        try Task.checkCancellation()

        do {
            return try Self.recognize(
                response,
                as: FitChefSupportOutcomeReceipt.self
            )
        } catch is CancellationError {
            throw CancellationError()
        } catch {
            throw FitChefSupportContractError.invalidOutcomeReceipt
        }
    }

    private static func recognize<Value: Decodable>(
        _ response: JSONValue,
        as type: Value.Type
    ) throws -> Value {
        // Duplicate raw JSON member detection is outside this post-transport recognizer.
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(response)

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .useDefaultKeys
        return try decoder.decode(type, from: data)
    }
}

private struct FitChefSupportHandoffRequest: Encodable {
    let supportNeed: String
}

private struct FitChefSupportOutcomeRequest: Encodable {
    let schemaVersion: String
    let supportNeed: String
    let outcome: String
    let clientEventID: String
}
