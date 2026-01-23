import Foundation
@testable import PulsePlate

/// Mock BMI service for testing (uses legacy types for backward compatibility with existing tests).
/// TODO: Update to use BMICalculate*DTO after UI migration (tracked in BACKLOG_LEDGER.md)
final class MockBMIService: LegacyBMIServicing {
    var result: Result<BMIResponse, Error> = .failure(BMIServiceError.transport("not set"))

    func calculateBMI(request: BMIRequest) async throws -> BMIResponse {
        switch result {
        case .success(let v): return v
        case .failure(let e): throw e
        }
    }
}

// Test-only mock; used from a single thread in unit tests, so @unchecked Sendable is safe.
extension MockBMIService: @unchecked Sendable {}
