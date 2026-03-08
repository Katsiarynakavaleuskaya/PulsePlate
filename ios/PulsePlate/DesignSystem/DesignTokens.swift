import SwiftUI

/// Stable public facade for generated design tokens.
/// Source of truth: /tokens via DesignTokens.generated.swift.
enum PPDesignTokens {
    enum Brand {
        static let navy = GeneratedDesignTokens.Brand.navy
        static let blue = GeneratedDesignTokens.Brand.blue
        static let green = GeneratedDesignTokens.Brand.green
        static let red = GeneratedDesignTokens.Brand.red
        static let gold = GeneratedDesignTokens.Brand.gold
    }

    enum ColorToken {
        static let success = GeneratedDesignTokens.ColorToken.success
        static let warning = GeneratedDesignTokens.ColorToken.warning
        static let error = GeneratedDesignTokens.ColorToken.error
        static let info = GeneratedDesignTokens.ColorToken.info

        static let textPrimary = GeneratedDesignTokens.ColorToken.textPrimary
        static let textSecondary = GeneratedDesignTokens.ColorToken.textSecondary
        static let textTertiary = GeneratedDesignTokens.ColorToken.textTertiary

        static let surface = GeneratedDesignTokens.ColorToken.surface
        static let surfaceElevated = GeneratedDesignTokens.ColorToken.surfaceElevated
        static let surfaceHighlight = GeneratedDesignTokens.ColorToken.surfaceHighlight
        static let strokeSubtle = GeneratedDesignTokens.ColorToken.strokeSubtle

        static let primary = GeneratedDesignTokens.ColorToken.primary
        static let primaryForeground = GeneratedDesignTokens.ColorToken.primaryForeground
    }

    enum Spacing {
        static let xxSmall = GeneratedDesignTokens.Spacing.xxSmall
        static let xSmall = GeneratedDesignTokens.Spacing.xSmall
        static let small = GeneratedDesignTokens.Spacing.small
        static let medium = GeneratedDesignTokens.Spacing.medium
        static let large = GeneratedDesignTokens.Spacing.large
        static let xLarge = GeneratedDesignTokens.Spacing.xLarge
        static let xxLarge = GeneratedDesignTokens.Spacing.xxLarge

        static let touchTarget = GeneratedDesignTokens.Spacing.touchTarget
        static let touchTargetLarge = GeneratedDesignTokens.Spacing.touchTargetLarge

        static let buttonPaddingSmall = GeneratedDesignTokens.Spacing.buttonPaddingSmall
        static let buttonPaddingMedium = GeneratedDesignTokens.Spacing.buttonPaddingMedium
        static let buttonPaddingLarge = GeneratedDesignTokens.Spacing.buttonPaddingLarge

        static let inputPaddingSmall = GeneratedDesignTokens.Spacing.inputPaddingSmall
        static let inputPaddingMedium = GeneratedDesignTokens.Spacing.inputPaddingMedium
        static let inputPaddingLarge = GeneratedDesignTokens.Spacing.inputPaddingLarge
    }

    enum Typography {
        static let sizeXS = GeneratedDesignTokens.Typography.sizeXS
        static let sizeSM = GeneratedDesignTokens.Typography.sizeSM
        static let sizeBase = GeneratedDesignTokens.Typography.sizeBase
        static let sizeLG = GeneratedDesignTokens.Typography.sizeLG
        static let sizeXL = GeneratedDesignTokens.Typography.sizeXL
        static let size2XL = GeneratedDesignTokens.Typography.size2XL
        static let size3XL = GeneratedDesignTokens.Typography.size3XL
        static let size4XL = GeneratedDesignTokens.Typography.size4XL

        static let caption = Font.system(size: sizeXS, weight: .regular)
        static let captionStrong = Font.system(size: sizeXS, weight: .semibold)
        static let body = Font.system(size: sizeBase, weight: .regular)
        static let bodyStrong = Font.system(size: sizeBase, weight: .semibold)
        static let title = Font.system(size: sizeLG, weight: .semibold)
        static let heading = Font.system(size: size2XL, weight: .bold)
        static let largeTitle = Font.system(size: size3XL, weight: .bold)
    }

    enum Radius {
        static let none = GeneratedDesignTokens.Radius.none
        static let small = GeneratedDesignTokens.Radius.small
        static let base = GeneratedDesignTokens.Radius.base
        static let medium = GeneratedDesignTokens.Radius.medium
        static let large = GeneratedDesignTokens.Radius.large
        static let xLarge = GeneratedDesignTokens.Radius.xLarge
        static let full = GeneratedDesignTokens.Radius.full
    }

    enum Elevation {
        static let none = GeneratedDesignTokens.Elevation.none
        static let card = GeneratedDesignTokens.Elevation.card
        static let dropdown = GeneratedDesignTokens.Elevation.dropdown
        static let modal = GeneratedDesignTokens.Elevation.modal
        static let popover = GeneratedDesignTokens.Elevation.popover
    }

    enum Motion {
        static let fast = GeneratedDesignTokens.Motion.fast
        static let standard = GeneratedDesignTokens.Motion.standard
        static let slow = GeneratedDesignTokens.Motion.slow
        static let springResponse = GeneratedDesignTokens.Motion.springResponse
        static let springDamping = GeneratedDesignTokens.Motion.springDamping
    }
}
