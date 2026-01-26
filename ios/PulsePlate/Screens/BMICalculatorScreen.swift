import SwiftUI

struct BMICalculatorScreen: View {
    @StateObject private var vm = BMICalculatorViewModel()

    @State private var weightKg = "70"
    @State private var heightCm = "175"
    @State private var age = "30"
    @State private var gender: String? = nil
    @State private var lang: String? = "en"
    @State private var validationMessage: String? = nil

    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                GroupBox("Input") {
                    VStack(alignment: .leading, spacing: 8) {
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

                Button(vm.isLoading ? "Loading..." : "Calculate") {
                    Task { await onCalculate() }
                }
                .disabled(vm.isLoading)

                if let validationMessage {
                    Text(validationMessage)
                        .foregroundColor(.red)
                        .font(.caption)
                }

                if let err = vm.error {
                    ValidationErrorsView(error: err)
                }

                if let res = vm.result {
                    GroupBox("Result") {
                        VStack(alignment: .leading, spacing: 8) {
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

                            // Soft paywall hook: only render if navigation handler is available
                            // Deferred: wire to real paywall router (see BACKLOG_LEDGER.md)
                            if let hook = res.softPaywall {
                                SoftPaywallHookView(hook: hook) {
                                    // Navigation deferred until paywall router is available
                                }
                            }
                        }
                    }
                }
            }
            .padding()
        }
        .navigationTitle("BMI")
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
