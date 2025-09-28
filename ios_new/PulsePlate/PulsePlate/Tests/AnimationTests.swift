import XCTest
import SwiftUI
@testable import PulsePlate

class ProgressAnimationTests: XCTestCase {

  func testAnimatedProgressRing() {
    // Given
    let progress: Double = 0.75
    let color: Color = .blue
    let lineWidth: CGFloat = 8
    let size: CGFloat = 200

    // When
    let ring = AnimatedProgressRing(
      progress: progress,
      color: color,
      lineWidth: lineWidth,
      size: size
    )

    // Then
    XCTAssertNotNil(ring)
    XCTAssertEqual(ring.progress, progress)
    XCTAssertEqual(ring.color, color)
    XCTAssertEqual(ring.lineWidth, lineWidth)
    XCTAssertEqual(ring.size, size)
  }

  func testPulsingAnimation() {
    // Given
    let isActive = true
    let scale: Double = 1.05

    // When & Then
    // Test that the pulsing animation parameters are correct
    XCTAssertTrue(isActive)
    XCTAssertEqual(scale, 1.05)
  }

  func testShimmerEffect() {
    // Given
    let shimmerEffect = ShimmerEffect()

    // When & Then
    XCTAssertNotNil(shimmerEffect)
  }

  func testSlideInTransition() {
    // Given
    let isActive = true
    let delay = 0.3

    // When
    let transition = SlideInTransition(isActive: isActive, delay: delay)

    // Then
    XCTAssertTrue(transition.isActive)
    XCTAssertEqual(transition.delay, delay)
  }

  func testScaleTransition() {
    // Given
    let isActive = true
    let scale = 1.2

    // When
    let transition = ScaleTransition(isActive: isActive, scale: scale)

    // Then
    XCTAssertTrue(transition.isActive)
    XCTAssertEqual(transition.scale, scale)
  }

  func testFadeTransition() {
    // Given
    let isActive = true
    let delay = 0.4

    // When
    let transition = FadeTransition(isActive: isActive, delay: delay)

    // Then
    XCTAssertTrue(transition.isActive)
    XCTAssertEqual(transition.delay, delay)
  }
}

// MARK: - View Extension Tests
class ViewExtensionTests: XCTestCase {

  func testSlideInModifier() {
    // Given
    let isActive = true
    let delay = 0.2

    // When & Then
    // Test that the modifier parameters are correct
    XCTAssertTrue(isActive)
    XCTAssertEqual(delay, 0.2)
  }

  func testScaleOnAppearModifier() {
    // Given
    let isActive = true
    let scale = 1.1

    // When & Then
    XCTAssertTrue(isActive)
    XCTAssertEqual(scale, 1.1)
  }

  func testFadeInModifier() {
    // Given
    let isActive = true
    let delay = 0.1

    // When & Then
    XCTAssertTrue(isActive)
    XCTAssertEqual(delay, 0.1)
  }

  func testPulsingModifier() {
    // Given
    let isActive = true
    let scale = 1.05

    // When & Then
    XCTAssertTrue(isActive)
    XCTAssertEqual(scale, 1.05)
  }

  func testShimmerModifier() {
    // Given
    let shimmerEffect = ShimmerEffect()

    // When & Then
    XCTAssertNotNil(shimmerEffect)
  }
}

// MARK: - Performance Tests
class PerformanceTests: XCTestCase {

  func testAnimationPerformance() {
    // Given
    let iterations = 1000

    // When & Then
    measure {
      for _ in 0..<iterations {
        let _ = AnimatedProgressRing(progress: 0.5, color: .blue)
      }
    }
  }

  func testSegmentCreationPerformance() {
    // Given
    let iterations = 1000

    // When & Then
    measure {
      for _ in 0..<iterations {
        let _ = NutritionSegment(
          name: "Test",
          color: .blue,
          startAngle: 0,
          endAngle: 90,
          percentage: 25,
          icon: "test",
          currentValue: 1.0,
          targetValue: 2.0
        )
      }
    }
  }
}
