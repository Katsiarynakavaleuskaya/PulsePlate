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
enum PlateLoadIssue: Equatable, Sendable {
  case missingProKey
  case missingProfile
  case unauthorized
  case forbidden
  case validation(message: String)
  case api(statusCode: Int, message: String)
  case transport(message: String)
  case decoding(message: String)
  case unknown(message: String)

  var title: String {
    switch self {
    case .missingProKey:
      return "PRO access required"
    case .missingProfile:
      return "Profile required"
    case .unauthorized:
      return "Unauthorized"
    case .forbidden:
      return "Forbidden"
    case .validation:
      return "Check your details"
    case .api(let statusCode, _):
      return "Server error (HTTP \(statusCode))"
    case .transport:
      return "Network error"
    case .decoding:
      return "Unexpected response"
    case .unknown:
      return "Something went wrong"
    }
  }

  var message: String {
    switch self {
    case .missingProKey:
      #if DEBUG
      return "Configure PRO API key (PRO_API_KEY) in the Xcode scheme environment."
      #else
      return "PRO is not available on this device."
      #endif
    case .missingProfile:
      return "Open Profile and enter sex, age, height, and weight."
    case .unauthorized:
      return "Your PRO key is missing or invalid."
    case .forbidden:
      return "Your account does not have PRO access."
    case .validation(let message):
      return message
    case .api(_, let message):
      return message
    case .transport(let message):
      return message
    case .decoding(let message):
      return message
    case .unknown(let message):
      return message
    }
  }
}

class NutritionService: ObservableObject {
  @Published var nutritionData: NutritionData?
  @Published var isLoading = false
  @Published var issue: PlateLoadIssue?

  private let healthKitManager = HealthKitManager()
  private let apiClient: APIClientProtocol
  private let profileProvider: ProfileProviding
  private let apiKeyProvider: @Sendable () -> String?
  private let dailyService: ProDailyNutritionServicing

  init(
    apiClient: APIClientProtocol = APIClient(baseURL: AppConfig.baseURL()),
    profileProvider: ProfileProviding = DefaultProfileProvider(),
    apiKeyProvider: @escaping @Sendable () -> String? = { ProKeyProvider.value() },
    dailyService: ProDailyNutritionServicing? = nil
  ) {
    self.apiClient = apiClient
    self.profileProvider = profileProvider
    self.apiKeyProvider = apiKeyProvider
    self.dailyService = dailyService ?? DefaultProDailyNutritionService(apiClient: apiClient)
  }

  func fetchNutritionData(for date: Date = Date()) async {
    await MainActor.run {
      isLoading = true
      issue = nil
    }

    do {
      guard let apiKey = apiKeyProvider(), !apiKey.isEmpty else {
        await MainActor.run {
          self.issue = .missingProKey
          self.isLoading = false
        }
        return
      }

      guard let profile = profileProvider.proNutritionProfile() else {
        await MainActor.run {
          self.issue = .missingProfile
          self.isLoading = false
        }
        return
      }

      let lang = profileProvider.languageCode()
      let nutritionData = try await dailyService.fetchDailyNutrition(
        date: date,
        profile: profile,
        lang: lang,
        apiKey: apiKey
      )

      await MainActor.run {
        self.nutritionData = nutritionData
        self.isLoading = false
      }
    } catch let apiError as APIError {
      await MainActor.run {
        switch apiError {
        case .api(let statusCode, let message):
          if statusCode == 401 {
            self.issue = .unauthorized
          } else if statusCode == 403 {
            self.issue = .forbidden
          } else {
            self.issue = .api(statusCode: statusCode, message: message)
          }
        case .validation(let validation):
          let firstMessage = validation.detail.first?.msg ?? "Validation error"
          self.issue = .validation(message: firstMessage)
        case .transport(let message):
          self.issue = .transport(message: message)
        case .decodingFailed(let message):
          self.issue = .decoding(message: message)
        case .emptyResponse(let statusCode):
          self.issue = .api(statusCode: statusCode, message: "Empty response")
        default:
          self.issue = .unknown(message: apiError.localizedDescription)
        }
        self.isLoading = false
      }
    } catch {
      await MainActor.run {
        self.issue = .unknown(message: error.localizedDescription)
        self.isLoading = false
      }
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
      issue = nil
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
        self.issue = .unknown(message: error.localizedDescription)
        self.isLoading = false
      }
    }
  }
}
