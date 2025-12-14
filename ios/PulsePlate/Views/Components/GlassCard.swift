import SwiftUI

/// Adaptive glass card with iOS 26 Liquid Glass support and iOS 17+ fallback
/// Centralizes glass effects to handle future API changes gracefully
struct GlassCard<Content: View>: View {
    let cornerRadius: CGFloat
    let content: Content

    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency

    init(cornerRadius: CGFloat = 18, @ViewBuilder content: () -> Content) {
        self.cornerRadius = cornerRadius
        self.content = content()
    }

    var body: some View {
        content
            .padding(14)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
            .contentShape(RoundedRectangle(cornerRadius: cornerRadius, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .strokeBorder(.white.opacity(0.10), lineWidth: 1)
            )
    }

    @ViewBuilder
    private var background: some View {
        let shape = RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
        if reduceTransparency {
            // Respect "Reduce Transparency" accessibility setting (HIG)
            shape.fill(.background)
        } else {
            // Single implementation using thinMaterial.
            // Reintroduce iOS 26-specific conditional when the
            // SDK exposes the new Liquid Glass API.
            shape.fill(.thinMaterial)
        }
    }
}
