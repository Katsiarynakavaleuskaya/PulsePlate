import SwiftUI

struct ProfileView: View {
    @ObservedObject var localization = LocalizationManager.shared
    @State private var showAnimationTest = false
    @State private var showBundleTest = false

    // RU: Минимальный PRO-профиль для Plate (/api/v1/pro/nutrition/daily).
    // EN: Minimal PRO profile for Plate (/api/v1/pro/nutrition/daily).
    @AppStorage("pro_profile_sex") private var proSex: String = ""
    @AppStorage("pro_profile_age") private var proAge: String = ""
    @AppStorage("pro_profile_height_cm") private var proHeightCm: String = ""
    @AppStorage("pro_profile_weight_kg") private var proWeightKg: String = ""
    @AppStorage("pro_profile_activity") private var proActivity: String = ProProfileActivity.moderate.rawValue
    @AppStorage("pro_profile_goal") private var proGoal: String = ProProfileGoal.maintain.rawValue

    var body: some View {
        NavigationStack {
            Form {
                Section(header: Text("PRO Nutrition Profile")) {
                    Picker("Sex", selection: $proSex) {
                        Text("Not set").tag("")
                        Text("Female").tag(ProProfileSex.female.rawValue)
                        Text("Male").tag(ProProfileSex.male.rawValue)
                    }

                    TextField("Age (years)", text: $proAge)
                        .keyboardType(.numberPad)

                    TextField("Height (cm)", text: $proHeightCm)
                        .keyboardType(.numberPad)

                    TextField("Weight (kg)", text: $proWeightKg)
                        .keyboardType(.numberPad)

                    Picker("Activity", selection: $proActivity) {
                        Text("Sedentary").tag(ProProfileActivity.sedentary.rawValue)
                        Text("Light").tag(ProProfileActivity.light.rawValue)
                        Text("Moderate").tag(ProProfileActivity.moderate.rawValue)
                        Text("Active").tag(ProProfileActivity.active.rawValue)
                        Text("Very active").tag(ProProfileActivity.veryActive.rawValue)
                    }

                    Picker("Goal", selection: $proGoal) {
                        Text("Loss").tag(ProProfileGoal.loss.rawValue)
                        Text("Maintain").tag(ProProfileGoal.maintain.rawValue)
                        Text("Gain").tag(ProProfileGoal.gain.rawValue)
                    }

                    Text("Used by Plate (PRO) to request /api/v1/pro/nutrition/daily.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                Section(header: Text(localization.localized("profile_language_section"))) {
                    Text(localization.localized("profile_language_value"))
                }
                Section(header: Text("Animation Test")) {
                    Button("Test MP4 Animation") {
                        showAnimationTest = true
                    }
                    Button("Test Bundle Files") {
                        showBundleTest = true
                    }
                    Button("Test Lottie Animation") {
                        // TODO: Add Lottie test
                    }
                }
                Section(header: Text(localization.localized("profile_legal_section"))) {
                    if let privacyURL = URL(string: "https://pulseplate.app/privacy") {
                        Link(localization.localized("profile_privacy_policy"), destination: privacyURL)
                    }
                    if let termsURL = URL(string: "https://pulseplate.app/terms") {
                        Link(localization.localized("profile_terms_of_use"), destination: termsURL)
                    }
                }
            }
            .navigationTitle("Profile")
            .sheet(isPresented: $showAnimationTest) {
                SimpleVideoTest()
            }
            .sheet(isPresented: $showBundleTest) {
                BundleTestView()
            }
            .accessibilityLabel(localization.localized("profile_screen_accessibility_label"))
        }
    }
}
