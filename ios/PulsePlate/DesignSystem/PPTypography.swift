import SwiftUI

/// Design system typography components aligned with web typography tokens
/// Uses PPDesignTokens for consistent cross-platform styling

// MARK: - Text Style Variants
enum PPTextStyle {
    case caption
    case captionStrong
    case body
    case bodyStrong
    case title
    case heading
    case largeTitle

    var font: Font {
        switch self {
        case .caption: return PPDesignTokens.Typography.caption
        case .captionStrong: return PPDesignTokens.Typography.captionStrong
        case .body: return PPDesignTokens.Typography.body
        case .bodyStrong: return PPDesignTokens.Typography.bodyStrong
        case .title: return PPDesignTokens.Typography.title
        case .heading: return PPDesignTokens.Typography.heading
        case .largeTitle: return PPDesignTokens.Typography.largeTitle
        }
    }
}

// MARK: - Text Color Variants
enum PPTextColor {
    case primary
    case secondary
    case tertiary
    case success
    case warning
    case error
    case info
    case brand

    var color: Color {
        switch self {
        case .primary: return PPDesignTokens.ColorToken.textPrimary
        case .secondary: return PPDesignTokens.ColorToken.textSecondary
        case .tertiary: return PPDesignTokens.ColorToken.textTertiary
        case .success: return PPDesignTokens.ColorToken.success
        case .warning: return PPDesignTokens.ColorToken.warning
        case .error: return PPDesignTokens.ColorToken.error
        case .info: return PPDesignTokens.ColorToken.info
        case .brand: return PPDesignTokens.Brand.blue
        }
    }
}

// MARK: - Typography Components

/// Caption text (small, supplementary information)
struct PPCaption: View {
    let text: String
    let color: PPTextColor
    let isStrong: Bool

    init(_ text: String, color: PPTextColor = .tertiary, strong: Bool = false) {
        self.text = text
        self.color = color
        self.isStrong = strong
    }

    var body: some View {
        Text(text)
            .font(isStrong ? PPDesignTokens.Typography.captionStrong : PPDesignTokens.Typography.caption)
            .foregroundColor(color.color)
    }
}

/// Body text (default readable text)
struct PPBody: View {
    let text: String
    let color: PPTextColor
    let isStrong: Bool

    init(_ text: String, color: PPTextColor = .primary, strong: Bool = false) {
        self.text = text
        self.color = color
        self.isStrong = strong
    }

    var body: some View {
        Text(text)
            .font(isStrong ? PPDesignTokens.Typography.bodyStrong : PPDesignTokens.Typography.body)
            .foregroundColor(color.color)
    }
}

/// Title text (section headers)
struct PPTitle: View {
    let text: String
    let color: PPTextColor

    init(_ text: String, color: PPTextColor = .primary) {
        self.text = text
        self.color = color
    }

    var body: some View {
        Text(text)
            .font(PPDesignTokens.Typography.title)
            .foregroundColor(color.color)
    }
}

/// Heading text (large section headers)
struct PPHeading: View {
    let text: String
    let color: PPTextColor

    init(_ text: String, color: PPTextColor = .primary) {
        self.text = text
        self.color = color
    }

    var body: some View {
        Text(text)
            .font(PPDesignTokens.Typography.heading)
            .foregroundColor(color.color)
    }
}

/// Large title text (screen titles)
struct PPLargeTitle: View {
    let text: String
    let color: PPTextColor

    init(_ text: String, color: PPTextColor = .primary) {
        self.text = text
        self.color = color
    }

    var body: some View {
        Text(text)
            .font(PPDesignTokens.Typography.largeTitle)
            .foregroundColor(color.color)
    }
}

// MARK: - View Modifiers
extension View {
    /// Apply design system text style
    func ppTextStyle(_ style: PPTextStyle, color: PPTextColor = .primary) -> some View {
        self
            .font(style.font)
            .foregroundColor(color.color)
    }
}

extension Text {
    /// Apply design system text style to Text
    func ppStyle(_ style: PPTextStyle, color: PPTextColor = .primary) -> some View {
        self
            .font(style.font)
            .foregroundColor(color.color)
    }
}
