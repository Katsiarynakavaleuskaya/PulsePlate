import SwiftUI

/// Adaptive glass card with visual Liquid Glass approximation
/// Uses system materials on iOS 17–25 and a tuned glass-like color on iOS 26+
/// Centralizes glass styling to allow easy migration to real Liquid Glass APIs when available
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
            // iOS 26+ Liquid Glass API
            if #available(iOS 26.0, *) {
                shape.fill(Color.liquidGlass)
            } else {
                // iOS 17-25 fallback
                shape.fill(.thinMaterial)
            }
        }
    }
}
