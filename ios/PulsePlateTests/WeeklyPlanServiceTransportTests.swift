import Testing
import Foundation
@testable import PulsePlate

struct WeeklyPlanServiceTransportTests {
    @Test func service_wrapsTransportError() async throws {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [FailingURLProtocol.self]
        let session = URLSession(configuration: config)
        let httpClient = HTTPClient(session: session)
        let apiClient = APIClient(baseURL: URL(string: "https://example.com")!, httpClient: httpClient)

        let service = DefaultWeeklyPlanService(apiClient: apiClient)

        let request = WeeklyPlanRequest(
            endpointPath: "/api/v1/pro/meal/weekly",
            body: Data(),
            apiKey: nil
        )

        do {
            _ = try await service.fetchWeeklyPlan(request: request)
            Issue.record("Expected APIError for transport failure")
        } catch let error as APIError {
            // For URLSession failures we surface APIError.api with best-effort message.
            #expect(error.localizedDescription.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false)
        } catch {
            Issue.record("Expected APIError, got: \(error)")
        }
    }

    @Test func service_wrapsURLError() async throws {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [TimeoutURLProtocol.self]
        let session = URLSession(configuration: config)
        let httpClient = HTTPClient(session: session)
        let apiClient = APIClient(baseURL: URL(string: "https://example.com")!, httpClient: httpClient)

        let service = DefaultWeeklyPlanService(apiClient: apiClient)

        let request = WeeklyPlanRequest(
            endpointPath: "/api/v1/pro/meal/weekly",
            body: Data(),
            apiKey: nil
        )

        do {
            _ = try await service.fetchWeeklyPlan(request: request)
            Issue.record("Expected APIError for timeout")
        } catch let error as APIError {
            #expect(error.localizedDescription.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false)
        } catch {
            Issue.record("Expected APIError, got: \(error)")
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

private final class TimeoutURLProtocol: URLProtocol {
    override static func canInit(with request: URLRequest) -> Bool { true }
    override static func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        client?.urlProtocol(self, didFailWithError: URLError(.timedOut))
    }
    override func stopLoading() {}
}
