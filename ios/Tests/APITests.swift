import XCTest
import SwiftUI
@testable import PulsePlate

class APITests: XCTestCase {

  var nutritionService: NutritionService!

  override func setUp() {
    super.setUp()
    nutritionService = NutritionService()
  }

  override func tearDown() {
    nutritionService = nil
    super.tearDown()
  }

  func testNutritionServiceInitialization() {
    // Given & When
    let service = NutritionService()

    // Then
    XCTAssertNotNil(service)
    XCTAssertFalse(service.isLoading)
    XCTAssertNil(service.error)
    XCTAssertNil(service.nutritionData)
  }

  func testMockDataLoading() {
    // Given
    let service = NutritionService()

    // When
    service.loadMockData()

    // Then
    XCTAssertNotNil(service.nutritionData)
    XCTAssertEqual(service.nutritionData?.segments.count, 4)
    XCTAssertEqual(service.nutritionData?.totalProgress, 0.68)
  }

  func testNutritionDataStructure() {
    // Given
    let service = NutritionService()
    service.loadMockData()

    // When
    let nutritionData = service.nutritionData

    // Then
    XCTAssertNotNil(nutritionData)
    XCTAssertEqual(nutritionData?.date, "2025-01-27")
    XCTAssertEqual(nutritionData?.totalProgress, 0.68)
    XCTAssertEqual(nutritionData?.segments.count, 4)
  }

  func testSegmentDataStructure() {
    // Given
    let service = NutritionService()
    service.loadMockData()

    // When
    let segment = service.nutritionData?.segments.first

    // Then
    XCTAssertNotNil(segment)
    XCTAssertEqual(segment?.name, "Vegetables")
    XCTAssertEqual(segment?.currentValue, 3.2)
    XCTAssertEqual(segment?.targetValue, 4.0)
    XCTAssertEqual(segment?.percentage, 40)
    XCTAssertEqual(segment?.color, "green")
    XCTAssertEqual(segment?.icon, "leaf.fill")
  }

  func testDailyGoalsStructure() {
    // Given
    let service = NutritionService()
    service.loadMockData()

    // When
    let dailyGoals = service.nutritionData?.dailyGoals

    // Then
    XCTAssertNotNil(dailyGoals)
    XCTAssertEqual(dailyGoals?.vegetables, 4.0)
    XCTAssertEqual(dailyGoals?.protein, 2.0)
    XCTAssertEqual(dailyGoals?.carbs, 1.5)
    XCTAssertEqual(dailyGoals?.fats, 0.8)
  }
}

// MARK: - API Error Tests
class APIErrorTests: XCTestCase {

  func testAPIErrorCases() {
    // Given & When & Then
    XCTAssertEqual(APIError.invalidURL.errorDescription, "Invalid URL")
    XCTAssertEqual(APIError.invalidResponse.errorDescription, "Invalid response from server")
    XCTAssertEqual(APIError.noData.errorDescription, "No data received")
  }

  func testAPIErrorLocalizedDescription() {
    // Given
    let errors: [APIError] = [.invalidURL, .invalidResponse, .noData]

    // When & Then
    for error in errors {
      XCTAssertNotNil(error.localizedDescription)
      XCTAssertFalse(error.localizedDescription.isEmpty)
    }
  }
}

// MARK: - Data Model Tests
class DataModelTests: XCTestCase {

  func testNutritionDataCodable() {
    // Given
    let nutritionData = NutritionData(
      date: "2025-01-27",
      segments: [
        NutritionSegmentData(
          name: "Test",
          currentValue: 1.0,
          targetValue: 2.0,
          percentage: 50,
          color: "blue",
          icon: "test"
        )
      ],
      totalProgress: 0.5,
      dailyGoals: DailyGoals(
        vegetables: 4.0,
        protein: 2.0,
        carbs: 1.5,
        fats: 0.8
      )
    )

    // When
    let encoder = JSONEncoder()
    let decoder = JSONDecoder()

    do {
      let data = try encoder.encode(nutritionData)
      let decoded = try decoder.decode(NutritionData.self, from: data)

      // Then
      XCTAssertEqual(decoded.date, nutritionData.date)
      XCTAssertEqual(decoded.totalProgress, nutritionData.totalProgress)
      XCTAssertEqual(decoded.segments.count, nutritionData.segments.count)
      XCTAssertEqual(decoded.dailyGoals.vegetables, nutritionData.dailyGoals.vegetables)
    } catch {
      XCTFail("Failed to encode/decode NutritionData: \(error)")
    }
  }

  func testNutritionSegmentDataCodable() {
    // Given
    let segmentData = NutritionSegmentData(
      name: "Protein",
      currentValue: 1.5,
      targetValue: 2.0,
      percentage: 25,
      color: "red",
      icon: "fish.fill"
    )

    // When
    let encoder = JSONEncoder()
    let decoder = JSONDecoder()

    do {
      let data = try encoder.encode(segmentData)
      let decoded = try decoder.decode(NutritionSegmentData.self, from: data)

      // Then
      XCTAssertEqual(decoded.name, segmentData.name)
      XCTAssertEqual(decoded.currentValue, segmentData.currentValue)
      XCTAssertEqual(decoded.targetValue, segmentData.targetValue)
      XCTAssertEqual(decoded.percentage, segmentData.percentage)
      XCTAssertEqual(decoded.color, segmentData.color)
      XCTAssertEqual(decoded.icon, segmentData.icon)
    } catch {
      XCTFail("Failed to encode/decode NutritionSegmentData: \(error)")
    }
  }

  func testDailyGoalsCodable() {
    // Given
    let dailyGoals = DailyGoals(
      vegetables: 4.0,
      protein: 2.0,
      carbs: 1.5,
      fats: 0.8
    )

    // When
    let encoder = JSONEncoder()
    let decoder = JSONDecoder()

    do {
      let data = try encoder.encode(dailyGoals)
      let decoded = try decoder.decode(DailyGoals.self, from: data)

      // Then
      XCTAssertEqual(decoded.vegetables, dailyGoals.vegetables)
      XCTAssertEqual(decoded.protein, dailyGoals.protein)
      XCTAssertEqual(decoded.carbs, dailyGoals.carbs)
      XCTAssertEqual(decoded.fats, dailyGoals.fats)
    } catch {
      XCTFail("Failed to encode/decode DailyGoals: \(error)")
    }
  }
}
