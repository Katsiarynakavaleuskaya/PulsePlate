import SwiftUI

/// Cross-platform token mirror for iOS surfaces.
/// Mirrors the canonical web token groups (color/spacing/type/radius/elevation/motion).
enum PPDesignTokens {
    enum ColorToken {
        static let success = Color(hex: "#10B981")
        static let warning = Color(hex: "#F59E0B")
        static let error = Color(hex: "#EF4444")
        static let info = Color(hex: "#3B82F6")
        static let textPrimary = Color.white
        static let textSecondary = Color.white.opacity(0.8)
        static let textTertiary = Color.white.opacity(0.6)
        static let surface = Color.white.opacity(0.1)
        static let surfaceElevated = Color.white.opacity(0.1)
        static let surfaceHighlight = Color.white.opacity(0.25)
        static let strokeSubtle = Color.white.opacity(0.12)
    }

    enum Spacing {
        static let xSmall: CGFloat = 4
        static let small: CGFloat = 8
        static let medium: CGFloat = 12
        static let large: CGFloat = 16
        static let xLarge: CGFloat = 24
        static let touchTarget: CGFloat = 44
    }

    enum Typography {
        static let caption = Font.caption
        static let body = Font.body
        static let bodyStrong = Font.body.weight(.semibold)
        static let heading = Font.title.weight(.bold)
    }

    enum Radius {
        static let small: CGFloat = 8
        static let medium: CGFloat = 12
        static let large: CGFloat = 16
    }

    enum Elevation {
        static let card: CGFloat = 0
        static let modal: CGFloat = 8
    }

    enum Motion {
        static let fast: Double = 0.15
        static let standard: Double = 0.25
        static let slow: Double = 0.4
    }
}
