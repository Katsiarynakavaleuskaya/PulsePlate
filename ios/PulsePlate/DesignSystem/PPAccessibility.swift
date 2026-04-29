import SwiftUI

/// Shared accessibility and motion helpers for PulsePlate design-system primitives.
enum PPAccessibility {
    static let minimumTouchTarget = PPDesignTokens.Spacing.touchTarget

    static func minimumTouchTarget(for height: CGFloat) -> CGFloat {
        max(height, minimumTouchTarget)
    }

    static func pressScale(isPressed: Bool, reduceMotion: Bool) -> CGFloat {
        guard !reduceMotion else { return 1.0 }
        return isPressed ? 0.95 : 1.0
    }

    static func animation(_ animation: Animation?, reduceMotion: Bool) -> Animation? {
        reduceMotion ? nil : animation
    }
}
