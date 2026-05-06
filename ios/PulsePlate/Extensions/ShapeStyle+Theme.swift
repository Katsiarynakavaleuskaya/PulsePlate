import SwiftUI

// MARK: - Design Tokens (Theme System)
extension ShapeStyle where Self == Color {
    /// Surface color for cards and containers (light overlay on navy background)
    static var surface: Color {
        PPDesignTokens.ColorToken.surface
    }

    /// Elevated surface color for floating elements
    static var surfaceElevated: Color {
        PPDesignTokens.ColorToken.surfaceElevated
    }

    /// Liquid glass effect for glassmorphism UI.
    ///
    /// Until `/tokens` promotes a dedicated liquid-glass token, reuse the
    /// elevated surface token so iOS does not carry a separate opacity source.
    static var liquidGlass: Color {
        PPDesignTokens.ColorToken.surfaceElevated
    }
}

// MARK: - Convenience View Modifiers
extension View {
    /// Apply surface background (standard card background)
    func surfaceBackground() -> some View {
        self.background(Color.surface)
    }

    /// Apply elevated surface background (floating elements)
    func elevatedSurfaceBackground() -> some View {
        self.background(Color.surfaceElevated)
    }
}
