import SwiftUI

struct BMICalculatorScreen: View {
    @StateObject private var vm = BMICalculatorViewModel()
    @StateObject private var paywallRouter = PaywallRouter()

    @State private var weightKg = "70"
    @State private var heightCm = "175"
    @State private var age = "30"
    @State private var gender: String? = nil
    @State private var lang: String? = "en"
    @State private var validationMessage: String? = nil

    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        ScrollView {
            VStack(spacing: PPDesignTokens.Spacing.medium) {
                inputRegion
                calculateAction

                if let validationMessage {
                    PPCaption(validationMessage, color: .error, strong: true)
                }

                if let err = vm.error {
                    ValidationErrorsView(error: err)
                }

                if let res = vm.result {
                    GroupBox("Result") {
                        VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
                            Text("BMI: \(res.bmi, specifier: "%.2f")")
                            if let category = res.category {
                                Text("Category: \(category)")
                            }
                            Text("Group: \(res.groupDisplay)")
                            Text(res.interpretation)

                            if let vis = res.visualization {
                                Text("Visualization: \(vis.kind)")
                                Text("Ranges: \(vis.ranges.count)")
                            }

                            if let hook = res.softPaywall {
                                SoftPaywallHookView(hook: hook, nextBestAction: res.nextBestAction) {
                                    paywallRouter.presentPaywall(
                                        source: .bmiSoftPaywallCTA,
                                        target: PaywallTarget.resolve(
                                            softPaywallTarget: hook.target,
                                            nextBestAction: res.nextBestAction
                                        ),
                                        nextBestAction: res.nextBestAction
                                    )
                                }
                            }
                        }
                    }
                }
            }
            .padding(PPDesignTokens.Spacing.large)
            .padding(.bottom, PPDesignTokens.Spacing.touchTargetLarge)
        }
        .navigationTitle("BMI")
        .sheet(
            isPresented: $paywallRouter.isPaywallPresented,
            onDismiss: { paywallRouter.dismissPaywall() }
        ) {
            NavigationStack {
                PaywallScreen()
            }
        }
    }

    @ViewBuilder
    private var inputRegion: some View {
        if horizontalSizeClass == .regular && !dynamicTypeSize.isAccessibilitySize {
            HStack(alignment: .top, spacing: PPDesignTokens.Spacing.large) {
                inputGroup
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                movementPhoto(
                    width: BMIVisualLayout.regularPhotoWidth,
                    height: BMIVisualLayout.regularPhotoHeight
                )
            }
        } else {
            VStack(spacing: PPDesignTokens.Spacing.medium) {
                inputGroup
                HStack {
                    Spacer(minLength: 0)
                    movementPhoto(
                        width: BMIVisualLayout.compactPhotoWidth,
                        height: BMIVisualLayout.compactPhotoHeight
                    )
                    Spacer(minLength: 0)
                }
            }
        }
    }

    private var inputGroup: some View {
        GroupBox("Input") {
            VStack(alignment: .leading, spacing: PPDesignTokens.Spacing.small) {
                TextField("Weight (kg)", text: $weightKg)
                    .keyboardType(.decimalPad)
                TextField("Height (cm)", text: $heightCm)
                    .keyboardType(.decimalPad)
                TextField("Age", text: $age)
                    .keyboardType(.numberPad)

                Picker("Gender", selection: Binding(
                    get: { gender ?? "" },
                    set: { gender = $0.isEmpty ? nil : $0 }
                )) {
                    Text("—").tag("")
                    Text("female").tag("female")
                    Text("male").tag("male")
                }

                Picker("Lang", selection: Binding(
                    get: { lang ?? "" },
                    set: { lang = $0.isEmpty ? nil : $0 }
                )) {
                    Text("en").tag("en")
                    Text("ru").tag("ru")
                    Text("es").tag("es")
                }
            }
        }
    }

    private var calculateAction: some View {
        HStack(spacing: PPDesignTokens.Spacing.medium) {
            Image(ppRequiredBundleAsset: "FitChefThinking")
                .renderingMode(.original)
                .resizable()
                .scaledToFill()
                .scaleEffect(
                    BMIVisualLayout.medallionZoom,
                    anchor: UnitPoint(
                        x: BMIVisualLayout.medallionFocalX,
                        y: BMIVisualLayout.medallionFocalY
                    )
                )
                .frame(
                    width: BMIVisualLayout.medallionSide,
                    height: BMIVisualLayout.medallionSide
                )
                .clipped()
                .clipShape(Circle())
                .overlay(
                    Circle()
                        .stroke(PPDesignTokens.ColorToken.strokeSubtle, lineWidth: 1)
                )
                .accessibilityHidden(true)

            PPButton(
                vm.isLoading
                    ? NSLocalizedString("bmi.calculate.loading", comment: "")
                    : NSLocalizedString("bmi.calculate.cta", comment: ""),
                variant: .primary,
                size: .lg,
                fullWidth: true,
                isLoading: vm.isLoading
            ) {
                Task { await onCalculate() }
            }
        }
    }

    private func movementPhoto(width: CGFloat, height: CGFloat) -> some View {
        Image(ppRequiredBundleAsset: "photo-activity-movement-everyday-fitness-v1.jpg")
            .resizable()
            .scaledToFill()
            .frame(width: width, height: height)
            .clipped()
            .clipShape(
                RoundedRectangle(
                    cornerRadius: PPDesignTokens.Radius.large,
                    style: .continuous
                )
            )
            .accessibilityHidden(true)
    }

    private func onCalculate() async {
        validationMessage = nil

        guard
            let w = parseDouble(weightKg),
            let h = parseDouble(heightCm),
            let a = Int(age)
        else {
            validationMessage = "Invalid input. Please check weight, height, and age."
            return
        }

        let req = BMICalculateRequestDTO(
            weightKg: w,
            heightCm: h,
            age: a,
            gender: gender,
            pregnant: nil,
            athlete: nil,
            waistCm: nil,
            lang: lang
        )

        await vm.calculateBMI(request: req)
    }

    @MainActor
    private static let numberFormatter: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.locale = .current
        formatter.numberStyle = .decimal
        return formatter
    }()

    /// Locale-aware parsing of decimal numbers.
    /// Handles both dot (70.5) and comma (70,5) decimal separators.
    /// This is UI normalization, not BMI logic.
    @MainActor
    private func parseDouble(_ text: String) -> Double? {
        Self.numberFormatter.number(from: text)?.doubleValue
    }
}

private enum BMIVisualLayout {
    static let compactPhotoWidth: CGFloat = 148
    static let compactPhotoHeight: CGFloat = 185
    static let regularPhotoWidth: CGFloat = 224
    static let regularPhotoHeight: CGFloat = 280
    static let medallionSide: CGFloat = 52
    static let medallionFocalX: CGFloat = 0.5
    static let medallionFocalY: CGFloat = 0.38
    static let medallionZoom: CGFloat = 1.08
}
