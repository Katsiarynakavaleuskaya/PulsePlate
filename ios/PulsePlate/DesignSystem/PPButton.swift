import SwiftUI

/// Button variant matching web Button.tsx variants
enum PPButtonVariant {
    case primary
    case secondary
    case ghost
}

/// Button size matching web Button.tsx sizes
enum PPButtonSize {
    case sm
    case md
    case lg

    var minHeight: CGFloat {
        switch self {
        case .sm: return 40
        case .md: return 44  // iOS HIG touch target
        case .lg: return 48
        }
    }

    var horizontalPadding: CGFloat {
        switch self {
        case .sm: return PPDesignTokens.Spacing.large
        case .md: return PPDesignTokens.Spacing.xLarge
        case .lg: return PPDesignTokens.Spacing.xLarge
        }
    }

    var verticalPadding: CGFloat {
        switch self {
        case .sm: return PPDesignTokens.Spacing.small
        case .md: return PPDesignTokens.Spacing.medium
        case .lg: return PPDesignTokens.Spacing.large
        }
    }

    var font: Font {
        switch self {
        case .sm: return PPDesignTokens.Typography.body
        case .md: return PPDesignTokens.Typography.body
        case .lg: return PPDesignTokens.Typography.bodyStrong
        }
    }
}

/// Design system button aligned with web Button.tsx
/// Uses PPDesignTokens for consistent cross-platform styling
struct PPButton: View {
    let title: String
    let variant: PPButtonVariant
    let size: PPButtonSize
    let fullWidth: Bool
    let isLoading: Bool
    let action: () -> Void

    init(
        _ title: String,
        variant: PPButtonVariant = .primary,
        size: PPButtonSize = .md,
        fullWidth: Bool = false,
        isLoading: Bool = false,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.variant = variant
        self.size = size
        self.fullWidth = fullWidth
        self.isLoading = isLoading
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: PPDesignTokens.Spacing.small) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: foregroundColor))
                        .scaleEffect(0.8)
                }
                Text(title)
                    .font(size.font)
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: fullWidth ? .infinity : nil)
            .frame(minHeight: size.minHeight)
            .padding(.horizontal, size.horizontalPadding)
            .padding(.vertical, size.verticalPadding)
        }
        .buttonStyle(PPButtonStyle(variant: variant))
        .disabled(isLoading)
    }

    private var foregroundColor: Color {
        switch variant {
        case .primary:
            return PPDesignTokens.ColorToken.primaryForeground
        case .secondary, .ghost:
            return PPDesignTokens.ColorToken.textPrimary
        }
    }
}

/// Custom button style for PPButton variants
struct PPButtonStyle: ButtonStyle {
    let variant: PPButtonVariant

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(foregroundColor)
            .background(backgroundColor(isPressed: configuration.isPressed))
            .clipShape(RoundedRectangle(cornerRadius: PPDesignTokens.Radius.large, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: PPDesignTokens.Radius.large, style: .continuous)
                    .stroke(borderColor, lineWidth: variant == .secondary ? 1 : 0)
            )
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeInOut(duration: PPDesignTokens.Motion.fast), value: configuration.isPressed)
    }

    private var foregroundColor: Color {
        switch variant {
        case .primary:
            return PPDesignTokens.ColorToken.primaryForeground
        case .secondary:
            return PPDesignTokens.ColorToken.textPrimary
        case .ghost:
            return PPDesignTokens.ColorToken.textPrimary
        }
    }

    private func backgroundColor(isPressed: Bool) -> Color {
        switch variant {
        case .primary:
            return isPressed
                ? PPDesignTokens.ColorToken.primary.opacity(0.9)
                : PPDesignTokens.ColorToken.primary
        case .secondary:
            return isPressed
                ? PPDesignTokens.ColorToken.surface
                : Color.clear
        case .ghost:
            return isPressed
                ? PPDesignTokens.ColorToken.surfaceHighlight
                : Color.clear
        }
    }

    private var borderColor: Color {
        switch variant {
        case .secondary:
            return PPDesignTokens.ColorToken.strokeSubtle
        default:
            return .clear
        }
    }
}
