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

  // TODO: Backend endpoint /api/nutrition/{date} not yet implemented (GitHub issue)
  // This method is ready for integration when the endpoint is available
  // For now, falls back to mock data if endpoint returns 404/501
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

      let baseURL = AppConfig.baseURL()
      guard let url = URL(string: "\(baseURL.absoluteString)/api/nutrition/\(dateString)") else {
        throw NutritionAPIError.invalidURL
      }

      var request = URLRequest(url: url)
      request.setValue("application/json", forHTTPHeaderField: "Accept")

      let (data, response) = try await URLSession.shared.data(for: request)

      guard let httpResponse = response as? HTTPURLResponse else {
        throw NutritionAPIError.invalidResponse
      }

      // Fallback to mock data if endpoint not implemented (404) or not ready (501)
      if httpResponse.statusCode == 404 || httpResponse.statusCode == 501 {
        await MainActor.run {
          self.loadMockData()
          self.isLoading = false
        }
        return
      }

      guard httpResponse.statusCode == 200 else {
        throw NutritionAPIError.serverError(statusCode: httpResponse.statusCode)
      }

      let nutritionData = try JSONDecoder().decode(NutritionData.self, from: data)

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

// MARK: - API Errors
// Note: Legacy APIError renamed to NutritionAPIError to avoid conflict with Networking/APIError
enum NutritionAPIError: Error, LocalizedError {
  case invalidURL
  case invalidResponse
  case noData
  case serverError(statusCode: Int)

  var errorDescription: String? {
    switch self {
    case .invalidURL:
      return "Invalid URL"
    case .invalidResponse:
      return "Invalid response from server"
    case .noData:
      return "No data received"
    case .serverError(let code):
      return "Server error (HTTP \(code))"
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
