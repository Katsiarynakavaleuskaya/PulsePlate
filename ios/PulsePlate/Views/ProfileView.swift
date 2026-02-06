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
                Section(header: Text(localization.localized("pro_profile_section_title"))) {
                    Picker(localization.localized("pro_profile_sex"), selection: $proSex) {
                        Text(localization.localized("pro_profile_not_set")).tag("")
                        Text(localization.localized("pro_profile_sex_female"))
                            .tag(ProProfileSex.female.rawValue)
                        Text(localization.localized("pro_profile_sex_male"))
                            .tag(ProProfileSex.male.rawValue)
                    }

                    TextField(localization.localized("pro_profile_age"), text: $proAge)
                        .keyboardType(.numberPad)

                    TextField(localization.localized("pro_profile_height_cm"), text: $proHeightCm)
                        .keyboardType(.numberPad)

                    TextField(localization.localized("pro_profile_weight_kg"), text: $proWeightKg)
                        .keyboardType(.numberPad)

                    Picker(localization.localized("pro_profile_activity"), selection: $proActivity) {
                        Text(localization.localized("pro_profile_activity_sedentary"))
                            .tag(ProProfileActivity.sedentary.rawValue)
                        Text(localization.localized("pro_profile_activity_light"))
                            .tag(ProProfileActivity.light.rawValue)
                        Text(localization.localized("pro_profile_activity_moderate"))
                            .tag(ProProfileActivity.moderate.rawValue)
                        Text(localization.localized("pro_profile_activity_active"))
                            .tag(ProProfileActivity.active.rawValue)
                        Text(localization.localized("pro_profile_activity_very_active"))
                            .tag(ProProfileActivity.veryActive.rawValue)
                    }

                    Picker(localization.localized("pro_profile_goal"), selection: $proGoal) {
                        Text(localization.localized("pro_profile_goal_loss"))
                            .tag(ProProfileGoal.loss.rawValue)
                        Text(localization.localized("pro_profile_goal_maintain"))
                            .tag(ProProfileGoal.maintain.rawValue)
                        Text(localization.localized("pro_profile_goal_gain"))
                            .tag(ProProfileGoal.gain.rawValue)
                    }

                    Text(localization.localized("pro_profile_helper_text"))
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
