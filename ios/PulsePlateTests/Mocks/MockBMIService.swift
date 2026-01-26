import Foundation
@testable import PulsePlate

/// Mock BMI service for testing (thin DTO boundary only).
final class MockBMIService: BMIServicing {
    var result: Result<BMICalculateResponseDTO, Error> = .failure(APIError.api(statusCode: 500, message: "not set"))

    func calculateBMI(request: BMICalculateRequestDTO) async throws -> BMICalculateResponseDTO {
        switch result {
        case .success(let v): return v
        case .failure(let e): throw e
        }
    }
}

// Test-only mock; used from a single thread in unit tests, so @unchecked Sendable is safe.
extension MockBMIService: @unchecked Sendable {}
