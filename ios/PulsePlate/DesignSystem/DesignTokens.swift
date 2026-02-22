import SwiftUI

/// Cross-platform token mirror for iOS surfaces.
/// Mirrors the canonical web token groups (color/spacing/type/radius/elevation/motion).
/// Source of truth: Assets.xcassets for brand colors, aligned with frontend/src/styles/tokens.ts
enum PPDesignTokens {
    // MARK: - Brand Colors (from Assets.xcassets)
    /// Canonical brand colors matching web tokens.css --pp-* variables
    enum Brand {
        /// Navy: #0F172A - Base, depth, trust
        static let navy = Color("Navy")
        /// Blue: #339FFF - Action, progress
        static let blue = Color("AppPrimary")
        /// Green: #20C997 - Success, positive
        static let green = Color("AccentGreen")
        /// Red: #FF5D5D - Accent-only, critical states
        static let red = Color("HeartRed")
        /// Gold: #D4AF37 - Premium accents
        static let gold = Color("Gold")
    }

    // MARK: - Semantic Colors
    enum ColorToken {
        // Status colors (aligned with web --color-success/warning/error/info)
        static let success = Brand.green
        static let warning = Color(hex: "#F59E0B")
        static let error = Brand.red
        static let info = Brand.blue

        // Text colors (for dark backgrounds like navy)
        static let textPrimary = Color.white
        static let textSecondary = Color.white.opacity(0.8)
        static let textTertiary = Color.white.opacity(0.6)

        // Surface colors (glass effect on navy background)
        static let surface = Color.white.opacity(0.1)
        static let surfaceElevated = Color.white.opacity(0.15)
        static let surfaceHighlight = Color.white.opacity(0.25)
        static let strokeSubtle = Color.white.opacity(0.12)

        // Primary action colors
        static let primary = Brand.blue
        static let primaryForeground = Color.white
    }

    // MARK: - Spacing (4px base unit, aligned with web)
    enum Spacing {
        static let xxSmall: CGFloat = 2    // 0.125rem
        static let xSmall: CGFloat = 4     // 0.25rem
        static let small: CGFloat = 8      // 0.5rem
        static let medium: CGFloat = 12    // 0.75rem
        static let large: CGFloat = 16     // 1rem
        static let xLarge: CGFloat = 24    // 1.5rem
        static let xxLarge: CGFloat = 32   // 2rem

        // Touch targets (iOS HIG: minimum 44pt)
        static let touchTarget: CGFloat = 44
        static let touchTargetLarge: CGFloat = 56

        // Button padding
        static let buttonPaddingSmall: CGFloat = 8
        static let buttonPaddingMedium: CGFloat = 12
        static let buttonPaddingLarge: CGFloat = 16

        // Input padding
        static let inputPaddingSmall: CGFloat = 8
        static let inputPaddingMedium: CGFloat = 12
        static let inputPaddingLarge: CGFloat = 16
    }

    // MARK: - Typography (aligned with web font sizes)
    enum Typography {
        // Font sizes (matching web rem values at 16px base)
        static let sizeXS: CGFloat = 12     // 0.75rem
        static let sizeSM: CGFloat = 14     // 0.875rem
        static let sizeBase: CGFloat = 16   // 1rem
        static let sizeLG: CGFloat = 18     // 1.125rem
        static let sizeXL: CGFloat = 20     // 1.25rem
        static let size2XL: CGFloat = 24    // 1.5rem
        static let size3XL: CGFloat = 30    // 1.875rem
        static let size4XL: CGFloat = 36    // 2.25rem

        // Pre-configured fonts
        static let caption = Font.system(size: sizeXS, weight: .regular)
        static let captionStrong = Font.system(size: sizeXS, weight: .semibold)
        static let body = Font.system(size: sizeBase, weight: .regular)
        static let bodyStrong = Font.system(size: sizeBase, weight: .semibold)
        static let title = Font.system(size: sizeLG, weight: .semibold)
        static let heading = Font.system(size: size2XL, weight: .bold)
        static let largeTitle = Font.system(size: size3XL, weight: .bold)
    }

    // MARK: - Border Radius (aligned with web)
    enum Radius {
        static let none: CGFloat = 0
        static let small: CGFloat = 4      // 0.25rem
        static let base: CGFloat = 6       // 0.375rem
        static let medium: CGFloat = 8     // 0.5rem
        static let large: CGFloat = 12     // 0.75rem
        static let xLarge: CGFloat = 16    // 1rem
        static let full: CGFloat = 9999
    }

    // MARK: - Elevation / Shadows
    enum Elevation {
        static let none: CGFloat = 0
        static let card: CGFloat = 2
        static let dropdown: CGFloat = 4
        static let modal: CGFloat = 8
        static let popover: CGFloat = 12
    }

    // MARK: - Motion / Animation
    enum Motion {
        static let fast: Double = 0.15
        static let standard: Double = 0.25
        static let slow: Double = 0.4

        // Spring animations
        static let springResponse: Double = 0.3
        static let springDamping: Double = 0.7
    }
}
