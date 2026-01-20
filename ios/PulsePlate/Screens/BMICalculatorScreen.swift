import SwiftUI

struct BMICalculatorScreen: View {
    @StateObject private var vm = BMICalculatorViewModel()

    @State private var weightKg = "70"
    @State private var heightCm = "175"
    @State private var age = "30"
    @State private var gender: String? = nil
    @State private var lang: String? = "en"

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

                            if let hook = res.softPaywall {
                                SoftPaywallHookView(hook: hook) {
                                    // TODO: Navigate to Pro Paywall (client routing)
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
        guard
            let w = Double(weightKg),
            let h = Double(heightCm),
            let a = Int(age)
        else { return }

        let req = BMIRequest(
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
}
