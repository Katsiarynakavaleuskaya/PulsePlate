import XCTest
import Foundation
@testable import PulsePlate


final class BMIServiceTests: XCTestCase {
    // Test double stores mutable state; safe in tests (single-threaded usage).
    private final class FakeAPIClient: APIClientProtocol, @unchecked Sendable {
        var lastPath: String?
        var lastBody: Any?
        var nextResponseData: Data?
        var nextError: Error?

        func postRaw<Response: Decodable>(
            path: String,
            body: Data,
            headers: [String: String]
        ) async throws -> Response {
            throw APIError.api(statusCode: 500, message: "FakeAPIClient.postRaw not implemented")
        }

        func post<Response: Decodable, Body: Encodable>(
            path: String,
            body: Body,
            headers: [String: String]
        ) async throws -> Response {
            lastPath = path
            lastBody = body

            if let nextError {
                throw nextError
            }
            guard let data = nextResponseData else {
                throw APIError.api(statusCode: 500, message: "FakeAPIClient response not set")
            }
            let decoder = JSONDecoder()
            // Use default keys: Response DTOs define explicit CodingKeys for snake_case fields.
            // Setting `.convertFromSnakeCase` here would break those DTOs (e.g., "group_display").
            decoder.keyDecodingStrategy = .useDefaultKeys
            return try decoder.decode(Response.self, from: data)
        }

        func get<Response: Decodable>(
            path: String,
            headers: [String: String]
        ) async throws -> Response {
            throw APIError.api(statusCode: 500, message: "FakeAPIClient.get not implemented")
        }
    }

    func test_serviceReturnsSuccess() async throws {
        let apiClient = FakeAPIClient()
        apiClient.nextResponseData = BMIFixtures.successJSON()
        let service = BMIService(apiClient: apiClient)

        let request = BMICalculateRequestDTO(weightKg: 70, heightCm: 175, age: 30, lang: "en")
        let response = try await service.calculateBMI(request: request)

        XCTAssertEqual(apiClient.lastPath, "/api/v1/bmi/calculate")
        XCTAssertEqual(response.bmi, 22.86, accuracy: 0.0001)
        XCTAssertEqual(response.group, "general")
        XCTAssertEqual(response.groupDisplay, "General")
    }

    func test_serviceHandles422Validation() async throws {
        let apiClient = FakeAPIClient()
        let validation = try JSONDecoder().decode(ValidationErrorResponse.self, from: BMIFixtures.validation422JSON())
        apiClient.nextError = APIError.validation(validation)
        let service = BMIService(apiClient: apiClient)

        let request = BMICalculateRequestDTO(weightKg: -1, heightCm: 175, age: 30)

        do {
            _ = try await service.calculateBMI(request: request)
            XCTFail("Expected APIError.validation")
        } catch let error as APIError {
            switch error {
            case .validation(let response):
                XCTAssertFalse(response.detail.isEmpty)
                XCTAssertTrue(response.detail.first?.msg.contains("greater than 0") ?? false)
            default:
                XCTFail("Expected validation error, got: \(error)")
            }
        }
    }

    func test_serviceHandles400DomainError() async throws {
        let apiClient = FakeAPIClient()
        apiClient.nextError = APIError.api(statusCode: 400, message: "Bad request")
        let service = BMIService(apiClient: apiClient)

        let request = BMICalculateRequestDTO(weightKg: 70, heightCm: 175, age: 30)

        do {
            _ = try await service.calculateBMI(request: request)
            XCTFail("Expected APIError.api(400)")
        } catch let error as APIError {
            switch error {
            case .api(let statusCode, _):
                XCTAssertEqual(statusCode, 400)
            default:
                XCTFail("Expected http error, got: \(error)")
            }
        }
    }

    func test_serviceWrapsTransportError() async throws {
        let apiClient = FakeAPIClient()
        apiClient.nextError = APIError.api(statusCode: 0, message: "Network offline")
        let service = BMIService(apiClient: apiClient)

        let request = BMICalculateRequestDTO(weightKg: 70, heightCm: 175, age: 30)

        do {
            _ = try await service.calculateBMI(request: request)
            XCTFail("Expected APIError.api(statusCode: 0, ...)")
        } catch let error as APIError {
            if case .api(let statusCode, let message) = error {
                XCTAssertEqual(statusCode, 0)
                XCTAssertFalse(message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                return
            }
            XCTFail("Expected transport error, got: \(error)")
        }
    }

    func test_serviceMapsRequestEncodingError() async throws {
        let apiClient = FakeAPIClient()
        apiClient.nextError = APIError.encodingFailed("Encode failed")
        let service = BMIService(apiClient: apiClient)

        let request = BMICalculateRequestDTO(weightKg: Double.nan, heightCm: 175, age: 30)

        do {
            _ = try await service.calculateBMI(request: request)
            XCTFail("Expected APIError.encodingFailed")
        } catch let error as APIError {
            switch error {
            case .encodingFailed(let message):
                XCTAssertFalse(message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            default:
                XCTFail("Expected encoding error, got: \(error)")
            }
        }
    }
}
