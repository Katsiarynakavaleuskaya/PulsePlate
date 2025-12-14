import SwiftUI

// MARK: - Design Tokens (Theme System)
extension ShapeStyle where Self == Color {
    /// Surface color for cards and containers (light overlay on navy background)
    static var surface: Color {
        Color.white.opacity(0.08)
    }

    /// Elevated surface color for floating elements
    static var surfaceElevated: Color {
        Color.white.opacity(0.12)
    }

    /// Liquid glass effect - works on iOS 17+
    /// Can be tweaked per iOS version later without breaking compilation
    static var liquidGlass: Color {
        if #available(iOS 18.0, *) {
            return Color.white.opacity(0.15)
        } else {
            return Color.white.opacity(0.15)
        }
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
