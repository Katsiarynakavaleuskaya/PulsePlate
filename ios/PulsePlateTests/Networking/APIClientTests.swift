import XCTest
@testable import PulsePlate

final class APIClientTests: XCTestCase {

    // Test double stores mutable state; safe in tests (single-threaded usage).
    fileprivate final class CapturingHTTPClient: HTTPClientProtocol, @unchecked Sendable {
        var lastRequest: URLRequest?

        func send<T: Decodable>(
            _ request: URLRequest,
            responseType: T.Type
        ) async throws -> T {
            lastRequest = request
            // Return dummy by decoding empty JSON object
            // For empty structs, we need at least one field or use a workaround
            // This is a test helper - in real tests we'd use proper response types
            let data = "{}".data(using: .utf8)!
            // Note: Empty struct {} can decode if T has no required fields
            // If decoding fails, the test will catch it
            return try JSONDecoder().decode(T.self, from: data)
        }
    }

    func test_post_buildsCorrectURLAndHeadersAndBody() async throws {
        let http = CapturingHTTPClient()
        let api = APIClient(
            baseURL: URL(string: "https://example.com")!,
            httpClient: http
        )

        let req = BMICalculateRequestDTO(
            weightKg: 70.0,
            heightCm: 175.0,
            age: 30,
            gender: "male",
            lang: "en"
        )

        // Use a simple response type that can decode from {}
        struct DummyResponse: Decodable {
            let ok: Bool?
        }
        let _: DummyResponse = try await api.post(
            path: "/api/v1/bmi/calculate",
            body: req,
            headers: [:]
        ) as DummyResponse

        guard let request = http.lastRequest else {
            XCTFail("Request not captured")
            return
        }

        XCTAssertEqual(request.url?.absoluteString, "https://example.com/api/v1/bmi/calculate")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertNotNil(request.httpBody)

        // JSON keys must be snake_case
        let json = try JSONSerialization.jsonObject(with: request.httpBody!, options: []) as? [String: Any]
        XCTAssertNotNil(json?["weight_kg"])
        XCTAssertNotNil(json?["height_cm"])
        XCTAssertEqual(json?["age"] as? Int, 30)
        XCTAssertEqual(json?["gender"] as? String, "male")
        XCTAssertEqual(json?["lang"] as? String, "en")
    }

    func test_post_withCustomHeaders_appendsHeaders() async throws {
        let http = CapturingHTTPClient()
        let api = APIClient(
            baseURL: URL(string: "https://example.com")!,
            httpClient: http
        )

        let req = BMICalculateRequestDTO(weightKg: 70.0, heightCm: 175.0, age: 30)

        // Use a simple response type that can decode from {}
        struct DummyResponse: Decodable {
            let ok: Bool?
        }
        let _: DummyResponse = try await api.post(
            path: "/api/v1/bmi/calculate",
            body: req,
            headers: ["X-API-Key": "test-key"]
        ) as DummyResponse

        guard let request = http.lastRequest else {
            XCTFail("Request not captured")
            return
        }

        XCTAssertEqual(request.value(forHTTPHeaderField: "X-API-Key"), "test-key")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Content-Type"), "application/json")
    }

    func test_post_normalizes_leading_slash_in_path() async throws {
        let http = CapturingHTTPClient()
        let api = APIClient(
            baseURL: URL(string: "https://example.com/base")!,
            httpClient: http
        )

        struct DummyResponse: Decodable {
            let ok: Bool?
        }
        struct DummyBody: Encodable {
            let x: Int
        }

        _ = try await api.post(
            path: "/api/v1/bmi/calculate",
            body: DummyBody(x: 1),
            headers: [:]
        ) as DummyResponse

        let url = try XCTUnwrap(http.lastRequest?.url)
        XCTAssertEqual(url.absoluteString, "https://example.com/base/api/v1/bmi/calculate")
    }

    func test_post_encodeFailure_throwsEncodingFailed() async throws {
        // Use a type that can't be encoded
        struct Unencodable: Encodable {
            func encode(to encoder: Encoder) throws {
                throw EncodingError.invalidValue("test", .init(codingPath: [], debugDescription: "test"))
            }
        }

        let api = APIClient(baseURL: URL(string: "https://example.com")!)

        do {
            struct DummyResponse: Decodable {
                let ok: Bool?
            }
            let _: DummyResponse = try await api.post(
                path: "/api/v1/bmi/calculate",
                body: Unencodable(),
                headers: [:]
            ) as DummyResponse
            XCTFail("Expected to throw")
        } catch let error as APIError {
            guard case .encodingFailed = error else {
                XCTFail("Expected .encodingFailed, got \(error)")
                return
            }
        }
    }
}
