import Testing
import Foundation
@testable import PulsePlate

struct WeeklyPlanServiceTransportTests {
    @Test func service_wrapsTransportError() async throws {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [FailingURLProtocol.self]
        let session = URLSession(configuration: config)

        let service = DefaultWeeklyPlanService(
            baseURL: URL(string: "https://example.com")!,
            session: session
        )

        let request = WeeklyPlanRequest(
            endpointPath: "/api/v1/pro/meal/weekly",
            body: Data(),
            apiKey: nil
        )

        do {
            _ = try await service.fetchWeeklyPlan(request: request)
            Issue.record("Expected WeeklyPlanServiceError.transport")
        } catch let error as WeeklyPlanServiceError {
            switch error {
            case .transport(let message):
                #expect(!message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            default:
                Issue.record("Expected transport error, got: \(error)")
            }
        } catch {
            Issue.record("Expected WeeklyPlanServiceError, got: \(error)")
        }
    }

    @Test func service_wrapsURLError() async throws {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [TimeoutURLProtocol.self]
        let session = URLSession(configuration: config)

        let service = DefaultWeeklyPlanService(
            baseURL: URL(string: "https://example.com")!,
            session: session
        )

        let request = WeeklyPlanRequest(
            endpointPath: "/api/v1/pro/meal/weekly",
            body: Data(),
            apiKey: nil
        )

        do {
            _ = try await service.fetchWeeklyPlan(request: request)
            Issue.record("Expected WeeklyPlanServiceError.transport for timeout")
        } catch let error as WeeklyPlanServiceError {
            switch error {
            case .transport(let message):
                // Timeout error should have descriptive message
                #expect(!message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            default:
                Issue.record("Expected transport error for timeout, got: \(error)")
            }
        } catch {
            Issue.record("Expected WeeklyPlanServiceError, got: \(error)")
        }
    }
}

// MARK: - Test URLProtocols

private final class FailingURLProtocol: URLProtocol {
    override static func canInit(with request: URLRequest) -> Bool { true }
    override static func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        client?.urlProtocol(self, didFailWithError: URLError(.notConnectedToInternet))
    }
    override func stopLoading() {}
}

final class TimeoutURLProtocol: URLProtocol {
    override static func canInit(with request: URLRequest) -> Bool { true }
    override static func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        client?.urlProtocol(self, didFailWithError: URLError(.timedOut))
    }
    override func stopLoading() {}
}
