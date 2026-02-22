import SwiftUI

/// Design system text input aligned with web Input.tsx
/// Uses PPDesignTokens for consistent cross-platform styling
struct PPInput: View {
    @Binding var text: String
    let placeholder: String
    let isSecure: Bool
    let keyboardType: UIKeyboardType

    @FocusState private var isFocused: Bool

    init(
        text: Binding<String>,
        placeholder: String = "",
        isSecure: Bool = false,
        keyboardType: UIKeyboardType = .default
    ) {
        self._text = text
        self.placeholder = placeholder
        self.isSecure = isSecure
        self.keyboardType = keyboardType
    }

    var body: some View {
        Group {
            if isSecure {
                SecureField(placeholder, text: $text)
            } else {
                TextField(placeholder, text: $text)
            }
        }
        .keyboardType(keyboardType)
        .focused($isFocused)
        .font(PPDesignTokens.Typography.body)
        .foregroundColor(PPDesignTokens.ColorToken.textPrimary)
        .padding(.horizontal, PPDesignTokens.Spacing.medium)
        .padding(.vertical, PPDesignTokens.Spacing.medium)
        .frame(minHeight: PPDesignTokens.Spacing.touchTarget)
        .background(PPDesignTokens.ColorToken.surface)
        .clipShape(RoundedRectangle(cornerRadius: PPDesignTokens.Radius.medium, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: PPDesignTokens.Radius.medium, style: .continuous)
                .stroke(
                    isFocused ? PPDesignTokens.ColorToken.primary : PPDesignTokens.ColorToken.strokeSubtle,
                    lineWidth: isFocused ? 2 : 1
                )
        )
        .animation(.easeInOut(duration: PPDesignTokens.Motion.fast), value: isFocused)
    }
}

/// Number input variant for numeric values with locale support
struct PPNumberInput: View {
    @Binding var value: Double?
    let placeholder: String
    let suffix: String?

    @State private var textValue: String = ""
    @FocusState private var isFocused: Bool

    init(
        value: Binding<Double?>,
        placeholder: String = "",
        suffix: String? = nil
    ) {
        self._value = value
        self.placeholder = placeholder
        self.suffix = suffix
    }

    var body: some View {
        HStack(spacing: PPDesignTokens.Spacing.small) {
            TextField(placeholder, text: $textValue)
                .keyboardType(.decimalPad)
                .focused($isFocused)
                .font(PPDesignTokens.Typography.body)
                .foregroundColor(PPDesignTokens.ColorToken.textPrimary)
                .onChange(of: textValue) { _, newValue in
                    // Parse locale-aware (support comma as decimal separator for RU)
                    let normalized = newValue.replacingOccurrences(of: ",", with: ".")
                    value = Double(normalized)
                }

            if let suffix = suffix {
                Text(suffix)
                    .font(PPDesignTokens.Typography.body)
                    .foregroundColor(PPDesignTokens.ColorToken.textSecondary)
            }
        }
        .padding(.horizontal, PPDesignTokens.Spacing.medium)
        .padding(.vertical, PPDesignTokens.Spacing.medium)
        .frame(minHeight: PPDesignTokens.Spacing.touchTarget)
        .background(PPDesignTokens.ColorToken.surface)
        .clipShape(RoundedRectangle(cornerRadius: PPDesignTokens.Radius.medium, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: PPDesignTokens.Radius.medium, style: .continuous)
                .stroke(
                    isFocused ? PPDesignTokens.ColorToken.primary : PPDesignTokens.ColorToken.strokeSubtle,
                    lineWidth: isFocused ? 2 : 1
                )
        )
        .animation(.easeInOut(duration: PPDesignTokens.Motion.fast), value: isFocused)
        .onAppear {
            if let value = value {
                textValue = String(format: "%.1f", value)
            }
        }
        // Sync textValue when bound value changes externally (fixes Cubic P2 review)
        .onChange(of: value) { _, newValue in
            let newText = newValue.map { String(format: "%.1f", $0) } ?? ""
            // Only update if different to avoid cursor jump during user typing
            if newText != textValue && !isFocused {
                textValue = newText
            }
        }
    }
}
