import Foundation
import HealthKit
import Combine

enum HealthKitError: Error, LocalizedError {
    case notAvailable
    case authorizationDenied
    case invalidObjectType(HKQuantityTypeIdentifier)
    case statisticsFailed

    var errorDescription: String? {
        switch self {
        case .notAvailable:
            return "HealthKit недоступен на этом устройстве."
        case .authorizationDenied:
            return "Доступ к данным HealthKit отклонён."
        case .invalidObjectType(let id):
            return "Тип \(id.rawValue) недоступен."
        case .statisticsFailed:
            return "Не удалось агрегировать данные."
        }
    }
}

struct DailyNutritionTotals: Identifiable {
    let id = UUID()
    var date: Date
    var energyKCal: Double
    var proteinG: Double
    var carbsG: Double
    var fatG: Double
    var fiberG: Double
    var sugarG: Double
    var sodiumMg: Double
}

final class HealthKitManager: ObservableObject {
    private let healthStore = HKHealthStore()

    @Published var isAuthorized = false
    @Published var error: Error?

    // MARK: - Auth

    func requestAuthorization() {
        guard HKHealthStore.isHealthDataAvailable() else {
            error = HealthKitError.notAvailable
            return
        }

        let ids: [HKQuantityTypeIdentifier] = [
            .dietaryEnergyConsumed,
            .dietaryProtein,
            .dietaryCarbohydrates,
            .dietaryFatTotal,
            .dietaryFiber,
            .dietarySugar,
            .dietarySodium,
            .bodyMass // для Progress
        ]

        let typesToRead = Set(ids.compactMap { HKObjectType.quantityType(forIdentifier: $0) })
        if typesToRead.count != ids.count {
            let missing = ids.first { HKObjectType.quantityType(forIdentifier: $0) == nil } ?? .dietaryEnergyConsumed
            error = HealthKitError.invalidObjectType(missing)
            return
        }

        healthStore.requestAuthorization(toShare: nil, read: typesToRead) { [weak self] success, authError in
            DispatchQueue.main.async {
                self?.isAuthorized = success
                self?.error = authError ?? (success ? nil : HealthKitError.authorizationDenied)
            }
        }
    }

    // MARK: - Daily totals

    func fetchDailyTotals(for date: Date) async throws -> DailyNutritionTotals {
        let calendar = Calendar.current
        let start = calendar.startOfDay(for: date)
        guard let end = calendar.date(byAdding: .day, value: 1, to: start) else {
            throw HealthKitError.statisticsFailed
        }

        func sum(_ id: HKQuantityTypeIdentifier) async throws -> Double {
            guard let type = HKObjectType.quantityType(forIdentifier: id) else {
                throw HealthKitError.invalidObjectType(id)
            }
            let predicate = HKQuery.predicateForSamples(withStart: start, end: end, options: .strictStartDate)

            return try await withCheckedThrowingContinuation { cont in
                let q = HKStatisticsQuery(quantityType: type,
                                          quantitySamplePredicate: predicate,
                                          options: .cumulativeSum) { _, stats, err in
                    if let err = err {
                        cont.resume(throwing: err); return
                    }
                    guard let qty = stats?.sumQuantity() else {
                        cont.resume(returning: 0.0); return
                    }
                    let val: Double
                    switch id {
                    case .dietaryEnergyConsumed: val = qty.doubleValue(for: .kilocalorie())
                    case .dietaryProtein, .dietaryCarbohydrates, .dietaryFatTotal, .dietaryFiber, .dietarySugar:
                        val = qty.doubleValue(for: .gram())
                    case .dietarySodium: val = qty.doubleValue(for: .milligram())
                    default: val = 0
                    }
                    cont.resume(returning: val)
                }
                self.healthStore.execute(q)
            }
        }

        async let energy = sum(.dietaryEnergyConsumed)
        async let protein = sum(.dietaryProtein)
        async let carbs  = sum(.dietaryCarbohydrates)
        async let fat    = sum(.dietaryFatTotal)
        async let fiber  = sum(.dietaryFiber)
        async let sugar  = sum(.dietarySugar)
        async let sodium = sum(.dietarySodium)

        return try await DailyNutritionTotals(
            date: start,
            energyKCal: energy,
            proteinG: protein,
            carbsG: carbs,
            fatG: fat,
            fiberG: fiber,
            sugarG: sugar,
            sodiumMg: sodium
        )
    }

    // MARK: - Week totals (Mon–Sun)

    func monday(of date: Date) -> Date {
        var cal = Calendar.current
        cal.firstWeekday = 2 // Monday
        let comps = cal.dateComponents([.yearForWeekOfYear, .weekOfYear], from: date)
        return cal.date(from: comps) ?? Calendar.current.startOfDay(for: date)
    }

    /// Неделя, в которую попадает `date` (Пн–Вс)
    func fetchWeekTotals(weekOf date: Date) async throws -> [DailyNutritionTotals] {
        let startMonday = monday(of: date)
        var days: [DailyNutritionTotals] = []
        for i in 0..<7 {
            if let d = Calendar.current.date(byAdding: .day, value: i, to: startMonday) {
                let t = try await fetchDailyTotals(for: d)
                days.append(t)
            }
        }
        return days
    }

    // MARK: - Latest body mass

    func fetchLatestBodyMass() async throws -> Double? {
        guard let type = HKObjectType.quantityType(forIdentifier: .bodyMass) else { return nil }
        return try await withCheckedThrowingContinuation { cont in
            let sort = NSSortDescriptor(key: HKSampleSortIdentifierStartDate, ascending: false)
            let q = HKSampleQuery(sampleType: type, predicate: nil, limit: 1, sortDescriptors: [sort]) { _, samples, err in
                if let err = err { cont.resume(throwing: err); return }
                let s = samples?.first as? HKQuantitySample
                let kg = s?.quantity.doubleValue(for: .gramUnit(with: .kilo))
                cont.resume(returning: kg)
            }
            self.healthStore.execute(q)
        }
    }
}
