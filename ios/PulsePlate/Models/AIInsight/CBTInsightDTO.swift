import Foundation

public struct CBTInsightRequestDTO: Encodable, Sendable, Equatable {
    public let query: String

    public init(query: String) {
        self.query = query
    }
}

public struct CBTInsightSourceDTO: Codable, Sendable, Equatable, Identifiable {
    public let chunkId: String
    public let file: String
    public let preview: String
    public let score: Double

    public var id: String { chunkId }

    public init(chunkId: String, file: String, preview: String, score: Double) {
        self.chunkId = chunkId
        self.file = file
        self.preview = preview
        self.score = score
    }
}

public struct CBTInsightResponseDTO: Codable, Sendable, Equatable {
    public let insight: String
    public let ragUsed: Bool
    public let sources: [CBTInsightSourceDTO]
    public let confidence: Double
    public let uncertainty: Double
    public let warnings: [String]
    public let mode: String
    public let quotaState: String

    public init(
        insight: String,
        ragUsed: Bool,
        sources: [CBTInsightSourceDTO],
        confidence: Double,
        uncertainty: Double,
        warnings: [String],
        mode: String,
        quotaState: String
    ) {
        self.insight = insight
        self.ragUsed = ragUsed
        self.sources = sources
        self.confidence = confidence
        self.uncertainty = uncertainty
        self.warnings = warnings
        self.mode = mode
        self.quotaState = quotaState
    }
}
