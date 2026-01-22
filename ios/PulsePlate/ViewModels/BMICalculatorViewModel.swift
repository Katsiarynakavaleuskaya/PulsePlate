import Foundation
import Combine

@MainActor
final class BMICalculatorViewModel: ObservableObject {
    // TODO: Migrate to BMICalculateResponseDTO (tracked in BACKLOG_LEDGER.md)
    @Published var result: BMIResponse?
    @Published var isLoading = false
    // TODO: Migrate to APIError (tracked in BACKLOG_LEDGER.md)
    @Published var error: BMIServiceError?

    private let service: LegacyBMIServicing

    // TODO: Update to use BMIService() after UI migration (tracked in BACKLOG_LEDGER.md)
    init(service: LegacyBMIServicing = DefaultBMIService()) {
        self.service = service
    }

    // TODO: Migrate to BMICalculateRequestDTO (tracked in BACKLOG_LEDGER.md)
    func calculateBMI(request: BMIRequest) async {
        isLoading = true
        error = nil
        result = nil
        defer { isLoading = false }

        do {
            let res = try await service.calculateBMI(request: request)
            result = res
        } catch let e as BMIServiceError {
            error = e
        } catch {
            self.error = .transport(error.localizedDescription)
        }
    }
}
