import SwiftUI

struct ProfileView: View {
    @ObservedObject var localization = LocalizationManager.shared
    @State private var showAnimationTest = false
    @State private var showBundleTest = false
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    // RU: Минимальный PRO-профиль для Plate (/api/v1/pro/nutrition/daily).
    // EN: Minimal PRO profile for Plate (/api/v1/pro/nutrition/daily).
    @AppStorage("pro_profile_sex") private var proSex: String = ""
    @AppStorage("pro_profile_age") private var proAge: String = ""
    @AppStorage("pro_profile_height_cm") private var proHeightCm: String = ""
    @AppStorage("pro_profile_weight_kg") private var proWeightKg: String = ""
    @AppStorage("pro_profile_activity") private var proActivity: String = ProProfileActivity.moderate.rawValue
    @AppStorage("pro_profile_goal") private var proGoal: String = ProProfileGoal.maintain.rawValue

    private var isAppStoreScreenshotMode: Bool {
        AppStoreScreenshotContext.isEnabled
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        Spacer(minLength: 0)
                        Image("FitChefOnboardingProfileSetup")
                            .renderingMode(.original)
                            .resizable()
                            .scaledToFill()
                            .scaleEffect(
                                ProfileVisualLayout.heroZoom,
                                anchor: UnitPoint(
                                    x: ProfileVisualLayout.heroFocalX,
                                    y: ProfileVisualLayout.heroFocalY
                                )
                            )
                            .frame(width: profileHeroWidth, height: profileHeroHeight)
                            .clipped()
                            .clipShape(
                                RoundedRectangle(
                                    cornerRadius: PPDesignTokens.Radius.large,
                                    style: .continuous
                                )
                            )
                            .accessibilityHidden(true)
                        Spacer(minLength: 0)
                    }
                    .frame(maxWidth: .infinity)
                }

                Section(header: Text(localization.localized("pro.profile.header"))) {
                    Picker(localization.localized("pro.profile.sex"), selection: $proSex) {
                        Text(localization.localized("common.not_set")).tag("")
                        Text(localization.localized("sex.female")).tag(ProProfileSex.female.rawValue)
                        Text(localization.localized("sex.male")).tag(ProProfileSex.male.rawValue)
                    }

                    TextField(localization.localized("pro.profile.age_years"), text: $proAge)
                        .keyboardType(.numberPad)

                    TextField(localization.localized("pro.profile.height_cm"), text: $proHeightCm)
                        .keyboardType(.numberPad)

                    TextField(localization.localized("pro.profile.weight_kg"), text: $proWeightKg)
                        .keyboardType(.numberPad)

                    Picker(localization.localized("pro.profile.activity"), selection: $proActivity) {
                        Text(localization.localized("activity.sedentary"))
                            .tag(ProProfileActivity.sedentary.rawValue)
                        Text(localization.localized("activity.light")).tag(ProProfileActivity.light.rawValue)
                        Text(localization.localized("activity.moderate"))
                            .tag(ProProfileActivity.moderate.rawValue)
                        Text(localization.localized("activity.active")).tag(ProProfileActivity.active.rawValue)
                        Text(localization.localized("activity.very_active"))
                            .tag(ProProfileActivity.veryActive.rawValue)
                    }

                    Picker(localization.localized("pro.profile.goal"), selection: $proGoal) {
                        Text(localization.localized("goal.loss")).tag(ProProfileGoal.loss.rawValue)
                        Text(localization.localized("goal.maintain")).tag(ProProfileGoal.maintain.rawValue)
                        Text(localization.localized("goal.gain")).tag(ProProfileGoal.gain.rawValue)
                    }

                    Text(localization.localized("pro.profile.footer"))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                Section(header: Text(localization.localized("profile_language_section"))) {
                    Label(
                        localization.localized("profile_language_value"),
                        systemImage: "globe"
                    )
                }
                if !isAppStoreScreenshotMode {
                    Section(header: Text("Animation Test")) {
                        Button("Test MP4 Animation") {
                            showAnimationTest = true
                        }
                        Button("Test Bundle Files") {
                            showBundleTest = true
                        }
                        NavigationLink("Test Lottie Animation") {
                            LottieTestView()
                        }
                    }
                }
                Section(header: Text(localization.localized("profile_legal_section"))) {
                    if let privacyURL = URL(string: "https://pulseplate.app/privacy") {
                        Link(destination: privacyURL) {
                            Label(
                                localization.localized("profile_privacy_policy"),
                                systemImage: "lock.shield"
                            )
                        }
                    }
                    if let termsURL = URL(string: "https://pulseplate.app/terms") {
                        Link(destination: termsURL) {
                            Label(
                                localization.localized("profile_terms_of_use"),
                                systemImage: "doc.text"
                            )
                        }
                    }
                }
            }
            .navigationTitle(localization.localized("home.action.profile.title"))
            .sheet(isPresented: $showAnimationTest) {
                SimpleVideoTest()
            }
            .sheet(isPresented: $showBundleTest) {
                BundleTestView()
            }
            .accessibilityLabel(localization.localized("profile_screen_accessibility_label"))
        }
    }

    private var profileHeroWidth: CGFloat {
        if dynamicTypeSize.isAccessibilitySize {
            return ProfileVisualLayout.accessibilityWidth
        }
        return horizontalSizeClass == .regular
            ? ProfileVisualLayout.regularWidth
            : ProfileVisualLayout.compactWidth
    }

    private var profileHeroHeight: CGFloat {
        if dynamicTypeSize.isAccessibilitySize {
            return ProfileVisualLayout.accessibilityHeight
        }
        return horizontalSizeClass == .regular
            ? ProfileVisualLayout.regularHeight
            : ProfileVisualLayout.compactHeight
    }
}

private enum ProfileVisualLayout {
    static let compactWidth: CGFloat = 112
    static let compactHeight: CGFloat = 148
    static let regularWidth: CGFloat = 160
    static let regularHeight: CGFloat = 148
    static let accessibilityWidth: CGFloat = 112
    static let accessibilityHeight: CGFloat = 132
    static let heroFocalX: CGFloat = 0.5
    static let heroFocalY: CGFloat = 0.44
    static let heroZoom: CGFloat = 1.02
}
