import XCTest
@testable import PulsePlate

final class FitChefSupportDTORecognitionTests: XCTestCase {
    func testBothCanonicalHandoffDiagonalsAndSubmittedNeedEchoAreAccepted() async throws {
        for (need, target) in [
            (FitChefSupportNeed.dailyStructure, FitChefSupportTargetSurface.proDailyPlate),
            (FitChefSupportNeed.weeklyStructure, FitChefSupportTargetSurface.proWeeklyPlan),
        ] {
            let apiClient = FitChefCapturingAPIClient(
                responses: [.success(canonicalHandoffValue(need: need, target: target))]
            )
            let service = DefaultFitChefSupportService(apiClient: apiClient)

            let descriptor = try await service.requestHandoff(
                for: need,
                apiKey: "credential" // pragma: allowlist secret -- deterministic test sentinel
            )

            XCTAssertEqual(descriptor.supportNeed, need)
            XCTAssertEqual(descriptor.action.targetSurface, target)
        }
    }

    func testEveryMissingHandoffRootAndActionKeyFailsClosed() async throws {
        let canonical = try XCTUnwrap(
            canonicalHandoffValue(
                need: .dailyStructure,
                target: .proDailyPlate
            ).objectValue
        )
        for key in canonical.keys {
            var missing = canonical
            missing.removeValue(forKey: key)
            await assertHandoffRejected(.object(missing), label: "missing root key \(key)")
        }

        let action = try XCTUnwrap(canonical["action"]?.objectValue)
        for key in action.keys {
            var missingAction = action
            missingAction.removeValue(forKey: key)
            var payload = canonical
            payload["action"] = .object(missingAction)
            await assertHandoffRejected(
                .object(payload),
                label: "missing action key \(key)"
            )
        }
    }

    func testUnknownCamelCaseCollisionWrongTypeLiteralBooleanAndRelationFailClosed() async throws {
        let canonical = try XCTUnwrap(
            canonicalHandoffValue(
                need: .dailyStructure,
                target: .proDailyPlate
            ).objectValue
        )
        let canonicalAction = try XCTUnwrap(canonical["action"]?.objectValue)

        var unknownRoot = canonical
        unknownRoot["unknown"] = .string("credential-secret")

        var camelOnly = canonical
        camelOnly.removeValue(forKey: "support_need")
        camelOnly["supportNeed"] = .string("daily_structure")

        var rootCollision = canonical
        rootCollision["supportNeed"] = .string("weekly_structure")

        var actionCamel = canonicalAction
        actionCamel.removeValue(forKey: "target_surface")
        actionCamel["targetSurface"] = .string("pro_daily_plate")
        var actionCamelPayload = canonical
        actionCamelPayload["action"] = .object(actionCamel)

        var actionCollision = canonicalAction
        actionCollision["targetSurface"] = .string("pro_weekly_plan")
        var actionCollisionPayload = canonical
        actionCollisionPayload["action"] = .object(actionCollision)

        var wrongType = canonical
        wrongType["support_need"] = .number(1)

        var wrongLiteral = canonical
        wrongLiteral["scenario"] = .string("support_handoff ")

        var coerciveBoolean = canonical
        coerciveBoolean["user_confirmation_required"] = .number(1)

        var wrongBoolean = canonical
        wrongBoolean["execution_authority"] = .bool(true)

        var nullField = canonical
        nullField["wellness_boundary"] = .null

        var nonObjectAction = canonical
        nonObjectAction["action"] = .array([])

        var offDiagonalAction = canonicalAction
        offDiagonalAction["target_surface"] = .string("pro_weekly_plan")
        var offDiagonal = canonical
        offDiagonal["action"] = .object(offDiagonalAction)

        let cases: [(String, JSONValue)] = [
            ("unknown root", .object(unknownRoot)),
            ("camel-only root", .object(camelOnly)),
            ("root alias collision", .object(rootCollision)),
            ("camel-only action", .object(actionCamelPayload)),
            ("action alias collision", .object(actionCollisionPayload)),
            ("wrong type", .object(wrongType)),
            ("wrong literal", .object(wrongLiteral)),
            ("numeric boolean", .object(coerciveBoolean)),
            ("wrong boolean", .object(wrongBoolean)),
            ("null field", .object(nullField)),
            ("non-object action", .object(nonObjectAction)),
            ("off diagonal", .object(offDiagonal)),
            ("non-object root", .array([])),
        ]

        for (label, payload) in cases {
            await assertHandoffRejected(payload, label: label)
        }
    }

    func testInternallyValidHandoffWithWrongRequestEchoFailsClosed() async {
        await assertHandoffRejected(
            canonicalHandoffValue(
                need: .weeklyStructure,
                target: .proWeeklyPlan
            ),
            submittedNeed: .dailyStructure,
            label: "submitted need echo"
        )
    }

    func testExactRecordedAndReplayedReceiptsAreAccepted() async throws {
        for state in [
            FitChefSupportOutcomeState.recorded,
            FitChefSupportOutcomeState.replayed,
        ] {
            let apiClient = FitChefCapturingAPIClient(
                responses: [.success(canonicalOutcomeReceiptValue(state: state))]
            )
            let service = DefaultFitChefSupportService(apiClient: apiClient)

            let receipt = try await service.recordOutcome(
                fixedAttempt(),
                apiKey: "credential" // pragma: allowlist secret -- deterministic test sentinel
            )

            XCTAssertEqual(receipt.state, state)
        }
    }

    func testMalformedOutcomeReceiptsFailClosedWithoutRawDiagnostics() async throws {
        let canonical = try XCTUnwrap(
            canonicalOutcomeReceiptValue(state: .recorded).objectValue
        )
        var missingSchema = canonical
        missingSchema.removeValue(forKey: "schema_version")
        var missingState = canonical
        missingState.removeValue(forKey: "state")
        var extra = canonical
        extra["raw_secret"] = .string("credential-secret")
        var camelOnly = canonical
        camelOnly.removeValue(forKey: "schema_version")
        camelOnly["schemaVersion"] = .string("fitchef_support_outcome_v1")
        var collision = canonical
        collision["schemaVersion"] = .string("fitchef_support_outcome_v1")
        var wrongSchema = canonical
        wrongSchema["schema_version"] = .string("fitchef_support_outcome.v2")
        var wrongState = canonical
        wrongState["state"] = .string("saved")
        var wrongType = canonical
        wrongType["state"] = .bool(true)

        let cases: [(String, JSONValue)] = [
            ("missing schema", .object(missingSchema)),
            ("missing state", .object(missingState)),
            ("extra key", .object(extra)),
            ("camel-only", .object(camelOnly)),
            ("alias collision", .object(collision)),
            ("wrong schema", .object(wrongSchema)),
            ("wrong state", .object(wrongState)),
            ("wrong type", .object(wrongType)),
            ("non-object", .string("credential-secret")),
        ]

        for (label, payload) in cases {
            let apiClient = FitChefCapturingAPIClient(responses: [.success(payload)])
            let service = DefaultFitChefSupportService(apiClient: apiClient)
            do {
                _ = try await service.recordOutcome(
                    fixedAttempt(),
                    apiKey: "credential" // pragma: allowlist secret -- deterministic test sentinel
                )
                XCTFail("Expected receipt rejection: \(label)")
            } catch {
                XCTAssertTrue(error is FitChefSupportContractError, label)
                let diagnostic = String(describing: error)
                XCTAssertFalse(diagnostic.contains("credential-secret"), label)
                XCTAssertFalse(diagnostic.contains("raw_secret"), label)
            }
        }
    }

    // JSONValue.object is the admitted post-transport carrier. It preserves distinct
    // snake_case/camelCase spellings (proved by APIClientJSONValueAdmissionTests), but a
    // dictionary cannot prove rejection of repeated raw members with the same spelling.
    // Byte-level duplicate-member detection is intentionally outside this PR's claim.

    private func assertHandoffRejected(
        _ payload: JSONValue,
        submittedNeed: FitChefSupportNeed = .dailyStructure,
        label: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) async {
        let apiClient = FitChefCapturingAPIClient(responses: [.success(payload)])
        let service = DefaultFitChefSupportService(apiClient: apiClient)
        do {
            _ = try await service.requestHandoff(
                for: submittedNeed,
                apiKey: "credential" // pragma: allowlist secret -- deterministic test sentinel
            )
            XCTFail("Expected handoff rejection: \(label)", file: file, line: line)
        } catch {
            XCTAssertTrue(error is FitChefSupportContractError, label, file: file, line: line)
            let diagnostic = String(describing: error)
            XCTAssertFalse(diagnostic.contains("credential-secret"), file: file, line: line)
            XCTAssertFalse(diagnostic.contains("unknown"), file: file, line: line)
        }
    }
}

final class FitChefSupportServiceTests: XCTestCase {
    func testRecommendUsesOneCanonicalPostWithOnlySupportNeedAndCredential() async throws {
        let apiClient = FitChefCapturingAPIClient(
            responses: [
                .success(
                    canonicalHandoffValue(
                        need: .dailyStructure,
                        target: .proDailyPlate
                    )
                )
            ]
        )
        let service = DefaultFitChefSupportService(apiClient: apiClient)

        _ = try await service.requestHandoff(
            for: .dailyStructure,
            apiKey: "pinned-credential" // pragma: allowlist secret -- deterministic test sentinel
        )

        let requests = apiClient.requests
        XCTAssertEqual(requests.count, 1)
        XCTAssertEqual(requests[0].path, "/api/v1/pro/fitchef/recommend")
        XCTAssertEqual(requests[0].headers, ["X-API-Key": "pinned-credential"])
        XCTAssertEqual(Set(requests[0].body.keys), ["support_need"])
        XCTAssertEqual(requests[0].body["support_need"] as? String, "daily_structure")
        XCTAssertEqual(apiClient.postRawCallCount, 0)
    }

    func testAllTwoByTwoOutcomeAttemptsUseExactClosedBody() async throws {
        let apiClient = FitChefCapturingAPIClient(
            responses: Array(
                repeating: .success(canonicalOutcomeReceiptValue(state: .recorded)),
                count: 4
            )
        )
        let service = DefaultFitChefSupportService(apiClient: apiClient)
        var expectedPairs: [(String, String)] = []

        for need in [FitChefSupportNeed.dailyStructure, .weeklyStructure] {
            for outcome in [FitChefSupportOutcome.acknowledged, .dismissed] {
                expectedPairs.append((need.rawValue, outcome.rawValue))
                _ = try await service.recordOutcome(
                    FitChefSupportOutcomeAttempt(
                        supportNeed: need,
                        outcome: outcome,
                        clientEventID: "00000000-0000-4000-8000-000000000001"
                    ),
                    apiKey: "pinned-credential" // pragma: allowlist secret -- deterministic test sentinel
                )
            }
        }

        XCTAssertEqual(apiClient.requests.count, 4)
        for (index, request) in apiClient.requests.enumerated() {
            XCTAssertEqual(request.path, "/api/v1/pro/fitchef/recommend/outcome")
            XCTAssertEqual(request.headers, ["X-API-Key": "pinned-credential"])
            XCTAssertEqual(
                Set(request.body.keys),
                ["schema_version", "support_need", "outcome", "client_event_id"]
            )
            XCTAssertEqual(
                request.body["schema_version"] as? String,
                "fitchef_support_outcome_v1"
            )
            XCTAssertEqual(request.body["support_need"] as? String, expectedPairs[index].0)
            XCTAssertEqual(request.body["outcome"] as? String, expectedPairs[index].1)
            XCTAssertEqual(
                request.body["client_event_id"] as? String,
                "00000000-0000-4000-8000-000000000001"
            )
            for forbidden in [
                "target_surface", "subject_id", "user_id", "timestamp", "profile",
                "plan", "goal", "health", "nutrition", "text", "metadata", "analytics",
            ] {
                XCTAssertNil(request.body[forbidden], "Forbidden outcome field: \(forbidden)")
            }
        }
        XCTAssertEqual(apiClient.postRawCallCount, 0)
    }
}

@MainActor
final class FitChefSupportFlowViewModelTests: XCTestCase {
    func testRenderSelectionChangeClearAndPreResultExitCreateNoNetworkOutcome() throws {
        let service = FitChefRecordingService(
            handoffResults: [.success(try makeDescriptor(need: .dailyStructure))]
        )
        let viewModel = makeViewModel(service: service)

        assertSelecting(viewModel.state, need: nil)
        viewModel.select(.dailyStructure)
        assertSelecting(viewModel.state, need: .dailyStructure)
        viewModel.select(.weeklyStructure)
        assertSelecting(viewModel.state, need: .weeklyStructure)
        viewModel.clearSelection()
        assertSelecting(viewModel.state, need: nil)
        viewModel.cancel()

        XCTAssertEqual(service.handoffCalls.count, 0)
        XCTAssertEqual(service.outcomeCalls.count, 0)
    }

    func testMissingAndBlankCredentialFailLocallyWithoutEntitlementInferenceOrCall() async {
        for credential in [nil, "", "   "] {
            let service = FitChefRecordingService()
            let viewModel = FitChefSupportFlowViewModel(
                service: service,
                apiKeyProvider: { credential },
                makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
            )
            viewModel.select(.dailyStructure)

            viewModel.confirm()

            XCTAssertEqual(service.handoffCalls.count, 0)
            XCTAssertEqual(service.outcomeCalls.count, 0)
            XCTAssertEqual(
                viewModel.userFacingMessageKey,
                "fitchef.support_flow.unavailable"
            )
            XCTAssertFalse(viewModel.userFacingMessageKey?.contains("PRO") == true)
            XCTAssertFalse(viewModel.userFacingMessageKey?.contains("entitl") == true)
        }
    }

    func testConfirmSendsOneRecommendAndPresentsOnlyTheValidatedDescriptor() async throws {
        let descriptor = try makeDescriptor(need: .dailyStructure)
        let service = FitChefRecordingService(handoffResults: [.success(descriptor)])
        let viewModel = makeViewModel(service: service)
        viewModel.select(.dailyStructure)

        viewModel.confirm()
        assertRequesting(viewModel.state, need: .dailyStructure)
        viewModel.confirm()
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }

        XCTAssertEqual(service.handoffCalls.count, 1)
        XCTAssertEqual(service.handoffCalls[0].need, .dailyStructure)
        XCTAssertEqual(service.handoffCalls[0].apiKey, "credential-one")
        XCTAssertEqual(service.outcomeCalls.count, 0)
        guard case .presenting(let presented) = viewModel.state else {
            XCTFail("Expected presenting state, got \(viewModel.state)")
            return
        }
        XCTAssertEqual(presented, descriptor)
        XCTAssertEqual(
            viewModel.targetDisplayKey,
            "fitchef.support_flow.result.target.daily"
        )
        XCTAssertFalse(viewModel.targetDisplayKey?.contains("pro_daily_plate") == true)
    }

    func testSecondConfirmWhileRecommendIsPendingIsIgnored() async throws {
        let started = expectation(description: "recommend started")
        let service = FitChefSuspendingService(handoffStarted: started)
        let viewModel = makeViewModel(service: service)
        viewModel.select(.dailyStructure)

        viewModel.confirm()
        assertRequesting(viewModel.state, need: .dailyStructure)
        viewModel.select(.weeklyStructure)
        viewModel.confirm()
        assertRequesting(viewModel.state, need: .dailyStructure)
        await fulfillment(of: [started], timeout: 2)

        XCTAssertEqual(service.handoffCalls.count, 1)
        service.resumeHandoff(.success(try makeDescriptor(need: .dailyStructure)))
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }
        guard case .presenting = viewModel.state else {
            XCTFail("Expected presenting state, got \(viewModel.state)")
            return
        }
    }

    func testAcknowledgeSynchronouslyClaimsRecordingAndRejectsImmediateAlternatives() async throws {
        try await assertFirstOutcomeGestureClaimsSynchronously(
            firstOutcome: .acknowledged
        )
    }

    func testDismissSynchronouslyClaimsRecordingAndRejectsImmediateAlternatives() async throws {
        try await assertFirstOutcomeGestureClaimsSynchronously(
            firstOutcome: .dismissed
        )
    }

    func testRetryHandoffSynchronouslyClaimsRequestingAndDoesNotDoubleDispatch() async throws {
        let started = expectation(description: "retry handoff started")
        let descriptor = try makeDescriptor(need: .weeklyStructure)
        let service = FitChefRetryClaimService(
            mode: .handoff(descriptor),
            retryStarted: started
        )
        let credentials = CredentialSequence(["credential-one", "credential-two"])
        let viewModel = FitChefSupportFlowViewModel(
            service: service,
            apiKeyProvider: { credentials.next() },
            makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
        )
        viewModel.select(.weeklyStructure)
        viewModel.confirm()
        await waitForState(viewModel) {
            if case .handoffFailed(_, .retryable) = $0 { return true }
            return false
        }

        viewModel.retryHandoff()
        assertRequesting(viewModel.state, need: .weeklyStructure)
        viewModel.retryHandoff()
        assertRequesting(viewModel.state, need: .weeklyStructure)
        await fulfillment(of: [started], timeout: 2)
        XCTAssertEqual(service.handoffCalls.count, 2)
        XCTAssertEqual(service.handoffCalls.map(\.need), [.weeklyStructure, .weeklyStructure])
        XCTAssertEqual(service.handoffCalls.map(\.apiKey), ["credential-one", "credential-one"])
        XCTAssertEqual(credentials.readCount, 1)

        service.resumeRetryHandoff(.success(descriptor))
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }
    }

    func testRetryOutcomeSynchronouslyClaimsSameRecordingAndDoesNotDoubleDispatch() async throws {
        let started = expectation(description: "retry outcome started")
        let descriptor = try makeDescriptor(need: .dailyStructure)
        let service = FitChefRetryClaimService(
            mode: .outcome(descriptor),
            retryStarted: started
        )
        let identifiers = UUIDSequence([UUID(uuidString: fixedUUIDString)!])
        let viewModel = FitChefSupportFlowViewModel(
            service: service,
            apiKeyProvider: { "credential-one" },
            makeClientEventID: { identifiers.next() }
        )
        viewModel.select(.dailyStructure)
        viewModel.confirm()
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }
        viewModel.acknowledge()
        await waitForState(viewModel) {
            if case .outcomeFailed(_, _, .retryable) = $0 { return true }
            return false
        }
        guard case .outcomeFailed(_, let firstAttempt, .retryable) = viewModel.state else {
            XCTFail("Expected retryable outcome failure, got \(viewModel.state)")
            return
        }

        viewModel.retryOutcome()
        assertRecording(
            viewModel.state,
            descriptor: descriptor,
            attempt: firstAttempt
        )
        viewModel.retryOutcome()
        assertRecording(
            viewModel.state,
            descriptor: descriptor,
            attempt: firstAttempt
        )
        await fulfillment(of: [started], timeout: 2)
        XCTAssertEqual(service.outcomeCalls.count, 2)
        XCTAssertEqual(service.outcomeCalls[0].attempt, firstAttempt)
        XCTAssertEqual(service.outcomeCalls[1].attempt, firstAttempt)
        XCTAssertEqual(service.outcomeCalls.map(\.apiKey), ["credential-one", "credential-one"])
        XCTAssertEqual(identifiers.readCount, 1)

        service.resumeRetryOutcome(
            .success(FitChefSupportOutcomeReceipt(state: .recorded))
        )
        await waitForState(viewModel) {
            if case .completed = $0 { return true }
            return false
        }
    }

    func testHandoffFailureDoesNotRetryAutomaticallyAndExplicitRetryUsesSameNeed() async throws {
        let descriptor = try makeDescriptor(need: .weeklyStructure)
        let service = FitChefRecordingService(
            handoffResults: [
                .failure(APIError.transport("raw-handoff-secret")),
                .success(descriptor),
            ]
        )
        let credentials = CredentialSequence(["credential-one", "credential-two"])
        let viewModel = FitChefSupportFlowViewModel(
            service: service,
            apiKeyProvider: { credentials.next() },
            makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
        )
        viewModel.select(.weeklyStructure)

        viewModel.confirm()
        assertRequesting(viewModel.state, need: .weeklyStructure)
        await waitForState(viewModel) {
            if case .handoffFailed = $0 { return true }
            return false
        }
        XCTAssertEqual(service.handoffCalls.count, 1)
        XCTAssertEqual(service.outcomeCalls.count, 0)
        XCTAssertTrue(viewModel.canRetryHandoff)
        XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.handoff_failed")
        XCTAssertEqual(credentials.readCount, 1)
        XCTAssertFalse(
            viewModel.userFacingMessageKey?.contains("raw-handoff-secret") == true
        )
        await Task.yield()
        XCTAssertEqual(service.handoffCalls.count, 1, "Automatic retry is forbidden")

        viewModel.retryHandoff()
        assertRequesting(viewModel.state, need: .weeklyStructure)
        viewModel.retryHandoff()
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }

        XCTAssertEqual(service.handoffCalls.map(\.need), [.weeklyStructure, .weeklyStructure])
        XCTAssertEqual(service.handoffCalls.map(\.apiKey), ["credential-one", "credential-one"])
        XCTAssertEqual(credentials.readCount, 1)
        XCTAssertEqual(service.outcomeCalls.count, 0)
        guard case .presenting(let presented) = viewModel.state else {
            XCTFail("Expected presenting state, got \(viewModel.state)")
            return
        }
        XCTAssertEqual(presented, descriptor)
    }

    func testHandoff401And403RequireNewLifecycleWithoutRetryOrCredentialSwitch() async {
        for statusCode in [401, 403] {
            let service = FitChefRecordingService(
                handoffResults: [
                    .failure(
                        APIError.api(
                            statusCode: statusCode,
                            message: "raw-auth-detail"
                        )
                    ),
                ]
            )
            let credentials = CredentialSequence(["credential-one", "credential-two"])
            let viewModel = FitChefSupportFlowViewModel(
                service: service,
                apiKeyProvider: { credentials.next() },
                makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
            )
            viewModel.select(.dailyStructure)

            viewModel.confirm()
            assertRequesting(viewModel.state, need: .dailyStructure)
            await waitForState(viewModel) {
                if case .handoffFailed = $0 { return true }
                return false
            }

            assertHandoffFailure(
                viewModel.state,
                need: .dailyStructure,
                failure: .restartRequired
            )
            XCTAssertFalse(viewModel.canRetryHandoff)
            XCTAssertTrue(viewModel.requiresNewLifecycle)
            XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.handoff_failed")
            XCTAssertFalse(
                viewModel.userFacingMessageKey?.contains("raw-auth-detail") == true
            )
            viewModel.retryHandoff()
            XCTAssertEqual(service.handoffCalls.count, 1)
            XCTAssertEqual(service.handoffCalls[0].apiKey, "credential-one")
            XCTAssertEqual(credentials.readCount, 1)

            viewModel.startNewLifecycle()
            assertSelecting(viewModel.state, need: nil)
        }
    }

    func testHandoffValidationEncodingAndDeterministic4xxAreTerminalWithoutRetry() async {
        let validation = ValidationErrorResponse(
            detail: [
                ValidationErrorItem(
                    loc: [.string("body")],
                    msg: "raw-validation-detail",
                    type: "value_error"
                )
            ]
        )
        let errors: [Error] = [
            APIError.validation(validation),
            APIError.api(statusCode: 422, message: "raw-422-detail"),
            APIError.encodingFailed("raw-encoding-detail"),
            APIError.api(statusCode: 400, message: "raw-400-detail"),
            APIError.api(statusCode: 404, message: "raw-404-detail"),
            APIError.api(statusCode: 409, message: "raw-409-detail"),
            APIError.api(statusCode: 429, message: "raw-429-detail"),
        ]

        for error in errors {
            let service = FitChefRecordingService(handoffResults: [.failure(error)])
            let credentials = CredentialSequence(["credential-one", "credential-two"])
            let viewModel = FitChefSupportFlowViewModel(
                service: service,
                apiKeyProvider: { credentials.next() },
                makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
            )
            viewModel.select(.weeklyStructure)

            viewModel.confirm()
            assertRequesting(viewModel.state, need: .weeklyStructure)
            await waitForState(viewModel) {
                if case .handoffFailed = $0 { return true }
                return false
            }

            assertHandoffFailure(
                viewModel.state,
                need: .weeklyStructure,
                failure: .terminal
            )
            XCTAssertFalse(viewModel.canRetryHandoff)
            XCTAssertFalse(viewModel.requiresNewLifecycle)
            XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.handoff_failed")
            XCTAssertFalse(viewModel.userFacingMessageKey?.contains("raw-") == true)
            viewModel.retryHandoff()
            XCTAssertEqual(service.handoffCalls.count, 1)
            XCTAssertEqual(service.handoffCalls[0].apiKey, "credential-one")
            XCTAssertEqual(credentials.readCount, 1)
        }
    }

    func testHandoffTransientAndInvalidDescriptorFailuresAreManualRetryOnlyWithPinnedKey() async throws {
        let retryableErrors: [Error] = [
            APIError.api(statusCode: 503, message: "raw-503-detail"),
            APIError.api(statusCode: 500, message: "raw-500-detail"),
            APIError.api(statusCode: 599, message: "raw-599-detail"),
            APIError.transport("raw-transport-detail"),
            APIError.emptyResponse(statusCode: 204),
            FitChefSupportContractError.invalidHandoffDescriptor,
        ]

        for error in retryableErrors {
            let descriptor = try makeDescriptor(need: .dailyStructure)
            let service = FitChefRecordingService(
                handoffResults: [.failure(error), .success(descriptor)]
            )
            let credentials = CredentialSequence(["credential-one", "credential-two"])
            let viewModel = FitChefSupportFlowViewModel(
                service: service,
                apiKeyProvider: { credentials.next() },
                makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
            )
            viewModel.select(.dailyStructure)

            viewModel.confirm()
            assertRequesting(viewModel.state, need: .dailyStructure)
            await waitForState(viewModel) {
                if case .handoffFailed = $0 { return true }
                return false
            }

            assertHandoffFailure(
                viewModel.state,
                need: .dailyStructure,
                failure: .retryable
            )
            XCTAssertTrue(viewModel.canRetryHandoff)
            XCTAssertFalse(viewModel.requiresNewLifecycle)
            XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.handoff_failed")
            XCTAssertFalse(viewModel.userFacingMessageKey?.contains("raw-") == true)
            XCTAssertEqual(service.handoffCalls.count, 1)
            XCTAssertEqual(credentials.readCount, 1)
            await Task.yield()
            XCTAssertEqual(service.handoffCalls.count, 1, "Automatic retry is forbidden")

            viewModel.retryHandoff()
            assertRequesting(viewModel.state, need: .dailyStructure)
            viewModel.retryHandoff()
            await waitForState(viewModel) {
                if case .presenting = $0 { return true }
                return false
            }

            XCTAssertEqual(service.handoffCalls.map(\.apiKey), ["credential-one", "credential-one"])
            XCTAssertEqual(credentials.readCount, 1)
            guard case .presenting(let presented) = viewModel.state else {
                XCTFail("Expected presenting state, got \(viewModel.state)")
                continue
            }
            XCTAssertEqual(presented, descriptor)
        }
    }

    func testHandoffFailureCancelBackAndDeallocationCreateZeroOutcomes() async {
        let service = FitChefRecordingService(
            handoffResults: [
                .failure(APIError.transport("raw-network-secret")),
            ]
        )
        var viewModel: FitChefSupportFlowViewModel? = makeViewModel(service: service)
        viewModel?.select(.dailyStructure)

        viewModel?.confirm()
        if let viewModel {
            await waitForState(viewModel) {
                if case .handoffFailed = $0 { return true }
                return false
            }
        }
        viewModel?.cancel()
        weak var weakViewModel = viewModel
        viewModel = nil

        XCTAssertNil(weakViewModel)
        XCTAssertEqual(service.handoffCalls.count, 1)
        XCTAssertEqual(service.outcomeCalls.count, 0)
    }

    func testFirstPostResultActionWinsAndUsesOneLowercaseUUID() async throws {
        let descriptor = try makeDescriptor(need: .weeklyStructure)
        let service = FitChefRecordingService(
            handoffResults: [.success(descriptor)],
            outcomeResults: [.success(FitChefSupportOutcomeReceipt(state: .recorded))]
        )
        let identifiers = UUIDSequence([UUID(uuidString: fixedUUIDString)!])
        let viewModel = FitChefSupportFlowViewModel(
            service: service,
            apiKeyProvider: { "credential-one" },
            makeClientEventID: { identifiers.next() }
        )
        viewModel.select(.weeklyStructure)
        viewModel.confirm()
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }

        viewModel.acknowledge()
        guard case .recording(_, let claimedAttempt) = viewModel.state else {
            XCTFail("Expected immediate recording state, got \(viewModel.state)")
            return
        }
        viewModel.dismissResult()
        viewModel.acknowledge()
        assertRecording(viewModel.state, descriptor: descriptor, attempt: claimedAttempt)
        await waitForState(viewModel) {
            if case .completed = $0 { return true }
            return false
        }

        XCTAssertEqual(service.outcomeCalls.count, 1)
        let call = service.outcomeCalls[0]
        XCTAssertEqual(call.attempt.supportNeed, .weeklyStructure)
        XCTAssertEqual(call.attempt.outcome, .acknowledged)
        XCTAssertEqual(call.attempt.clientEventID, fixedUUIDString.lowercased())
        XCTAssertEqual(call.attempt.clientEventID, call.attempt.clientEventID.lowercased())
        XCTAssertEqual(call.apiKey, "credential-one")
        XCTAssertEqual(identifiers.readCount, 1)
        guard case .completed(let completedDescriptor, let outcome, let state) = viewModel.state else {
            XCTFail("Expected completed state, got \(viewModel.state)")
            return
        }
        XCTAssertEqual(completedDescriptor, descriptor)
        XCTAssertEqual(outcome, .acknowledged)
        XCTAssertEqual(state, .recorded)
        XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.recorded")
    }

    func testDismissMapsOnlyToDismissed() async throws {
        let descriptor = try makeDescriptor(need: .dailyStructure)
        let service = FitChefRecordingService(
            handoffResults: [.success(descriptor)],
            outcomeResults: [.success(FitChefSupportOutcomeReceipt(state: .replayed))]
        )
        let viewModel = makeViewModel(service: service)
        viewModel.select(.dailyStructure)
        viewModel.confirm()
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }

        viewModel.dismissResult()
        await waitForState(viewModel) {
            if case .completed = $0 { return true }
            return false
        }

        XCTAssertEqual(service.outcomeCalls.count, 1)
        XCTAssertEqual(service.outcomeCalls[0].attempt.outcome, .dismissed)
        guard case .completed(_, let outcome, let state) = viewModel.state else {
            XCTFail("Expected completed state, got \(viewModel.state)")
            return
        }
        XCTAssertEqual(outcome, .dismissed)
        XCTAssertEqual(state, .replayed)
        XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.replayed")
    }

    func testRetryableFailurePinsSuccessfulCredentialAndReusesByteEquivalentAttempt() async throws {
        let descriptor = try makeDescriptor(need: .dailyStructure)
        let service = FitChefRecordingService(
            handoffResults: [.success(descriptor)],
            outcomeResults: [
                .failure(APIError.api(statusCode: 503, message: "raw-store-secret")),
                .success(FitChefSupportOutcomeReceipt(state: .recorded)),
            ]
        )
        let credentials = CredentialSequence(["credential-one", "credential-two"])
        let viewModel = FitChefSupportFlowViewModel(
            service: service,
            apiKeyProvider: { credentials.next() },
            makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
        )
        viewModel.select(.dailyStructure)
        viewModel.confirm()
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }

        viewModel.acknowledge()
        await waitForState(viewModel) {
            if case .outcomeFailed(_, _, .retryable) = $0 { return true }
            return false
        }

        XCTAssertTrue(viewModel.canRetryOutcome)
        XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.outcome_retryable")
        XCTAssertEqual(service.outcomeCalls.count, 1)
        let first = service.outcomeCalls[0]
        XCTAssertEqual(first.apiKey, "credential-one")
        XCTAssertEqual(credentials.readCount, 1)

        viewModel.retryOutcome()
        guard case .recording = viewModel.state else {
            XCTFail("Expected immediate recording state, got \(viewModel.state)")
            return
        }
        viewModel.retryOutcome()
        await waitForState(viewModel) {
            if case .completed = $0 { return true }
            return false
        }

        XCTAssertEqual(service.outcomeCalls.count, 2)
        XCTAssertEqual(service.outcomeCalls[1].attempt, first.attempt)
        XCTAssertEqual(service.outcomeCalls[1].apiKey, "credential-one")
        XCTAssertEqual(credentials.readCount, 1)
        XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.recorded")
    }

    func test409And422AreTerminalAndNeverGenerateReplacementAttempt() async throws {
        let validation = ValidationErrorResponse(
            detail: [
                ValidationErrorItem(
                    loc: [.string("body")],
                    msg: "raw-validation-secret",
                    type: "value_error"
                )
            ]
        )
        let errors: [Error] = [
            APIError.api(statusCode: 409, message: "raw-conflict-secret"),
            APIError.validation(validation),
        ]

        for error in errors {
            let descriptor = try makeDescriptor(need: .dailyStructure)
            let service = FitChefRecordingService(
                handoffResults: [.success(descriptor)],
                outcomeResults: [.failure(error)]
            )
            let viewModel = makeViewModel(service: service)
            viewModel.select(.dailyStructure)
            viewModel.confirm()
            await waitForState(viewModel) {
                if case .presenting = $0 { return true }
                return false
            }
            viewModel.acknowledge()
            await waitForState(viewModel) {
                if case .outcomeFailed = $0 { return true }
                return false
            }
            let firstAttempt = try XCTUnwrap(service.outcomeCalls.first?.attempt)

            XCTAssertFalse(viewModel.canRetryOutcome)
            XCTAssertFalse(viewModel.requiresNewLifecycle)
            XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.outcome_terminal")
            viewModel.retryOutcome()
            XCTAssertEqual(service.outcomeCalls.count, 1)
            XCTAssertEqual(service.outcomeCalls[0].attempt, firstAttempt)
        }
    }

    func test401And403RequireNewLifecycleAndNeverSwitchCredentialInPlace() async throws {
        for statusCode in [401, 403] {
            let descriptor = try makeDescriptor(need: .dailyStructure)
            let service = FitChefRecordingService(
                handoffResults: [.success(descriptor)],
                outcomeResults: [
                    .failure(
                        APIError.api(
                            statusCode: statusCode,
                            message: "raw-auth-secret"
                        )
                    ),
                ]
            )
            let credentials = CredentialSequence(["credential-one", "credential-two"])
            let viewModel = FitChefSupportFlowViewModel(
                service: service,
                apiKeyProvider: { credentials.next() },
                makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
            )
            viewModel.select(.dailyStructure)
            viewModel.confirm()
            await waitForState(viewModel) {
                if case .presenting = $0 { return true }
                return false
            }
            viewModel.acknowledge()
            await waitForState(viewModel) {
                if case .outcomeFailed = $0 { return true }
                return false
            }

            XCTAssertFalse(viewModel.canRetryOutcome)
            XCTAssertTrue(viewModel.requiresNewLifecycle)
            XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.outcome_restart")
            viewModel.retryOutcome()
            XCTAssertEqual(service.outcomeCalls.count, 1)
            XCTAssertEqual(service.outcomeCalls[0].apiKey, "credential-one")
            XCTAssertEqual(credentials.readCount, 1)

            viewModel.startNewLifecycle()
            assertSelecting(viewModel.state, need: nil)
        }
    }

    func testRetryableClassesNeverRetryAutomaticallyAndExplicitRetryReusesAttempt() async throws {
        let retryableErrors: [Error] = [
            APIError.api(statusCode: 429, message: "raw-rate-secret"),
            APIError.api(statusCode: 500, message: "raw-server-secret"),
            APIError.api(statusCode: 503, message: "raw-store-secret"),
            APIError.transport("raw-transport-secret"),
            APIError.emptyResponse(statusCode: 204),
            FitChefSupportContractError.invalidOutcomeReceipt,
        ]

        for error in retryableErrors {
            let descriptor = try makeDescriptor(need: .weeklyStructure)
            let service = FitChefRecordingService(
                handoffResults: [.success(descriptor)],
                outcomeResults: [
                    .failure(error),
                    .success(FitChefSupportOutcomeReceipt(state: .replayed)),
                ]
            )
            let viewModel = makeViewModel(service: service)
            viewModel.select(.weeklyStructure)
            viewModel.confirm()
            await waitForState(viewModel) {
                if case .presenting = $0 { return true }
                return false
            }
            viewModel.dismissResult()
            await waitForState(viewModel) {
                if case .outcomeFailed(_, _, .retryable) = $0 { return true }
                return false
            }

            XCTAssertEqual(service.outcomeCalls.count, 1)
            XCTAssertTrue(viewModel.canRetryOutcome)
            XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.outcome_retryable")
            let first = service.outcomeCalls[0]

            await Task.yield()
            XCTAssertEqual(service.outcomeCalls.count, 1, "Automatic retry is forbidden")

            viewModel.retryOutcome()
            guard case .recording = viewModel.state else {
                XCTFail("Expected immediate recording state, got \(viewModel.state)")
                continue
            }
            viewModel.retryOutcome()
            await waitForState(viewModel) {
                if case .completed = $0 { return true }
                return false
            }
            XCTAssertEqual(service.outcomeCalls.count, 2)
            XCTAssertEqual(service.outcomeCalls[1].attempt, first.attempt)
            XCTAssertEqual(service.outcomeCalls[1].apiKey, first.apiKey)
            XCTAssertEqual(viewModel.userFacingMessageKey, "fitchef.support_flow.replayed")
        }
    }

    func testRawErrorsCredentialEventIDAndTargetSlugNeverReachUserFacingKeys() async throws {
        let descriptor = try makeDescriptor(need: .dailyStructure)
        let service = FitChefRecordingService(
            handoffResults: [.success(descriptor)],
            outcomeResults: [
                .failure(APIError.transport("raw-body credential-one \(fixedUUIDString) pro_daily_plate")),
            ]
        )
        let viewModel = makeViewModel(service: service)
        viewModel.select(.dailyStructure)
        viewModel.confirm()
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }
        viewModel.acknowledge()
        await waitForState(viewModel) {
            if case .outcomeFailed = $0 { return true }
            return false
        }

        let key = try XCTUnwrap(viewModel.userFacingMessageKey)
        for forbidden in ["raw-body", "credential-one", fixedUUIDString, "pro_daily_plate"] {
            XCTAssertFalse(key.contains(forbidden))
        }
        XCTAssertEqual(key, "fitchef.support_flow.outcome_retryable")
    }

    func testPinnedCredentialSourceLifetimeIsLimitedToAdmissibleRetryWindows() throws {
        let source = try viewModelSource()
        let handoff = try sourceSlice(
            source,
            from: "private func performHandoff(",
            to: "private func handoffFailure"
        )
        assertOrderedSource(
            [
                "let failure = handoffFailure(for: error)",
                "if failure != .retryable",
                "pinnedAPIKey = nil",
                "transition(to: .handoffFailed(need, failure))",
            ],
            in: handoff
        )

        let outcome = try sourceSlice(
            source,
            from: "private func performOutcome(",
            to: "private func outcomeFailure"
        )
        assertOrderedSource(
            [
                "guard isCurrent(generation) else { return }",
                "pinnedAPIKey = nil",
                "transition(to: .completed",
                "let failure = outcomeFailure(for: error)",
                "if failure != .retryable",
                "pinnedAPIKey = nil",
                "transition(to: .outcomeFailed",
            ],
            in: outcome
        )

        let retry = try sourceSlice(
            source,
            from: "func retryOutcome()",
            to: "func cancel()"
        )
        assertOrderedSource(
            [
                "case .outcomeFailed(let descriptor, let attempt, .retryable)",
                "let apiKey = pinnedAPIKey",
                "transition(to: .recording(descriptor, attempt))",
                "Task {",
                "await performOutcome",
            ],
            in: retry
        )
    }

    func testPublicGestureSourceClaimsStateBeforeLaunchingAsyncWork() throws {
        let source = try viewModelSource()
        for signature in [
            "func confirm()",
            "func retryHandoff()",
            "func acknowledge()",
            "func dismissResult()",
            "func retryOutcome()",
        ] {
            XCTAssertTrue(source.contains(signature), "Missing synchronous gesture: \(signature)")
            XCTAssertFalse(source.contains("\(signature) async"), signature)
        }

        let confirm = try sourceSlice(
            source,
            from: "func confirm()",
            to: "func retryHandoff()"
        )
        assertOrderedSource(
            [
                "case .selecting(let need?)",
                "let apiKey",
                "let generation = beginOperation()",
                "transition(to: .requesting(need))",
                "Task {",
                "await performHandoff",
            ],
            in: confirm
        )

        let retryHandoff = try sourceSlice(
            source,
            from: "func retryHandoff()",
            to: "func acknowledge()"
        )
        assertOrderedSource(
            [
                "case .handoffFailed(let need, .retryable)",
                "let apiKey = pinnedAPIKey",
                "let generation = beginOperation()",
                "transition(to: .requesting(need))",
                "Task {",
                "await performHandoff",
            ],
            in: retryHandoff
        )

        let firstOutcome = try sourceSlice(
            source,
            from: "private func recordFirstOutcome(_ outcome: FitChefSupportOutcome)",
            to: "private func performOutcome"
        )
        assertOrderedSource(
            [
                "case .presenting(let descriptor)",
                "let apiKey = pinnedAPIKey",
                "let attempt = FitChefSupportOutcomeAttempt(",
                "let generation = beginOperation()",
                "transition(to: .recording(descriptor, attempt))",
                "Task {",
                "await performOutcome",
            ],
            in: firstOutcome
        )

        let retryOutcome = try sourceSlice(
            source,
            from: "func retryOutcome()",
            to: "func cancel()"
        )
        assertOrderedSource(
            [
                "case .outcomeFailed(let descriptor, let attempt, .retryable)",
                "let apiKey = pinnedAPIKey",
                "let generation = beginOperation()",
                "transition(to: .recording(descriptor, attempt))",
                "Task {",
                "await performOutcome",
            ],
            in: retryOutcome
        )
    }

    func testLateHandoffCompletionCannotMutateNewLifecycle() async throws {
        let started = expectation(description: "handoff started")
        let service = FitChefSuspendingService(handoffStarted: started)
        let viewModel = makeViewModel(service: service)
        viewModel.select(.dailyStructure)

        viewModel.confirm()
        assertRequesting(viewModel.state, need: .dailyStructure)
        await fulfillment(of: [started], timeout: 2)
        viewModel.startNewLifecycle()
        service.resumeHandoff(.success(try makeDescriptor(need: .dailyStructure)))
        await drainMainActorTasks()

        assertSelecting(viewModel.state, need: nil)
        XCTAssertEqual(service.outcomeCalls.count, 0)
    }

    func testLateOutcomeCompletionCannotCompleteNewLifecycle() async throws {
        let outcomeStarted = expectation(description: "outcome started")
        let descriptor = try makeDescriptor(need: .weeklyStructure)
        let service = FitChefSuspendingService(
            immediateHandoff: descriptor,
            outcomeStarted: outcomeStarted
        )
        let viewModel = makeViewModel(service: service)
        viewModel.select(.weeklyStructure)
        viewModel.confirm()
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }

        viewModel.dismissResult()
        guard case .recording = viewModel.state else {
            XCTFail("Expected immediate recording state, got \(viewModel.state)")
            return
        }
        await fulfillment(of: [outcomeStarted], timeout: 2)
        viewModel.acknowledge()
        XCTAssertEqual(service.outcomeCalls.count, 1)
        viewModel.startNewLifecycle()
        service.resumeOutcome(.success(FitChefSupportOutcomeReceipt(state: .recorded)))
        await drainMainActorTasks()

        assertSelecting(viewModel.state, need: nil)
        XCTAssertEqual(service.outcomeCalls.count, 1)
    }

    private func makeViewModel(
        service: FitChefSupportServicing
    ) -> FitChefSupportFlowViewModel {
        FitChefSupportFlowViewModel(
            service: service,
            apiKeyProvider: { "credential-one" },
            makeClientEventID: { UUID(uuidString: fixedUUIDString)! }
        )
    }

    private func assertFirstOutcomeGestureClaimsSynchronously(
        firstOutcome: FitChefSupportOutcome
    ) async throws {
        let started = expectation(description: "outcome service started")
        let descriptor = try makeDescriptor(need: .dailyStructure)
        let service = FitChefSuspendingService(
            immediateHandoff: descriptor,
            outcomeStarted: started
        )
        let identifiers = UUIDSequence([UUID(uuidString: fixedUUIDString)!])
        let viewModel = FitChefSupportFlowViewModel(
            service: service,
            apiKeyProvider: { "credential-one" },
            makeClientEventID: { identifiers.next() }
        )
        viewModel.select(.dailyStructure)
        viewModel.confirm()
        assertRequesting(viewModel.state, need: .dailyStructure)
        await waitForState(viewModel) {
            if case .presenting = $0 { return true }
            return false
        }

        switch firstOutcome {
        case .acknowledged:
            viewModel.acknowledge()
        case .dismissed:
            viewModel.dismissResult()
        }
        guard case .recording(let claimedDescriptor, let claimedAttempt) = viewModel.state else {
            XCTFail("Expected immediate recording state, got \(viewModel.state)")
            return
        }
        XCTAssertEqual(claimedDescriptor, descriptor)
        XCTAssertEqual(claimedAttempt.supportNeed, .dailyStructure)
        XCTAssertEqual(claimedAttempt.outcome, firstOutcome)
        XCTAssertEqual(claimedAttempt.clientEventID, fixedUUIDString.lowercased())
        XCTAssertEqual(identifiers.readCount, 1)

        if firstOutcome == .acknowledged {
            viewModel.dismissResult()
            viewModel.acknowledge()
        } else {
            viewModel.acknowledge()
            viewModel.dismissResult()
        }
        assertRecording(
            viewModel.state,
            descriptor: descriptor,
            attempt: claimedAttempt
        )
        XCTAssertEqual(identifiers.readCount, 1)
        await fulfillment(of: [started], timeout: 2)
        XCTAssertEqual(service.outcomeCalls.count, 1)
        XCTAssertEqual(service.outcomeCalls[0].attempt, claimedAttempt)
        XCTAssertEqual(service.outcomeCalls[0].apiKey, "credential-one")

        service.resumeOutcome(
            .success(FitChefSupportOutcomeReceipt(state: .recorded))
        )
        await waitForState(viewModel) {
            if case .completed = $0 { return true }
            return false
        }
    }

    private func waitForState(
        _ viewModel: FitChefSupportFlowViewModel,
        maxYields: Int = 1_000,
        predicate: (FitChefSupportFlowState) -> Bool,
        file: StaticString = #filePath,
        line: UInt = #line
    ) async {
        for _ in 0..<maxYields {
            if predicate(viewModel.state) {
                return
            }
            await Task.yield()
        }
        XCTFail("Timed out waiting for state; current=\(viewModel.state)", file: file, line: line)
    }

    private func drainMainActorTasks(maxYields: Int = 100) async {
        for _ in 0..<maxYields {
            await Task.yield()
        }
    }

    private func viewModelSource() throws -> String {
        var candidate = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        while candidate.path != "/" {
            if FileManager.default.fileExists(
                atPath: candidate.appendingPathComponent(".git").path
            ) {
                return try String(
                    contentsOf: candidate.appendingPathComponent(
                        "ios/PulsePlate/ViewModels/FitChefSupportFlowViewModel.swift"
                    ),
                    encoding: .utf8
                )
            }
            candidate = candidate.deletingLastPathComponent()
        }
        throw FitChefRuntimeTestError.repositoryRootNotFound
    }

    private func sourceSlice(
        _ source: String,
        from start: String,
        to end: String
    ) throws -> String {
        let startIndex = try XCTUnwrap(source.range(of: start)?.lowerBound)
        let remainder = source[startIndex...]
        let endIndex = try XCTUnwrap(remainder.range(of: end)?.lowerBound)
        return String(source[startIndex..<endIndex])
    }

    private func assertOrderedSource(
        _ values: [String],
        in source: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        var lowerBound = source.startIndex
        for value in values {
            guard let range = source.range(of: value, range: lowerBound..<source.endIndex) else {
                XCTFail("Missing or out-of-order source value: \(value)", file: file, line: line)
                return
            }
            lowerBound = range.upperBound
        }
    }

    private func assertSelecting(
        _ state: FitChefSupportFlowState,
        need: FitChefSupportNeed?,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard case .selecting(let selectedNeed) = state else {
            XCTFail("Expected selecting state, got \(state)", file: file, line: line)
            return
        }
        XCTAssertEqual(selectedNeed, need, file: file, line: line)
    }

    private func assertRequesting(
        _ state: FitChefSupportFlowState,
        need: FitChefSupportNeed,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard case .requesting(let actualNeed) = state else {
            XCTFail("Expected requesting state, got \(state)", file: file, line: line)
            return
        }
        XCTAssertEqual(actualNeed, need, file: file, line: line)
    }

    private func assertRecording(
        _ state: FitChefSupportFlowState,
        descriptor: FitChefSupportHandoffDescriptor,
        attempt: FitChefSupportOutcomeAttempt,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard case .recording(let actualDescriptor, let actualAttempt) = state else {
            XCTFail("Expected recording state, got \(state)", file: file, line: line)
            return
        }
        XCTAssertEqual(actualDescriptor, descriptor, file: file, line: line)
        XCTAssertEqual(actualAttempt, attempt, file: file, line: line)
    }

    private func assertHandoffFailure(
        _ state: FitChefSupportFlowState,
        need: FitChefSupportNeed,
        failure: FitChefSupportFlowFailure,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard case .handoffFailed(let actualNeed, let actualFailure) = state else {
            XCTFail("Expected handoffFailed state, got \(state)", file: file, line: line)
            return
        }
        XCTAssertEqual(actualNeed, need, file: file, line: line)
        XCTAssertEqual(actualFailure, failure, file: file, line: line)
    }
}

final class FitChefSupportPresentationContractTests: XCTestCase {
    func testFlowLocalizationKeySetsAndConsumerCopyAreExactAcrossENRUES() throws {
        let expected: [String: [String: String]] = [
            "en": [
                "fitchef.support_flow.loading": "Getting things ready…",
                "fitchef.support_flow.result.title": "Your next focus",
                "fitchef.support_flow.result.target_label": "Start with",
                "fitchef.support_flow.result.target.daily": "Today",
                "fitchef.support_flow.result.target.weekly": "This week",
                "fitchef.support_flow.result.boundary":
                    "Nothing opens or changes automatically.",
                "fitchef.support_flow.result.response_notice":
                    "Choose Thanks or Not now. Your response will be saved.",
                "fitchef.support_flow.action.acknowledge": "Thanks",
                "fitchef.support_flow.action.dismiss": "Not now",
                "fitchef.support_flow.recording": "Saving your response…",
                "fitchef.support_flow.recorded": "Your response was saved.",
                "fitchef.support_flow.replayed": "This response was already saved.",
                "fitchef.support_flow.handoff_failed":
                    "We couldn't load the next step.",
                "fitchef.support_flow.unavailable":
                    "This option isn't available right now.",
                "fitchef.support_flow.outcome_retryable":
                    "We couldn't confirm whether your response was saved. Try again when you're ready.",
                "fitchef.support_flow.outcome_restart":
                    "We couldn't save your response. Close this screen and start again.",
                "fitchef.support_flow.outcome_terminal":
                    "We couldn't save your response. Close this screen.",
                "fitchef.support_flow.action.retry": "Try again",
                "fitchef.support_flow.action.close": "Close",
                "fitchef.support_flow.action.done": "Done",
            ],
            "ru": [
                "fitchef.support_flow.loading": "Готовим следующий шаг…",
                "fitchef.support_flow.result.title": "На чем сосредоточиться",
                "fitchef.support_flow.result.target_label": "Начать с",
                "fitchef.support_flow.result.target.daily": "Сегодня",
                "fitchef.support_flow.result.target.weekly": "Неделя",
                "fitchef.support_flow.result.boundary":
                    "Ничего не откроется и не изменится автоматически.",
                "fitchef.support_flow.result.response_notice":
                    "Выберите «Спасибо» или «Не сейчас». Ваш ответ будет сохранен.",
                "fitchef.support_flow.action.acknowledge": "Спасибо",
                "fitchef.support_flow.action.dismiss": "Не сейчас",
                "fitchef.support_flow.recording": "Сохраняем ответ…",
                "fitchef.support_flow.recorded": "Ответ сохранен.",
                "fitchef.support_flow.replayed": "Этот ответ уже был сохранен.",
                "fitchef.support_flow.handoff_failed":
                    "Не удалось загрузить следующий шаг.",
                "fitchef.support_flow.unavailable":
                    "Сейчас этот вариант недоступен.",
                "fitchef.support_flow.outcome_retryable":
                    "Не удалось подтвердить, был ли сохранен ваш ответ. Повторите попытку, когда будете готовы.",
                "fitchef.support_flow.outcome_restart":
                    "Не удалось сохранить ответ. Закройте экран и начните заново.",
                "fitchef.support_flow.outcome_terminal":
                    "Не удалось сохранить ответ. Закройте этот экран.",
                "fitchef.support_flow.action.retry": "Повторить",
                "fitchef.support_flow.action.close": "Закрыть",
                "fitchef.support_flow.action.done": "Готово",
            ],
            "es": [
                "fitchef.support_flow.loading": "Preparando el siguiente paso…",
                "fitchef.support_flow.result.title": "Tu próximo enfoque",
                "fitchef.support_flow.result.target_label": "Empieza por",
                "fitchef.support_flow.result.target.daily": "Hoy",
                "fitchef.support_flow.result.target.weekly": "Esta semana",
                "fitchef.support_flow.result.boundary":
                    "Nada se abre ni cambia automáticamente.",
                "fitchef.support_flow.result.response_notice":
                    "Elige «Gracias» o «Ahora no». Tu respuesta se guardará.",
                "fitchef.support_flow.action.acknowledge": "Gracias",
                "fitchef.support_flow.action.dismiss": "Ahora no",
                "fitchef.support_flow.recording": "Guardando tu respuesta…",
                "fitchef.support_flow.recorded": "Tu respuesta se guardó.",
                "fitchef.support_flow.replayed": "Esta respuesta ya estaba guardada.",
                "fitchef.support_flow.handoff_failed":
                    "No pudimos cargar el siguiente paso.",
                "fitchef.support_flow.unavailable":
                    "Esta opción no está disponible ahora.",
                "fitchef.support_flow.outcome_retryable":
                    "No pudimos confirmar si tu respuesta se guardó. Inténtalo de nuevo cuando quieras.",
                "fitchef.support_flow.outcome_restart":
                    "No pudimos guardar tu respuesta. Cierra esta pantalla y vuelve a empezar.",
                "fitchef.support_flow.outcome_terminal":
                    "No pudimos guardar tu respuesta. Cierra esta pantalla.",
                "fitchef.support_flow.action.retry": "Intentar de nuevo",
                "fitchef.support_flow.action.close": "Cerrar",
                "fitchef.support_flow.action.done": "Listo",
            ],
        ]

        let expectedKeys = try XCTUnwrap(expected["en"]).keys
        let retiredDefinitePlanCopy: Set<String> = [
            "Start with the plan for today.",
            "Сначала разобраться с планом на день.",
            "Empezar por el plan de hoy.",
        ]
        let retiredFlowOverclaims: Set<String> = [
            "FitChef support result",
            "Choose Acknowledge or Dismiss. Only that response is recorded.",
            "Результат поддержки FitChef",
            "Выберите «Принять к сведению» или «Отклонить». Будет записан только этот ответ.",
            "Resultado de ayuda de FitChef",
            "Elige «Tomar nota» o «Descartar». Solo se registra esa respuesta.",
        ]
        XCTAssertEqual(expectedKeys.count, 20)
        for locale in ["en", "ru", "es"] {
            let actual = try loadFlowLocalization(locale: locale)
            XCTAssertEqual(Set(actual.keys), Set(expectedKeys), locale)
            XCTAssertEqual(actual, expected[locale], locale)
            XCTAssertTrue(retiredFlowOverclaims.isDisjoint(with: actual.values), locale)
            for forbidden in [
                "support", "handoff", "target_surface", "endpoint", "route", "outcome",
                "client_event_id", "credential", "entitlement", "consent", "acknowledge",
                "dismiss", "recorded", "replayed", "pro_daily_plate", "pro_weekly_plan",
                "only keep", "only save", "only store",
                "поддержк", "передач", "маршрут", "эндпоинт", "исход", "идентификатор",
                "учетн", "право доступа", "соглас", "отклон", "записан", "только этот ответ",
                "ayuda", "traspaso", "destino", "ruta", "resultado", "credencial",
                "derecho", "consentimiento", "descartar", "registrad", "solo se guarda",
            ] {
                XCTAssertTrue(
                    actual.values.allSatisfy { !$0.localizedCaseInsensitiveContains(forbidden) },
                    "Forbidden internal or inflated meaning in \(locale): \(forbidden)"
                )
            }

            let choice = try loadChoiceLocalization(locale: locale)
            XCTAssertTrue(retiredDefinitePlanCopy.isDisjoint(with: choice.values), locale)
            XCTAssertEqual(
                actual["fitchef.support_flow.result.target.daily"],
                choice["fitchef.support_choice.daily.title"],
                locale
            )
            XCTAssertEqual(
                actual["fitchef.support_flow.result.target.weekly"],
                choice["fitchef.support_choice.weekly.title"],
                locale
            )
        }
    }

    func testCapabilityIsAbsentFromHomeFeatureFlagsAndHomeLocalization() throws {
        let featureFlags = try source(at: "ios/PulsePlate/Utilities/FeatureFlags.swift")
        let home = try source(at: "ios/PulsePlate/Views/HomeView.swift")

        for forbidden in [
            "fitChefSupportOutcomeFlowEnabled",
            "FITCHEF_SUPPORT_OUTCOME_FLOW_ENABLED",
            "FitChefSupportFlowScreen",
        ] {
            XCTAssertFalse(featureFlags.contains(forbidden), forbidden)
        }
        for forbidden in [
            "fitChefSupportOutcomeFlowEnabled",
            "FITCHEF_SUPPORT_OUTCOME_FLOW_ENABLED",
            "FitChefSupportFlowScreen",
            "makeFitChefSupportFlowScreen",
            "home.action.fitchef_support",
        ] {
            XCTAssertFalse(home.contains(forbidden), forbidden)
        }

        for locale in ["en", "ru", "es"] {
            let values = try loadLocalization(locale: locale)
            XCTAssertTrue(
                values.keys.allSatisfy { !$0.hasPrefix("home.action.fitchef_support.") },
                locale
            )
        }
    }

    func testNoProductionSwiftOutsideTheFeatureFileConstructsFlowScreen() throws {
        let root = try repositoryRoot().appendingPathComponent("ios/PulsePlate")
        let flowScreenPath = "/Views/FitChef/FitChefSupportFlowScreen.swift"
        let constructions = try swiftSources(under: root)
            .filter { !$0.path.hasSuffix(flowScreenPath) }
            .compactMap { url -> String? in
                let value = try String(contentsOf: url, encoding: .utf8)
                return value.contains("FitChefSupportFlowScreen(") ? url.path : nil
            }

        XCTAssertEqual(constructions, [])
    }

    func testEveryFlowScreenConstructionIsConfinedToSameFileDEBUGPreviews() throws {
        let source = try source(
            at: "ios/PulsePlate/Views/FitChef/FitChefSupportFlowScreen.swift"
        )
        let debugStart = try XCTUnwrap(source.range(of: "#if DEBUG")?.lowerBound)
        let productionPrefix = String(source[..<debugStart])
        let debugSuffix = String(source[debugStart...])

        XCTAssertEqual(
            occurrenceCount(of: "FitChefSupportFlowScreen(", in: productionPrefix),
            0
        )
        let debugConstructions = occurrenceCount(
            of: "FitChefSupportFlowScreen(",
            in: debugSuffix
        )
        XCTAssertGreaterThan(debugConstructions, 0)
        XCTAssertEqual(
            occurrenceCount(of: "FitChefSupportFlowScreen(", in: source),
            debugConstructions
        )
    }

    func testDEBUGPreviewServiceEchoesRequestedNeedAcrossBothDiagonalFixtures() throws {
        let source = try source(
            at: "ios/PulsePlate/Views/FitChef/FitChefSupportFlowScreen.swift"
        )
        let debugStart = try XCTUnwrap(source.range(of: "#if DEBUG")?.lowerBound)
        let debug = String(source[debugStart...])
        let previewService = try slice(
            debug,
            from: "private struct FitChefSupportPreviewService",
            to: "private enum FitChefSupportFlowPreviewFixtures"
        )

        XCTAssertTrue(previewService.contains("let dailyDescriptor"))
        XCTAssertTrue(previewService.contains("let weeklyDescriptor"))
        assertOrdered(
            [
                "switch supportNeed",
                "case .dailyStructure:",
                "return dailyDescriptor",
                "case .weeklyStructure:",
                "return weeklyDescriptor",
            ],
            in: previewService
        )
        XCTAssertFalse(
            previewService.contains(
                "case .weeklyStructure:\n            return dailyDescriptor"
            )
        )

        XCTAssertEqual(
            occurrenceCount(of: "\"support_need\": \"daily_structure\"", in: debug),
            1
        )
        XCTAssertEqual(
            occurrenceCount(of: "\"target_surface\": \"pro_daily_plate\"", in: debug),
            1
        )
        XCTAssertEqual(
            occurrenceCount(of: "\"support_need\": \"weekly_structure\"", in: debug),
            1
        )
        XCTAssertEqual(
            occurrenceCount(of: "\"target_surface\": \"pro_weekly_plan\"", in: debug),
            1
        )
    }

    func testTargetIsPlainTextAndFitChefScreenHasNoNavigationOrMutationAuthority() throws {
        let source = try source(
            at: "ios/PulsePlate/Views/FitChef/FitChefSupportFlowScreen.swift"
        )

        assertOrdered(
            [
                "fitchef.support_flow.result.title",
                "fitchef.support_flow.result.target_label",
                "viewModel.targetDisplayKey",
                "fitchef.support_flow.result.boundary",
                "fitchef.support_flow.result.response_notice",
                "fitchef.support_flow.action.acknowledge",
                "fitchef.support_flow.action.dismiss",
            ],
            in: source
        )
        XCTAssertTrue(source.contains("Text(localized(viewModel.targetDisplayKey))"))
        XCTAssertTrue(source.contains("PPCard"))
        XCTAssertTrue(source.contains("PPButton"))
        XCTAssertTrue(source.contains("PPAccessibility.minimumTouchTarget"))
        XCTAssertTrue(source.contains(".defaultScrollAnchor(.top)"))
        XCTAssertTrue(source.contains("if #available(iOS 18.0, *)"))
        XCTAssertTrue(source.contains("for: .alignment"))
        XCTAssertTrue(source.contains(".onDisappear"))
        XCTAssertTrue(source.contains("viewModel.cancel()"))

        for forbidden in [
            "NavigationLink", "navigationDestination", "openURL", "UIApplication.shared",
            "onTapGesture", ".isLink", ".isButton", "PlateView", "WeeklyPlan",
            "UserDefaults", "@AppStorage", "FileManager", "KeychainStore",
            "NotificationCenter", "Analytics", "analytics", ".save(", ".write(",
            ".isSelected", ".isAdjustable", "targetSurface.rawValue",
        ] {
            XCTAssertFalse(source.contains(forbidden), "Forbidden flow authority: \(forbidden)")
        }
    }

    func testScreenButtonsCallSynchronousGestureMethodsWithoutDelayedClaimTasks() throws {
        let source = try source(
            at: "ios/PulsePlate/Views/FitChef/FitChefSupportFlowScreen.swift"
        )
        let debugStart = try XCTUnwrap(source.range(of: "#if DEBUG")?.lowerBound)
        let production = String(source[..<debugStart])

        for call in [
            "viewModel.confirm()",
            "viewModel.retryHandoff()",
            "viewModel.acknowledge()",
            "viewModel.dismissResult()",
            "viewModel.retryOutcome()",
        ] {
            XCTAssertTrue(production.contains(call), "Missing direct gesture call: \(call)")
        }
        for delayedClaim in [
            "Task { await viewModel.confirm() }",
            "Task { await viewModel.retryHandoff() }",
            "Task { await viewModel.acknowledge() }",
            "Task { await viewModel.dismissResult() }",
            "Task { await viewModel.retryOutcome() }",
        ] {
            XCTAssertFalse(
                production.contains(delayedClaim),
                "Gesture claim must not be delayed: \(delayedClaim)"
            )
        }
    }

    func testFeatureLocalRuntimeUsesOnlyAPIClientAndHasNoDurableRetryOrAnalyticsRail() throws {
        let service = try source(
            at: "ios/PulsePlate/Services/FitChefSupportService.swift"
        )
        let viewModel = try source(
            at: "ios/PulsePlate/ViewModels/FitChefSupportFlowViewModel.swift"
        )

        XCTAssertTrue(service.contains("APIClientProtocol"))
        XCTAssertTrue(service.contains("let response: JSONValue"))
        XCTAssertTrue(service.contains("apiClient.post("))
        XCTAssertTrue(service.contains("decoder.keyDecodingStrategy = .useDefaultKeys"))
        XCTAssertTrue(service.contains("encoder.outputFormatting = [.sortedKeys]"))
        XCTAssertTrue(
            service.contains(
                "Duplicate raw JSON member detection is outside this post-transport recognizer."
            )
        )
        XCTAssertFalse(service.contains("postRaw"))
        for source in [service, viewModel] {
            for forbidden in [
                "URLSession", "HTTPClient(", "UserDefaults", "@AppStorage", "FileManager",
                "KeychainStore", "NotificationCenter", "Analytics", "analytics",
                "Timer", "Task.sleep", "DispatchQueue.asyncAfter", "background",
                "outbox", "beacon",
            ] {
                XCTAssertFalse(source.contains(forbidden), "Forbidden retry/storage rail: \(forbidden)")
            }
        }
        XCTAssertFalse(viewModel.contains("localizedDescription"))
        XCTAssertFalse(viewModel.contains("errorDescription"))
        XCTAssertFalse(viewModel.contains("String(describing: error)"))
    }

    func testFlowSourceIncludesDeterministicNoNetworkPreviewsForEveryMaterialState() throws {
        let source = try source(
            at: "ios/PulsePlate/Views/FitChef/FitChefSupportFlowScreen.swift"
        )
        for preview in [
            "Selection", "Requesting", "Result", "Recording", "Recorded", "Replayed",
            "Retryable failure", "Restart required", "Terminal failure",
        ] {
            XCTAssertTrue(source.contains(preview), "Missing deterministic preview: \(preview)")
        }
        XCTAssertTrue(source.contains("FitChefSupportPreviewService"))
        XCTAssertFalse(source.contains("APIClient(baseURL:"))
        XCTAssertTrue(source.contains(".dynamicTypeSize(.accessibility5)"))
        XCTAssertTrue(source.contains("Locale(identifier: \"es\")"))
        XCTAssertTrue(source.contains("traits: .fixedLayout(width: 390, height: 844)"))
        XCTAssertTrue(source.contains("traits: .fixedLayout(width: 834, height: 1194)"))
    }

    private func loadFlowLocalization(locale: String) throws -> [String: String] {
        try loadLocalization(locale: locale).filter {
            $0.key.hasPrefix("fitchef.support_flow.")
        }
    }

    private func loadChoiceLocalization(locale: String) throws -> [String: String] {
        try loadLocalization(locale: locale).filter {
            $0.key.hasPrefix("fitchef.support_choice.")
        }
    }

    private func loadLocalization(locale: String) throws -> [String: String] {
        let url = try repositoryRoot()
            .appendingPathComponent("ios/PulsePlate")
            .appendingPathComponent("\(locale).lproj")
            .appendingPathComponent("Localizable.strings")
        let data = try Data(contentsOf: url)
        let plist = try PropertyListSerialization.propertyList(
            from: data,
            options: [],
            format: nil
        )
        let values = try XCTUnwrap(plist as? [String: String])
        return values
    }

    private func swiftSources(under root: URL) throws -> [URL] {
        guard let enumerator = FileManager.default.enumerator(
            at: root,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        ) else {
            throw FitChefRuntimeTestError.sourceEnumerationUnavailable
        }

        var sources: [URL] = []
        while let url = enumerator.nextObject() as? URL {
            guard url.pathExtension == "swift" else { continue }
            let values = try url.resourceValues(forKeys: [.isRegularFileKey])
            if values.isRegularFile == true {
                sources.append(url)
            }
        }
        return sources.sorted { $0.path < $1.path }
    }

    private func source(at relativePath: String) throws -> String {
        try String(
            contentsOf: try repositoryRoot().appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    private func repositoryRoot() throws -> URL {
        var candidate = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        while candidate.path != "/" {
            if FileManager.default.fileExists(
                atPath: candidate.appendingPathComponent(".git").path
            ) {
                return candidate
            }
            candidate = candidate.deletingLastPathComponent()
        }
        throw FitChefRuntimeTestError.repositoryRootNotFound
    }

    private func assertOrdered(
        _ values: [String],
        in source: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        var lowerBound = source.startIndex
        for value in values {
            guard let range = source.range(of: value, range: lowerBound..<source.endIndex) else {
                XCTFail("Missing or out-of-order source value: \(value)", file: file, line: line)
                return
            }
            lowerBound = range.upperBound
        }
    }

    private func slice(_ source: String, from start: String, to end: String) throws -> String {
        let startIndex = try XCTUnwrap(source.range(of: start)?.lowerBound)
        let remainder = source[startIndex...]
        let endIndex = try XCTUnwrap(remainder.range(of: end)?.lowerBound)
        return String(source[startIndex..<endIndex])
    }

    private func occurrenceCount(of value: String, in source: String) -> Int {
        source.components(separatedBy: value).count - 1
    }

}

private let fixedUUIDString = "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF"

private func fixedAttempt() -> FitChefSupportOutcomeAttempt {
    FitChefSupportOutcomeAttempt(
        supportNeed: .dailyStructure,
        outcome: .acknowledged,
        clientEventID: fixedUUIDString.lowercased()
    )
}

private func canonicalHandoffValue(
    need: FitChefSupportNeed,
    target: FitChefSupportTargetSurface
) -> JSONValue {
    .object([
        "schema_version": .string("fitchef_support_handoff.v1"),
        "scenario": .string("support_handoff"),
        "support_need": .string(need.rawValue),
        "action": .object([
            "action_type": .string("handoff_to_product_surface"),
            "target_surface": .string(target.rawValue),
        ]),
        "user_confirmation_required": .bool(true),
        "execution_authority": .bool(false),
        "plan_mutation_authority": .bool(false),
        "used_llm": .bool(false),
        "wellness_boundary": .string("wellness_planning_only"),
    ])
}

private func canonicalOutcomeReceiptValue(
    state: FitChefSupportOutcomeState
) -> JSONValue {
    .object([
        "schema_version": .string("fitchef_support_outcome_v1"),
        "state": .string(state.rawValue),
    ])
}

private func makeDescriptor(
    need: FitChefSupportNeed
) throws -> FitChefSupportHandoffDescriptor {
    let target: FitChefSupportTargetSurface = need == .dailyStructure
        ? .proDailyPlate
        : .proWeeklyPlan
    let data = try JSONEncoder().encode(canonicalHandoffValue(need: need, target: target))
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .useDefaultKeys
    return try decoder.decode(FitChefSupportHandoffDescriptor.self, from: data)
}

private struct FitChefCapturedRequest {
    let path: String
    let headers: [String: String]
    let body: [String: Any]
}

// Test-only transport double. Mutable state is protected by NSLock.
private final class FitChefCapturingAPIClient: APIClientProtocol, @unchecked Sendable {
    private let lock = NSLock()
    private var responseQueue: [Result<JSONValue, Error>]
    private var capturedRequests: [FitChefCapturedRequest] = []
    private var capturedPostRawCallCount = 0

    init(responses: [Result<JSONValue, Error>]) {
        responseQueue = responses
    }

    var requests: [FitChefCapturedRequest] {
        withLock { capturedRequests }
    }

    var postRawCallCount: Int {
        withLock { capturedPostRawCallCount }
    }

    func postRaw<Response: Decodable>(
        path: String,
        body: Data,
        headers: [String: String]
    ) async throws -> Response {
        withLock { capturedPostRawCallCount += 1 }
        throw APIError.unknown("postRaw is outside the FitChef support contract")
    }

    func post<Response: Decodable, Body: Encodable>(
        path: String,
        body: Body,
        headers: [String: String]
    ) async throws -> Response {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        let data = try encoder.encode(body)
        let object = try JSONSerialization.jsonObject(with: data)
        guard let dictionary = object as? [String: Any] else {
            throw APIError.encodingFailed("Expected object request body")
        }

        let result: Result<JSONValue, Error> = withLock {
            capturedRequests.append(
                FitChefCapturedRequest(path: path, headers: headers, body: dictionary)
            )
            guard !responseQueue.isEmpty else {
                return .failure(APIError.unknown("Missing scripted response"))
            }
            return responseQueue.removeFirst()
        }
        let value = try result.get()
        guard Response.self == JSONValue.self else {
            throw APIError.decodingFailed("FitChef service must request JSONValue")
        }
        // The generic protocol requires the test double to return the requested concrete type.
        return value as! Response
    }

    func get<Response: Decodable>(
        path: String,
        headers: [String: String]
    ) async throws -> Response {
        throw APIError.unknown("GET is outside the FitChef support contract")
    }

    private func withLock<T>(_ operation: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return operation()
    }
}

private struct FitChefHandoffCall: Equatable {
    let need: FitChefSupportNeed
    let apiKey: String
}

private struct FitChefOutcomeCall: Equatable {
    let attempt: FitChefSupportOutcomeAttempt
    let apiKey: String
}

// Test-only service double. Mutable state is protected by NSLock.
private final class FitChefRecordingService: FitChefSupportServicing, @unchecked Sendable {
    private let lock = NSLock()
    private var handoffQueue: [Result<FitChefSupportHandoffDescriptor, Error>]
    private var outcomeQueue: [Result<FitChefSupportOutcomeReceipt, Error>]
    private var capturedHandoffCalls: [FitChefHandoffCall] = []
    private var capturedOutcomeCalls: [FitChefOutcomeCall] = []

    init(
        handoffResults: [Result<FitChefSupportHandoffDescriptor, Error>] = [],
        outcomeResults: [Result<FitChefSupportOutcomeReceipt, Error>] = []
    ) {
        handoffQueue = handoffResults
        outcomeQueue = outcomeResults
    }

    var handoffCalls: [FitChefHandoffCall] {
        withLock { capturedHandoffCalls }
    }

    var outcomeCalls: [FitChefOutcomeCall] {
        withLock { capturedOutcomeCalls }
    }

    func requestHandoff(
        for supportNeed: FitChefSupportNeed,
        apiKey: String
    ) async throws -> FitChefSupportHandoffDescriptor {
        let result: Result<FitChefSupportHandoffDescriptor, Error> = withLock {
            capturedHandoffCalls.append(
                FitChefHandoffCall(need: supportNeed, apiKey: apiKey)
            )
            guard !handoffQueue.isEmpty else {
                return .failure(APIError.unknown("Missing scripted handoff"))
            }
            return handoffQueue.removeFirst()
        }
        return try result.get()
    }

    func recordOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        apiKey: String
    ) async throws -> FitChefSupportOutcomeReceipt {
        let result: Result<FitChefSupportOutcomeReceipt, Error> = withLock {
            capturedOutcomeCalls.append(
                FitChefOutcomeCall(attempt: attempt, apiKey: apiKey)
            )
            guard !outcomeQueue.isEmpty else {
                return .failure(APIError.unknown("Missing scripted outcome"))
            }
            return outcomeQueue.removeFirst()
        }
        return try result.get()
    }

    private func withLock<T>(_ operation: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return operation()
    }
}

// Test-only continuation service. Access to continuations and calls is lock-protected.
private final class FitChefSuspendingService: FitChefSupportServicing, @unchecked Sendable {
    private let lock = NSLock()
    private let immediateHandoff: FitChefSupportHandoffDescriptor?
    private let handoffStarted: XCTestExpectation?
    private let outcomeStarted: XCTestExpectation?
    private var handoffContinuation:
        CheckedContinuation<FitChefSupportHandoffDescriptor, Error>?
    private var outcomeContinuation:
        CheckedContinuation<FitChefSupportOutcomeReceipt, Error>?
    private var capturedHandoffCalls: [FitChefHandoffCall] = []
    private var capturedOutcomeCalls: [FitChefOutcomeCall] = []

    init(
        immediateHandoff: FitChefSupportHandoffDescriptor? = nil,
        handoffStarted: XCTestExpectation? = nil,
        outcomeStarted: XCTestExpectation? = nil
    ) {
        self.immediateHandoff = immediateHandoff
        self.handoffStarted = handoffStarted
        self.outcomeStarted = outcomeStarted
    }

    var handoffCalls: [FitChefHandoffCall] {
        withLock { capturedHandoffCalls }
    }

    var outcomeCalls: [FitChefOutcomeCall] {
        withLock { capturedOutcomeCalls }
    }

    func requestHandoff(
        for supportNeed: FitChefSupportNeed,
        apiKey: String
    ) async throws -> FitChefSupportHandoffDescriptor {
        withLock {
            capturedHandoffCalls.append(
                FitChefHandoffCall(need: supportNeed, apiKey: apiKey)
            )
        }
        if let immediateHandoff {
            return immediateHandoff
        }
        return try await withCheckedThrowingContinuation { continuation in
            withLock { handoffContinuation = continuation }
            handoffStarted?.fulfill()
        }
    }

    func recordOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        apiKey: String
    ) async throws -> FitChefSupportOutcomeReceipt {
        return try await withCheckedThrowingContinuation { continuation in
            withLock {
                capturedOutcomeCalls.append(
                    FitChefOutcomeCall(attempt: attempt, apiKey: apiKey)
                )
                outcomeContinuation = continuation
            }
            outcomeStarted?.fulfill()
        }
    }

    func resumeHandoff(
        _ result: Result<FitChefSupportHandoffDescriptor, Error>
    ) {
        let continuation = withLock {
            let value = handoffContinuation
            handoffContinuation = nil
            return value
        }
        continuation?.resume(with: result)
    }

    func resumeOutcome(
        _ result: Result<FitChefSupportOutcomeReceipt, Error>
    ) {
        let continuation = withLock {
            let value = outcomeContinuation
            outcomeContinuation = nil
            return value
        }
        continuation?.resume(with: result)
    }

    private func withLock<T>(_ operation: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return operation()
    }
}

private enum FitChefRetryClaimMode {
    case handoff(FitChefSupportHandoffDescriptor)
    case outcome(FitChefSupportHandoffDescriptor)
}

// Test-only retry double. First eligible call fails; retry suspends until the test resumes it.
private final class FitChefRetryClaimService: FitChefSupportServicing, @unchecked Sendable {
    private let lock = NSLock()
    private let mode: FitChefRetryClaimMode
    private let retryStarted: XCTestExpectation
    private var retryHandoffContinuation:
        CheckedContinuation<FitChefSupportHandoffDescriptor, Error>?
    private var retryOutcomeContinuation:
        CheckedContinuation<FitChefSupportOutcomeReceipt, Error>?
    private var capturedHandoffCalls: [FitChefHandoffCall] = []
    private var capturedOutcomeCalls: [FitChefOutcomeCall] = []

    init(mode: FitChefRetryClaimMode, retryStarted: XCTestExpectation) {
        self.mode = mode
        self.retryStarted = retryStarted
    }

    var handoffCalls: [FitChefHandoffCall] {
        withLock { capturedHandoffCalls }
    }

    var outcomeCalls: [FitChefOutcomeCall] {
        withLock { capturedOutcomeCalls }
    }

    func requestHandoff(
        for supportNeed: FitChefSupportNeed,
        apiKey: String
    ) async throws -> FitChefSupportHandoffDescriptor {
        let callNumber = withLock {
            capturedHandoffCalls.append(
                FitChefHandoffCall(need: supportNeed, apiKey: apiKey)
            )
            return capturedHandoffCalls.count
        }
        switch mode {
        case .handoff:
            if callNumber == 1 {
                throw APIError.transport("first handoff fails")
            }
            return try await withCheckedThrowingContinuation { continuation in
                withLock { retryHandoffContinuation = continuation }
                retryStarted.fulfill()
            }
        case .outcome(let descriptor):
            return descriptor
        }
    }

    func recordOutcome(
        _ attempt: FitChefSupportOutcomeAttempt,
        apiKey: String
    ) async throws -> FitChefSupportOutcomeReceipt {
        let callNumber = withLock {
            capturedOutcomeCalls.append(
                FitChefOutcomeCall(attempt: attempt, apiKey: apiKey)
            )
            return capturedOutcomeCalls.count
        }
        guard case .outcome = mode else {
            throw APIError.unknown("Outcome is outside this retry scenario")
        }
        if callNumber == 1 {
            throw APIError.transport("first outcome fails")
        }
        return try await withCheckedThrowingContinuation { continuation in
            withLock { retryOutcomeContinuation = continuation }
            retryStarted.fulfill()
        }
    }

    func resumeRetryHandoff(
        _ result: Result<FitChefSupportHandoffDescriptor, Error>
    ) {
        let continuation = withLock {
            let value = retryHandoffContinuation
            retryHandoffContinuation = nil
            return value
        }
        continuation?.resume(with: result)
    }

    func resumeRetryOutcome(
        _ result: Result<FitChefSupportOutcomeReceipt, Error>
    ) {
        let continuation = withLock {
            let value = retryOutcomeContinuation
            retryOutcomeContinuation = nil
            return value
        }
        continuation?.resume(with: result)
    }

    private func withLock<T>(_ operation: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return operation()
    }
}

// Test-only credential sequence. Mutable state is protected by NSLock.
private final class CredentialSequence: @unchecked Sendable {
    private let lock = NSLock()
    private let values: [String]
    private var index = 0

    init(_ values: [String]) {
        self.values = values
    }

    var readCount: Int {
        withLock { index }
    }

    func next() -> String? {
        withLock {
            guard index < values.count else { return nil }
            defer { index += 1 }
            return values[index]
        }
    }

    private func withLock<T>(_ operation: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return operation()
    }
}

// Test-only UUID sequence. Mutable state is protected by NSLock.
private final class UUIDSequence: @unchecked Sendable {
    private let lock = NSLock()
    private let values: [UUID]
    private var index = 0

    init(_ values: [UUID]) {
        self.values = values
    }

    var readCount: Int {
        withLock { index }
    }

    func next() -> UUID {
        withLock {
            precondition(index < values.count, "Unexpected UUID generation")
            defer { index += 1 }
            return values[index]
        }
    }

    private func withLock<T>(_ operation: () -> T) -> T {
        lock.lock()
        defer { lock.unlock() }
        return operation()
    }
}

private enum FitChefRuntimeTestError: Error {
    case repositoryRootNotFound
    case sourceEnumerationUnavailable
}
