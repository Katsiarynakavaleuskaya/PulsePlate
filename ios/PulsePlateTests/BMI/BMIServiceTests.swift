import XCTest
import Foundation
@testable import PulsePlate


final class BMIServiceTests: XCTestCase {
    func test_serviceReturnsSuccess() async throws {
        MockURLProtocol.reset()

        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        let session = URLSession(configuration: config)

        MockURLProtocol.responseData = BMIFixtures.successJSON()
        MockURLProtocol.responseStatusCode = 200

        let service = DefaultBMIService(
            baseURL: URL(string: "https://example.com")!,
            session: session
        )

        let request = BMIRequest(weightKg: 70, heightCm: 175, age: 30, lang: "en")
        let response = try await service.calculateBMI(request: request)

        XCTAssertEqual(response.bmi, 22.86, accuracy: 0.0001)
        XCTAssertEqual(response.group, "general")
        XCTAssertEqual(response.groupDisplay, "General")
    }

    func test_serviceHandles422Validation() async throws {
        MockURLProtocol.reset()

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
            XCTFail("Expected BMIServiceError.validation")
        } catch let error as BMIServiceError {
            switch error {
            case .validation(let errors):
                XCTAssertFalse(errors.isEmpty)
                XCTAssertTrue(errors.first?.msg.contains("greater than 0") ?? false)
            default:
                XCTFail("Expected validation error, got: \(error)")
            }
        }
    }

    func test_serviceHandles400DomainError() async throws {
        MockURLProtocol.reset()

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
            XCTFail("Expected BMIServiceError.http(400)")
        } catch let error as BMIServiceError {
            switch error {
            case .http(let code, _):
                XCTAssertEqual(code, 400)
            default:
                XCTFail("Expected http error, got: \(error)")
            }
        }
    }

    func test_serviceWrapsTransportError() async throws {
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
            XCTFail("Expected BMIServiceError.transport")
        } catch let error as BMIServiceError {
            switch error {
            case .transport(let message):
                XCTAssertFalse(message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            default:
                XCTFail("Expected transport error, got: \(error)")
            }
        }
    }

    func test_serviceMapsRequestEncodingError() async throws {
        let service = DefaultBMIService(
            baseURL: URL(string: "https://example.com")!,
            session: URLSession(configuration: .ephemeral)
        )

        let request = BMIRequest(weightKg: Double.nan, heightCm: 175, age: 30)

        do {
            _ = try await service.calculateBMI(request: request)
            XCTFail("Expected BMIServiceError.encoding")
        } catch let error as BMIServiceError {
            switch error {
            case .encoding(let message):
                XCTAssertFalse(message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            default:
                XCTFail("Expected encoding error, got: \(error)")
            }
        }
    }
}

// MARK: - Test URLProtocols

final class MockURLProtocol: URLProtocol {
    static var responseData: Data?
    static var responseStatusCode: Int = 200

    override static func canInit(with request: URLRequest) -> Bool { true }
    override static func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let client else { return }

        guard let url = request.url else {
            client.urlProtocol(self, didFailWithError: URLError(.badURL))
            return
        }

        let response = HTTPURLResponse(
            url: url,
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

    static func reset() {
        responseData = nil
        responseStatusCode = 200
    }
}

private final class FailingURLProtocol: URLProtocol {
    override static func canInit(with request: URLRequest) -> Bool { true }
    override static func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        client?.urlProtocol(self, didFailWithError: URLError(.notConnectedToInternet))
    }

    override func stopLoading() {}
}
