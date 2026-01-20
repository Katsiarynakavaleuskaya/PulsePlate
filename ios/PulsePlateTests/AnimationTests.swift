import XCTest
import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

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
    #if canImport(UIKit)
    XCTAssertEqual(UIColor(ring.color), UIColor(color))
    #endif
    XCTAssertEqual(ring.lineWidth, lineWidth)
    XCTAssertEqual(ring.size, size)
  }

  func testPulsingAnimation() {
    // Given
    let isActive = true
    let scale: Double = 1.05

    // When - Create the modifier and verify properties
    let modifier = PulsingView(isActive: isActive, scale: scale)
    XCTAssertEqual(modifier.isActive, isActive)
    XCTAssertEqual(modifier.scale, scale)

    // Also test the extension method
    let pulsingView = Text("Test")
      .pulsing(isActive: isActive, scale: scale)
    XCTAssertNotNil(pulsingView)
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
    let testView = Text("Test")
    let isActive = true
    let delay = 0.2

    // When - Apply the slideIn modifier
    let modifiedView = testView.slideIn(isActive: isActive, delay: delay)

    // Then - Verify the view is created without crashing
    // Note: In a real test environment, you would use ViewInspector to verify
    // that the SlideInTransition modifier is correctly applied with the expected properties
    XCTAssertNotNil(modifiedView)
  }

  func testScaleOnAppearModifier() {
    // Given
    let testView = Text("Test")
    let isActive = true
    let scale = 1.1

    // When - Apply the scaleOnAppear modifier
    let modifiedView = testView.scaleOnAppear(isActive: isActive, scale: scale)

    // Then - Verify the view is created without crashing
    XCTAssertNotNil(modifiedView)
  }

  func testFadeInModifier() {
    // Given
    let testView = Text("Test")
    let isActive = true
    let delay = 0.1

    // When - Apply the fadeIn modifier
    let modifiedView = testView.fadeIn(isActive: isActive, delay: delay)

    // Then - Verify the view is created without crashing
    XCTAssertNotNil(modifiedView)
  }

  func testPulsingModifier() {
    // Given
    let testView = Text("Test")
    let isActive = true
    let scale = 1.05

    // When - Apply the pulsing modifier
    let modifiedView = testView.pulsing(isActive: isActive, scale: scale)

    // Then - Verify the view is created without crashing
    XCTAssertNotNil(modifiedView)
  }

  func testShimmerModifier() {
    // Given
    let testView = Text("Test")

    // When - Apply the shimmer modifier
    let modifiedView = testView.shimmer()

    // Then - Verify the view is created without crashing
    XCTAssertNotNil(modifiedView)
  }
}

// MARK: - Performance Tests
class PerformanceTests: XCTestCase {

  func testAnimationPerformance() {
    // Given
    let iterations = 1000

    // When & Then
    measure(metrics: [XCTClockMetric()]) {
      for _ in 0..<iterations {
        let _ = AnimatedProgressRing(progress: 0.5, color: .blue)
      }
    }
  }

  func testSegmentCreationPerformance() {
    // Given
    let iterations = 1000

    // When & Then
    measure(metrics: [XCTClockMetric()]) {
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
