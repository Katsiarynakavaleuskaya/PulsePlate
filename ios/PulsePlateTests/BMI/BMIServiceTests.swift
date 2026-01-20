import Testing
import Foundation
@testable import PulsePlate

struct BMIServiceTests {
    @Test func service_returnsSuccess() async throws {
        MockURLProtocol.reset() // Clean state before test

        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        let session = URLSession(configuration: config)

        // Set up mock response
        MockURLProtocol.responseData = BMIFixtures.successJSON()
        MockURLProtocol.responseStatusCode = 200

        let service = DefaultBMIService(
            baseURL: URL(string: "https://example.com")!,
            session: session
        )

        let request = BMIRequest(weightKg: 70, heightCm: 175, age: 30, lang: "en")
        let response = try await service.calculateBMI(request: request)

        #expect(response.bmi == 22.86)
        #expect(response.group == "general")
        #expect(response.groupDisplay == "General")
    }

    @Test func service_handles422Validation() async throws {
        MockURLProtocol.reset() // Clean state before test

        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        let session = URLSession(configuration: config)

        MockURLProtocol.responseData = BMIFixtures.validation422JSON()
        MockURLProtocol.responseStatusCode = 422

        let service = DefaultBMIService(
            baseURL: URL(string: "https://example.com")!,
            session: session
        )

        let request = BMIRequest(weightKg: -1, heightCm: 175, age: 30)

        do {
            _ = try await service.calculateBMI(request: request)
            Issue.record("Expected BMIServiceError.validation")
        } catch let error as BMIServiceError {
            switch error {
            case .validation(let errors):
                #expect(!errors.isEmpty)
                #expect(errors[0].msg.contains("greater than 0"))
            default:
                Issue.record("Expected validation error, got: \(error)")
            }
        } catch {
            Issue.record("Expected BMIServiceError, got: \(error)")
        }
    }

    @Test func service_handles400DomainError() async throws {
        MockURLProtocol.reset() // Clean state before test

        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        let session = URLSession(configuration: config)

        MockURLProtocol.responseData = BMIFixtures.error400JSON()
        MockURLProtocol.responseStatusCode = 400

        let service = DefaultBMIService(
            baseURL: URL(string: "https://example.com")!,
            session: session
        )

        let request = BMIRequest(weightKg: 70, heightCm: 175, age: 30)

        do {
            _ = try await service.calculateBMI(request: request)
            Issue.record("Expected BMIServiceError.http(400)")
        } catch let error as BMIServiceError {
            switch error {
            case .http(let code, _):
                #expect(code == 400)
            default:
                Issue.record("Expected http error, got: \(error)")
            }
        } catch {
            Issue.record("Expected BMIServiceError, got: \(error)")
        }
    }

    @Test func service_wrapsTransportError() async throws {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [FailingURLProtocol.self]
        let session = URLSession(configuration: config)

        let service = DefaultBMIService(
            baseURL: URL(string: "https://example.com")!,
            session: session
        )

        let request = BMIRequest(weightKg: 70, heightCm: 175, age: 30)

        do {
            _ = try await service.calculateBMI(request: request)
            Issue.record("Expected BMIServiceError.transport")
        } catch let error as BMIServiceError {
            switch error {
            case .transport(let message):
                #expect(!message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            default:
                Issue.record("Expected transport error, got: \(error)")
            }
        } catch {
            Issue.record("Expected BMIServiceError, got: \(error)")
        }
    }
}

// MARK: - Test URLProtocols

/// Mock URLProtocol for successful responses (200 OK with JSON data)
final class MockURLProtocol: URLProtocol {
    static var responseData: Data?
    static var responseStatusCode: Int = 200

    override static func canInit(with request: URLRequest) -> Bool { true }
    override static func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let client = client else { return }

        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: Self.responseStatusCode,
            httpVersion: "HTTP/1.1",
            headerFields: ["Content-Type": "application/json"]
        )!

        client.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)

        if let data = Self.responseData {
            client.urlProtocol(self, didLoad: data)
        }

        client.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}

    // Reset mock state after each test
    static func reset() {
        responseData = nil
        responseStatusCode = 200
    }
}
