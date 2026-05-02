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

        async let energy = fetchSum(for: .dietaryEnergyConsumed, start: start, end: end)
        async let protein = fetchSum(for: .dietaryProtein, start: start, end: end)
        async let carbs  = fetchSum(for: .dietaryCarbohydrates, start: start, end: end)
        async let fat    = fetchSum(for: .dietaryFatTotal, start: start, end: end)
        async let fiber  = fetchSum(for: .dietaryFiber, start: start, end: end)
        async let sugar  = fetchSum(for: .dietarySugar, start: start, end: end)
        async let sodium = fetchSum(for: .dietarySodium, start: start, end: end)

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

    /// Fetch cumulative sum for a single HealthKit quantity type within a date range.
    /// Extracted from `fetchDailyTotals` to avoid local-function capture across
    /// async boundaries (Swift 6 sendability).
    private func fetchSum(
        for id: HKQuantityTypeIdentifier,
        start: Date,
        end: Date
    ) async throws -> Double {
        guard let type = HKObjectType.quantityType(forIdentifier: id) else {
            throw HealthKitError.invalidObjectType(id)
        }
        let predicate = HKQuery.predicateForSamples(
            withStart: start, end: end, options: .strictStartDate
        )
        let store = healthStore

        return try await withCheckedThrowingContinuation { cont in
            let query = HKStatisticsQuery(
                quantityType: type,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, stats, err in
                if let err = err {
                    cont.resume(throwing: err); return
                }
                guard let qty = stats?.sumQuantity() else {
                    cont.resume(returning: 0.0); return
                }
                let val: Double
                switch id {
                case .dietaryEnergyConsumed:
                    val = qty.doubleValue(for: .kilocalorie())
                case .dietaryProtein, .dietaryCarbohydrates,
                     .dietaryFatTotal, .dietaryFiber, .dietarySugar:
                    val = qty.doubleValue(for: .gram())
                case .dietarySodium:
                    val = qty.doubleValue(for: .gramUnit(with: .milli))
                default:
                    val = 0
                }
                cont.resume(returning: val)
            }
            store.execute(query)
        }
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
