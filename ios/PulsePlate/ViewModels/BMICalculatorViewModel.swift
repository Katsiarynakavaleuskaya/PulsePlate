import Foundation
import Combine

@MainActor
final class BMICalculatorViewModel: ObservableObject {
    @Published var result: BMICalculateResponseDTO?
    @Published var isLoading = false
    @Published var error: APIError?

    private let service: BMIServicing

    init(
        service: BMIServicing = BMIService(apiClient: APIClient(baseURL: AppConfig.baseURL()))
    ) {
        self.service = service
    }

    func calculateBMI(request: BMICalculateRequestDTO) async {
        isLoading = true
        error = nil
        result = nil
        defer { isLoading = false }

        do {
            let res = try await service.calculateBMI(request: request)
            result = res
        } catch let e as APIError {
            error = e
        } catch let unknownError {
            // Unexpected non-APIError (should be rare).
            self.error = APIError.api(statusCode: 0, message: unknownError.localizedDescription)
        }
    }
}
