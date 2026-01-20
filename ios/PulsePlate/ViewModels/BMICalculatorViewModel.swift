import Foundation

@MainActor
final class BMICalculatorViewModel: ObservableObject {
    @Published var result: BMIResponse?
    @Published var isLoading = false
    @Published var error: BMIServiceError?

    private let service: BMIServicing

    init(service: BMIServicing = DefaultBMIService()) {
        self.service = service
    }

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
            error = .transport(error.localizedDescription)
        }
    }
}
