import Foundation
import HealthKit
import Combine

// MARK: - Nutrition Models
struct NutritionData: Codable {
  let date: String
  let segments: [NutritionSegmentData]
  let totalProgress: Double
  let dailyGoals: DailyGoals
}

struct NutritionSegmentData: Codable {
  let name: String
  let currentValue: Double
  let targetValue: Double
  let percentage: Double
  let color: String
  let icon: String
}

struct DailyGoals: Codable {
  let vegetables: Double
  let protein: Double
  let carbs: Double
  let fats: Double
}

// MARK: - API Service
class NutritionService: ObservableObject {
  @Published var nutritionData: NutritionData?
  @Published var isLoading = false
  @Published var error: String?

  private let healthKitManager = HealthKitManager()
  private let apiClient: APIClientProtocol

  // TODO: Backend endpoint /api/nutrition/{date} not yet implemented (GitHub issue)
  // This method is ready for integration when the endpoint is available
  // For now, falls back to mock data in DEBUG builds
  init(apiClient: APIClientProtocol = APIClient(baseURL: AppConfig.baseURL())) {
    self.apiClient = apiClient
  }

  func fetchNutritionData(for date: Date = Date()) async {
    await MainActor.run {
      isLoading = true
      error = nil
    }

    do {
      let dateFormatter = ISO8601DateFormatter()
      dateFormatter.formatOptions = [.withFullDate]
      dateFormatter.timeZone = TimeZone(identifier: "UTC")
      let dateString = dateFormatter.string(from: date)

      let path = "api/nutrition/\(dateString)"
      let nutritionData: NutritionData = try await apiClient.get(path: path)

      await MainActor.run {
        self.nutritionData = nutritionData
        self.isLoading = false
      }
    } catch let decodingError as DecodingError {
      // In DEBUG, fallback to mock data on decoding errors
      #if DEBUG
      await MainActor.run {
        self.loadMockData()
        self.isLoading = false
      }
      #else
      await MainActor.run {
        self.error = "Decoding failed: \(decodingError.localizedDescription)"
        self.isLoading = false
      }
      #endif
    } catch {
      // In DEBUG, fallback to mock data on network/server errors
      #if DEBUG
      await MainActor.run {
        self.loadMockData()
        self.isLoading = false
      }
      #else
      await MainActor.run {
        self.error = error.localizedDescription
        self.isLoading = false
      }
      #endif
    }
  }

  func updateSegmentValue(_ segmentName: String, newValue: Double) async {
    // TODO: Implement API call to update segment value
    print("Updating \(segmentName) to \(newValue)")
  }
}

// MARK: - Mock Data for Development
extension NutritionService {
  func loadMockData() {
    nutritionData = NutritionData(
      date: "2025-01-27",
      segments: [
        NutritionSegmentData(
          name: "Vegetables",
          currentValue: 3.2,
          targetValue: 4.0,
          percentage: 40,
          color: "green",
          icon: "leaf.fill"
        ),
        NutritionSegmentData(
          name: "Protein",
          currentValue: 1.8,
          targetValue: 2.0,
          percentage: 25,
          color: "red",
          icon: "fish.fill"
        ),
        NutritionSegmentData(
          name: "Carbs",
          currentValue: 1.2,
          targetValue: 1.5,
          percentage: 25,
          color: "orange",
          icon: "grain.fill"
        ),
        NutritionSegmentData(
          name: "Fats",
          currentValue: 0.6,
          targetValue: 0.8,
          percentage: 10,
          color: "yellow",
          icon: "drop.fill"
        )
      ],
      totalProgress: 0.68,
      dailyGoals: DailyGoals(
        vegetables: 4.0,
        protein: 2.0,
        carbs: 1.5,
        fats: 0.8
      )
    )
  }

  func loadFromHealthKit(for date: Date = Date()) async {
    await MainActor.run {
      isLoading = true
      error = nil
    }

    do {
      let totals = try await healthKitManager.fetchDailyTotals(for: date)
      // Process HealthKit totals and convert to NutritionData
      // This would integrate with your backend API
      _ = totals // Placeholder to silence unused variable warning for now
      await MainActor.run {
        self.loadMockData() // For now, use mock data
        self.isLoading = false
      }
    } catch {
      await MainActor.run {
        self.error = error.localizedDescription
        self.isLoading = false
      }
    }
  }
}
