import XCTest
@testable import PulsePlate

final class APIClientJSONValueAdmissionTests: XCTestCase {
    override func tearDown() {
        SequentialFitChefURLProtocol.reset()
        super.tearDown()
    }

    func testPostThroughRealTransportPreservesRawJSONMemberNamesAndAliases() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [RawJSONAdmissionURLProtocol.self]
        let session = URLSession(configuration: configuration)
        let apiClient = APIClient(
            baseURL: try XCTUnwrap(URL(string: "https://example.com")),
            httpClient: HTTPClient(session: session)
        )

        let response: JSONValue = try await apiClient.post(
            path: "/api/v1/pro/fitchef/recommend",
            body: AdmissionRequest(supportNeed: "daily_structure"),
            headers: ["X-API-Key": "admission-key"]
        )

        let root = try XCTUnwrap(response.objectValue)
        XCTAssertEqual(
            Set(root.keys),
            ["schema_version", "schemaVersion", "requested_support_need", "action"]
        )
        XCTAssertEqual(root["schema_version"]?.stringValue, "fitchef_support_handoff_v1")
        XCTAssertEqual(root["schemaVersion"]?.stringValue, "alias-must-remain-distinct")
        XCTAssertEqual(root["requested_support_need"]?.stringValue, "daily_structure")

        let action = try XCTUnwrap(root["action"]?.objectValue)
        XCTAssertEqual(Set(action.keys), ["action_type", "actionType"])
        XCTAssertEqual(action["action_type"]?.stringValue, "open_daily_nutrition")
        XCTAssertEqual(action["actionType"]?.stringValue, "alias-must-remain-distinct")
    }

    func testDefaultServiceHappyPathUsesRealTransportForBothDiagonalsAndReceipts() async throws {
        let scenarios: [(FitChefSupportNeed, String, FitChefSupportOutcomeState)] = [
            (.dailyStructure, "pro_daily_plate", .recorded),
            (.weeklyStructure, "pro_weekly_plan", .replayed),
        ]

        for (need, targetSurface, receiptState) in scenarios {
            SequentialFitChefURLProtocol.configure(
                responseBodies: [
                    handoffResponse(
                        supportNeed: need.rawValue,
                        targetSurface: targetSurface
                    ),
                    outcomeResponse(state: receiptState.rawValue),
                ]
            )
            let configuration = URLSessionConfiguration.ephemeral
            configuration.protocolClasses = [SequentialFitChefURLProtocol.self]
            let session = URLSession(configuration: configuration)
            let service = DefaultFitChefSupportService(
                apiClient: APIClient(
                    baseURL: try XCTUnwrap(URL(string: "https://example.com")),
                    httpClient: HTTPClient(session: session)
                )
            )
            let credential = "integration-credential"
            let eventID = "00000000-0000-4000-8000-000000000001"

            let descriptor = try await service.requestHandoff(
                for: need,
                apiKey: credential
            )
            let receipt = try await service.recordOutcome(
                FitChefSupportOutcomeAttempt(
                    supportNeed: descriptor.supportNeed,
                    outcome: .acknowledged,
                    clientEventID: eventID
                ),
                apiKey: credential
            )

            XCTAssertEqual(descriptor.supportNeed, need)
            XCTAssertEqual(descriptor.action.targetSurface.rawValue, targetSurface)
            XCTAssertEqual(receipt.state, receiptState)

            let requests = SequentialFitChefURLProtocol.capturedRequests()
            XCTAssertEqual(requests.count, 2)
            try assertRequest(
                requests[0],
                path: "/api/v1/pro/fitchef/recommend",
                credential: credential,
                body: ["support_need": need.rawValue]
            )
            try assertRequest(
                requests[1],
                path: "/api/v1/pro/fitchef/recommend/outcome",
                credential: credential,
                body: [
                    "schema_version": "fitchef_support_outcome_v1",
                    "support_need": need.rawValue,
                    "outcome": "acknowledged",
                    "client_event_id": eventID,
                ]
            )
            SequentialFitChefURLProtocol.reset()
        }
    }

    private func assertRequest(
        _ request: URLRequest,
        path: String,
        credential: String,
        body: [String: String],
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws {
        XCTAssertEqual(request.httpMethod, "POST", file: file, line: line)
        XCTAssertEqual(request.url?.path, path, file: file, line: line)
        XCTAssertEqual(
            request.value(forHTTPHeaderField: "X-API-Key"),
            credential,
            file: file,
            line: line
        )
        XCTAssertEqual(
            request.value(forHTTPHeaderField: "Content-Type"),
            "application/json",
            file: file,
            line: line
        )
        let data = try XCTUnwrap(request.httpBody, file: file, line: line)
        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: String],
            file: file,
            line: line
        )
        XCTAssertEqual(object, body, file: file, line: line)
    }

    private func handoffResponse(
        supportNeed: String,
        targetSurface: String
    ) -> Data {
        Data(
            """
            {
              "schema_version": "fitchef_support_handoff.v1",
              "scenario": "support_handoff",
              "support_need": "\(supportNeed)",
              "action": {
                "action_type": "handoff_to_product_surface",
                "target_surface": "\(targetSurface)"
              },
              "user_confirmation_required": true,
              "execution_authority": false,
              "plan_mutation_authority": false,
              "used_llm": false,
              "wellness_boundary": "wellness_planning_only"
            }
            """.utf8
        )
    }

    private func outcomeResponse(state: String) -> Data {
        Data(
            """
            {
              "schema_version": "fitchef_support_outcome_v1",
              "state": "\(state)"
            }
            """.utf8
        )
    }
}

private struct AdmissionRequest: Encodable {
    let supportNeed: String
}

private final class RawJSONAdmissionURLProtocol: URLProtocol {
    override static func canInit(with request: URLRequest) -> Bool { true }

    override static func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let body = Data(
            """
            {
              "schema_version": "fitchef_support_handoff_v1",
              "schemaVersion": "alias-must-remain-distinct",
              "requested_support_need": "daily_structure",
              "action": {
                "action_type": "open_daily_nutrition",
                "actionType": "alias-must-remain-distinct"
              }
            }
            """.utf8
        )
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: 200,
            httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: body)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

private final class SequentialFitChefURLProtocol: URLProtocol {
    private static let lock = NSLock()
    nonisolated(unsafe) private static var responseBodies: [Data] = []
    nonisolated(unsafe) private static var requests: [URLRequest] = []

    static func configure(responseBodies: [Data]) {
        withLock {
            self.responseBodies = responseBodies
            requests = []
        }
    }

    static func capturedRequests() -> [URLRequest] {
        withLock { requests }
    }

    static func reset() {
        withLock {
            responseBodies = []
            requests = []
        }
    }

    override static func canInit(with request: URLRequest) -> Bool { true }

    override static func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        let body: Data? = Self.withLock {
            var capturedRequest = request
            if capturedRequest.httpBody == nil {
                capturedRequest.httpBody = Self.readBodyStream(request.httpBodyStream)
            }
            Self.requests.append(capturedRequest)
            guard !Self.responseBodies.isEmpty else { return nil }
            return Self.responseBodies.removeFirst()
        }
        guard let body else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }
        let response = HTTPURLResponse(
            url: request.url!,
            statusCode: 200,
            httpVersion: nil,
            headerFields: ["Content-Type": "application/json"]
        )!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: body)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}

    private static func withLock<T>(_ operation: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return operation()
    }

    private static func readBodyStream(_ stream: InputStream?) -> Data? {
        guard let stream else { return nil }
        stream.open()
        defer { stream.close() }

        var data = Data()
        var buffer = [UInt8](repeating: 0, count: 1_024)
        while true {
            let count = stream.read(&buffer, maxLength: buffer.count)
            if count < 0 {
                return nil
            }
            if count == 0 {
                return data
            }
            data.append(buffer, count: count)
        }
    }
}
