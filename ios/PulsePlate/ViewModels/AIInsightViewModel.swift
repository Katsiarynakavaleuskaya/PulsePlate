import Foundation
import Observation

public enum AIInsightState: Equatable {
    case idle
    case loading
    case loaded(CBTInsightResponseDTO)
    case failed(String)

    public var isLoading: Bool {
        if case .loading = self { return true }
        return false
    }
}

@MainActor
@Observable
public final class AIInsightViewModel {
    static let maxQueryLength = 500

    public var query: String = ""
    public private(set) var state: AIInsightState = .idle

    private let service: CBTInsightServicing
    private let apiKeyProvider: @Sendable () -> String?
    private var submitTask: Task<Void, Never>?

    init(
        service: CBTInsightServicing,
        apiKeyProvider: @escaping @Sendable () -> String? = { nil }
    ) {
        self.service = service
        self.apiKeyProvider = apiKeyProvider
    }

    public var canSubmit: Bool {
        !trimmedQuery.isEmpty && trimmedQuery.count <= Self.maxQueryLength && !state.isLoading
    }

    public func enforceQueryLimit() {
        if query.count > Self.maxQueryLength {
            query = String(query.prefix(Self.maxQueryLength))
        }
    }

    public func submit() {
        let query = trimmedQuery
        guard !query.isEmpty else {
            state = .failed(localized("ai_insight.error.empty_query"))
            return
        }
        guard query.count <= Self.maxQueryLength else {
            state = .failed(
                String(
                    format: localized("ai_insight.error.query_too_long"),
                    Self.maxQueryLength
                )
            )
            return
        }

        guard let apiKey = apiKeyProvider(), !apiKey.isEmpty else {
            state = .failed(localized("ai_insight.error.missing_key"))
            return
        }

        submitTask?.cancel()
        state = .loading

        submitTask = Task { [weak self] in
            guard let self else { return }
            await self._submit(query: query, apiKey: apiKey)
        }
    }

    public func retry() {
        submit()
    }

    private func _submit(query: String, apiKey: String) async {
        do {
            try Task.checkCancellation()
            let response = try await service.fetchInsight(query: query, apiKey: apiKey)
            try Task.checkCancellation()
            state = .loaded(response)
        } catch is CancellationError {
            return
        } catch let error as APIError {
            state = .failed(Self.userFacingMessage(for: error))
        } catch {
            state = .failed(localized("ai_insight.error.unknown_generic"))
        }
    }

    private var trimmedQuery: String {
        query.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func localized(_ key: String) -> String {
        NSLocalizedString(key, comment: "")
    }

    private static func userFacingMessage(for error: APIError) -> String {
        switch error {
        case .validation:
            return NSLocalizedString("ai_insight.error.validation_generic", comment: "")
        case .api(let statusCode, _):
            switch statusCode {
            case 401:
                return NSLocalizedString("ai_insight.error.unauthorized", comment: "")
            case 403:
                return NSLocalizedString("ai_insight.error.forbidden", comment: "")
            case 429:
                return NSLocalizedString("ai_insight.error.quota_exceeded", comment: "")
            case 503:
                return NSLocalizedString("ai_insight.error.unavailable", comment: "")
            case 504:
                return NSLocalizedString("ai_insight.error.timeout", comment: "")
            default:
                return String(
                    format: NSLocalizedString("ai_insight.error.api_format", comment: ""),
                    statusCode
                )
            }
        case .transport:
            return NSLocalizedString("ai_insight.error.transport_generic", comment: "")
        case .decodingFailed:
            return NSLocalizedString("ai_insight.error.decoding_generic", comment: "")
        case .emptyResponse:
            return NSLocalizedString("ai_insight.error.empty_response", comment: "")
        default:
            return NSLocalizedString("ai_insight.error.unknown_generic", comment: "")
        }
    }
}
