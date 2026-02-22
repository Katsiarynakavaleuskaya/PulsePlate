import SwiftUI

/// Design system card aligned with web Card.tsx
/// Uses PPDesignTokens for consistent cross-platform styling
struct PPCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        // Use ppCardStyle() modifier to avoid duplication (CodeRabbit nitpick)
        content.ppCardStyle()
    }
}

/// Card header component
struct PPCardHeader<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(.horizontal, PPDesignTokens.Spacing.xLarge)
            .padding(.top, PPDesignTokens.Spacing.xLarge)
    }
}

/// Card content component
struct PPCardContent<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .padding(.horizontal, PPDesignTokens.Spacing.xLarge)
            .padding(.bottom, PPDesignTokens.Spacing.xLarge)
    }
}

/// Card footer component with separator
struct PPCardFooter<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        VStack(spacing: 0) {
            Divider()
                .background(PPDesignTokens.ColorToken.strokeSubtle)
            content
                .padding(.horizontal, PPDesignTokens.Spacing.xLarge)
                .padding(.vertical, PPDesignTokens.Spacing.large)
        }
    }
}

// MARK: - Convenience modifiers
extension View {
    /// Apply standard card styling
    func ppCardStyle() -> some View {
        self
            .background(PPDesignTokens.ColorToken.surface)
            .clipShape(RoundedRectangle(cornerRadius: PPDesignTokens.Radius.large, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: PPDesignTokens.Radius.large, style: .continuous)
                    .stroke(PPDesignTokens.ColorToken.strokeSubtle, lineWidth: 1)
            )
    }

    /// Apply elevated card styling (more prominent)
    func ppElevatedCardStyle() -> some View {
        self
            .background(PPDesignTokens.ColorToken.surfaceElevated)
            .clipShape(RoundedRectangle(cornerRadius: PPDesignTokens.Radius.large, style: .continuous))
            .shadow(color: .black.opacity(0.1), radius: CGFloat(PPDesignTokens.Elevation.card), x: 0, y: 2)
    }
}
