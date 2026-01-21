import Foundation
@testable import PulsePlate

final class MockBMIService: BMIServicing {
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
