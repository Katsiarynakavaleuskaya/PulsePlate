import Foundation
import HealthKit
import Combine

enum HealthKitError: Error, LocalizedError {
    case notAvailable
    case authorizationDenied
    case invalidObjectType

    var errorDescription: String? {
        switch self {
        case .notAvailable:
            return "HealthKit is not available on this device"
        case .authorizationDenied:
            return "HealthKit authorization was denied"
        case .invalidObjectType:
            return "One or more HealthKit object types are invalid or unavailable"
        }
    }
}

class HealthKitManager: ObservableObject {
    private let healthStore = HKHealthStore()
    @Published var isAuthorized = false
    @Published var error: Error?

    func requestAuthorization() {
        guard HKHealthStore.isHealthDataAvailable() else {
            error = HealthKitError.notAvailable
            return
        }

        let identifiers: [HKQuantityTypeIdentifier] = [
            .dietaryEnergyConsumed,
            .dietaryProtein,
            .dietaryCarbohydrates,
            .dietaryFatTotal,
            .dietaryFiber,
            .dietarySugar,
            .dietarySodium
        ]
        let typesToRead: Set<HKObjectType> = Set(identifiers.compactMap { HKObjectType.quantityType(forIdentifier: $0) })
        if typesToRead.count != identifiers.count {
            error = HealthKitError.invalidObjectType
            return
        }

        healthStore.requestAuthorization(toShare: nil, read: typesToRead) { [weak self] success, error in
            DispatchQueue.main.async {
                self?.isAuthorized = success
                self?.error = error ?? (success ? nil : HealthKitError.authorizationDenied)
            }
        }
    }

    func fetchNutritionData(for date: Date) async throws -> [HKQuantitySample] {
        let calendar = Calendar.current
        let startOfDay = calendar.startOfDay(for: date)
        let endOfDay = calendar.date(byAdding: .day, value: 1, to: startOfDay)!

        let predicate = HKQuery.predicateForSamples(withStart: startOfDay, end: endOfDay, options: .strictStartDate)
        guard let sampleType = HKObjectType.quantityType(forIdentifier: .dietaryEnergyConsumed) else {
            throw HealthKitError.invalidObjectType
        }
        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: sampleType,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: [NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: true)]
            ) { _, samples, error in
                if let error = error {
                    continuation.resume(throwing: error)
                } else {
                    continuation.resume(returning: samples as? [HKQuantitySample] ?? [])
                }
            }
            healthStore.execute(query)
        }
    }
}
