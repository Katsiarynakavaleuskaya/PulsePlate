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

  private let baseURL = "https://api.pulseplate.app" // Replace with actual API URL
  private let healthKitManager = HealthKitManager()

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

      guard let url = URL(string: "\(baseURL)/api/nutrition/\(dateString)") else {
        throw APIError.invalidURL
      }

      let (data, response) = try await URLSession.shared.data(from: url)

      guard let httpResponse = response as? HTTPURLResponse,
            httpResponse.statusCode == 200 else {
        throw APIError.invalidResponse
      }

      let nutritionData = try JSONDecoder().decode(NutritionData.self, from: data)

      await MainActor.run {
        self.nutritionData = nutritionData
        self.isLoading = false
      }
    } catch {
      await MainActor.run {
        self.error = error.localizedDescription
        self.isLoading = false
      }
    }
  }

  func updateSegmentValue(_ segmentName: String, newValue: Double) async {
    // TODO: Implement API call to update segment value
    print("Updating \(segmentName) to \(newValue)")
  }
}

// MARK: - API Errors
enum APIError: Error, LocalizedError {
  case invalidURL
  case invalidResponse
  case noData

  var errorDescription: String? {
    switch self {
    case .invalidURL:
      return "Invalid URL"
    case .invalidResponse:
      return "Invalid response from server"
    case .noData:
      return "No data received"
    }
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
      let samples = try await healthKitManager.fetchDailyTotals(for: date)
      // Process HealthKit samples and convert to NutritionData
      // This would integrate with your backend API
      _ = samples // Placeholder to silence unused variable warning for now
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
